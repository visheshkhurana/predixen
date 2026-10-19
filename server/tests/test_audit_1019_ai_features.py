"""AI-feature audit fixes (10-19): doc generator grounding, benchmark search,
OpenAI reasoning-model params, Slack linking, peer-benchmark privacy,
competitor URL safety, and the per-user LLM rate limit. No network: every LLM
and HTTP call is mocked."""
import asyncio
import hashlib
import hmac
import inspect
import time
import urllib.parse
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from server.core.db import Base
from server.models.company import Company
from server.models.company_decision import CompanyDecision
from server.models.financial import FinancialRecord
from server.models.scenario import Scenario
from server.models.truth_scan import TruthScan
from server.models.workspace import WorkspaceMember


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            Company.__table__,
            FinancialRecord.__table__,
            CompanyDecision.__table__,
            Scenario.__table__,
            TruthScan.__table__,
            WorkspaceMember.__table__,
        ],
    )
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _company(db, name="Co", **kw):
    c = Company(user_id=1, name=name, **kw)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _record(db, company_id, revenue=10000, runway=12.0, period=date(2026, 9, 1)):
    db.add(FinancialRecord(
        company_id=company_id,
        period_start=period,
        period_end=period,
        revenue=revenue,
        cogs=0,
        opex=1000,
        payroll=1000,
        other_costs=0,
        cash_balance=50000,
        runway_months=runway,
        source_type="manual",
    ))
    db.commit()


# ---------------------------------------------------------------------------
# 1. Doc generator
# ---------------------------------------------------------------------------
from server.api import doc_generator as dg


def test_known_metrics_drops_estimates_and_missing():
    metrics = {
        "mrr": 20000,
        "net_burn": {"value": 15000},
        "cac": 500,
        "ltv": 6000,
        "customer_count": 150,
        "net_revenue_retention": 100,
        "_estimated_metrics": ["cac", "ltv", "customer_count", "net_revenue_retention"],
    }
    out = dg._known_metrics(metrics)
    assert out["mrr"] == 20000
    assert out["burn_rate"] == 15000
    for name in ("cac", "ltv", "customers", "ndr", "cash_balance", "churn_rate"):
        assert out[name] is None, name


def test_prompt_marks_unknowns_and_forbids_invention():
    context = {
        "company": {"name": "Acme", "industry": "SaaS", "stage": "Seed"},
        "metrics": dg._known_metrics({"mrr": 20000, "cac": 500, "_estimated_metrics": ["cac"]}),
        "confidence": 60,
        "financial_records": [{
            "period_start": "2026-09-01", "revenue": 20000.0, "cogs": None, "opex": 5000.0,
            "payroll": 8000.0, "cash_balance": 300000.0, "net_burn": None,
            "headcount": 4, "customers": None,
        }],
        "scenarios": [],
    }
    prompt = dg._build_section_prompt("investor-memo", "Traction & Metrics", context)
    assert "MRR: $20,000" in prompt
    assert "CAC:" not in prompt  # estimated placeholder is not presented as data
    assert "Not available" in prompt and "CAC" in prompt.split("Not available")[1]
    assert "$0" not in prompt
    assert "2026-09-01" in prompt and "revenue $20,000" in prompt
    assert "Never invent" in prompt
    assert "Use specific numbers" not in prompt


def test_sample_records_never_reach_the_document_prompt(db):
    """Seeded demo numbers are not the founder's history and must not be
    presented as monthly records in a board or investor document."""
    company = _company(db, name="Sample SaaS Co.", metadata_json={"is_sample": True})
    _record(db, company.id, revenue=111.0, period=date(2026, 1, 1))
    db.query(FinancialRecord).filter(FinancialRecord.revenue == 111.0).update(
        {FinancialRecord.source_type: "sample"}, synchronize_session=False
    )
    _record(db, company.id, revenue=222.0, period=date(2026, 2, 1))
    db.add(FinancialRecord(company_id=company.id, period_start=date(2026, 3, 1),
                           period_end=date(2026, 3, 1), revenue=333.0))  # NULL = entered by hand
    db.commit()

    context = dg._gather_company_context(db, company)
    revenues = [r["revenue"] for r in context["financial_records"]]
    assert revenues == [333.0, 222.0]  # sample row dropped, newest first
    assert context["is_sample"] is True

    prompt = dg._build_section_prompt("board-memo", "Financial Highlights", context)
    assert "$111" not in prompt
    assert "$222" in prompt and "$333" in prompt
    assert "Sample data notice" in prompt
    assert "not reported by the founder" in prompt


def _run_generate(llm_side_effect):
    company = SimpleNamespace(id=1, name="Acme")
    user = SimpleNamespace(id=7, email="f@example.com")
    context = {
        "company": {"id": 1, "name": "Acme", "industry": "SaaS", "stage": "Seed", "currency": "USD"},
        "metrics": dg._known_metrics({}),
        "confidence": 50,
        "financial_records": [],
        "scenarios": [],
    }
    fake_router = MagicMock()
    fake_router.chat.side_effect = llm_side_effect
    with patch.object(dg, "get_user_company", return_value=company), \
         patch.object(dg, "_gather_company_context", return_value=context), \
         patch("server.lib.llm.llm_router.LLMRouter", return_value=fake_router), \
         patch("server.email.activity_triggers.trigger_document_generated_email") as email:
        result = dg.generate_document(
            1, dg.GenerateDocRequest(doc_type="board-memo"), db=MagicMock(), current_user=user
        )
    return result, email


def test_no_email_when_every_section_failed():
    result, email = _run_generate(RuntimeError("provider down"))
    assert all(s["model_used"] == "error" for s in result["sections"])
    email.assert_not_called()


def test_email_counts_only_successful_sections():
    calls = {"n": 0}

    def flaky(**kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("boom")
        return {"content": "ok", "model": "m", "provider": "p"}

    _, email = _run_generate(flaky)
    email.assert_called_once()
    assert email.call_args.kwargs["sections_count"] == 4


# ---------------------------------------------------------------------------
# 2. Benchmark search
# ---------------------------------------------------------------------------
from server.api import benchmark_search as bs


@pytest.fixture(autouse=True)
def _reset_state():
    bs.BENCHMARK_CACHE.clear()
    from server.core import llm_rate_limit
    llm_rate_limit.reset_llm_rate_limit()
    yield
    bs.BENCHMARK_CACHE.clear()
    llm_rate_limit.reset_llm_rate_limit()


_PPLX = {"choices": [{"message": {"content": "Median gross margin 75% ..."}}], "citations": ["https://example.com/r"]}


def test_parse_routes_through_llm_router_without_bad_params():
    fake = MagicMock()
    fake.chat.return_value = {"content": '```json\n{"benchmarks": [{"metric_name": "gross_margin", "p25": 65, "p50": 75, "p75": 82, "direction": "higher_is_better"}]}\n```'}
    with patch("server.lib.llm.llm_router.LLMRouter", return_value=fake), \
         patch("httpx.AsyncClient") as raw_http:
        result = asyncio.run(bs.parse_benchmarks_with_ai(_PPLX, "fintech", "seed", user_id=3))
    raw_http.assert_not_called()  # no direct api.openai.com post
    assert not result.is_fallback
    assert [b.metric_name for b in result.benchmarks] == ["gross_margin"]
    assert "response_format" not in fake.chat.call_args.kwargs


def test_parse_failure_returns_labelled_generic_defaults():
    fake = MagicMock()
    fake.chat.side_effect = RuntimeError("model rejected")
    with patch("server.lib.llm.llm_router.LLMRouter", return_value=fake):
        result = asyncio.run(bs.parse_benchmarks_with_ai(_PPLX, "fintech", "seed"))
    assert result.is_fallback
    assert result.sources == [bs.GENERIC_DEFAULTS_SOURCE]
    assert "generic" in (result.note or "").lower()


def _user(uid=1):
    return SimpleNamespace(id=uid)


def test_fallback_is_not_cached():
    async def boom(*a, **k):
        raise RuntimeError("no key")

    with patch.object(bs, "search_benchmarks_with_perplexity", boom):
        r1 = asyncio.run(bs.search_industry_benchmarks(bs.BenchmarkSearchRequest(industry="Fintech"), db=None, current_user=_user()))
    assert r1.is_fallback
    assert len(bs.BENCHMARK_CACHE) == 0


def test_real_result_cached_with_normalized_key():
    async def ok(*a, **k):
        return _PPLX

    async def parsed(resp, industry, stage, user_id=None):
        return bs.BenchmarkSearchResponse(
            industry=industry, stage=stage,
            benchmarks=[bs.BenchmarkData(metric_name="gross_margin", p25=1, p50=2, p75=3, direction="higher_is_better")],
            sources=[], last_updated="now",
        )

    with patch.object(bs, "search_benchmarks_with_perplexity", ok), \
         patch.object(bs, "parse_benchmarks_with_ai", parsed):
        asyncio.run(bs.search_industry_benchmarks(bs.BenchmarkSearchRequest(industry=" FinTech "), db=None, current_user=_user()))
        r2 = asyncio.run(bs.search_industry_benchmarks(bs.BenchmarkSearchRequest(industry="fintech"), db=None, current_user=_user()))
    assert r2.is_cached
    assert len(bs.BENCHMARK_CACHE) == 1


def test_cache_is_bounded():
    for i in range(bs.CACHE_MAX_ENTRIES + 20):
        bs.cache_put(bs.get_cache_key(f"industry {i}", "seed"), {"timestamp": "2099-01-01T00:00:00"})
    assert len(bs.BENCHMARK_CACHE) == bs.CACHE_MAX_ENTRIES
    assert len(bs.get_cache_key("x" * 5000, "seed")) < 200


def test_cache_key_separates_inputs_a_slug_collapses():
    # Two all-non-ASCII industries used to slug to "" and share the key "|seed".
    assert bs.get_cache_key("Eコマース", "seed") != bs.get_cache_key("フィンテック", "seed")
    # Two long names used to collide on their first _KEY_MAX_LEN characters.
    assert bs.get_cache_key("a" * 200 + "x", "seed") != bs.get_cache_key("a" * 200 + "y", "seed")
    # Case and whitespace still normalize to one entry.
    assert bs.get_cache_key("  FinTech  ", "Seed") == bs.get_cache_key("fintech", "seed")
    # Still bounded.
    assert len(bs.get_cache_key("x" * 5000, "seed")) < 200
    assert len(bs.get_cache_key("Eコマース", "シリーズA")) < 200


def test_clear_cache_requires_platform_admin():
    from server.api.admin import require_platform_admin
    dep = inspect.signature(bs.clear_benchmark_cache).parameters["current_user"].default
    assert dep.dependency is require_platform_admin


# ---------------------------------------------------------------------------
# 3. OpenAI params for reasoning models
# ---------------------------------------------------------------------------
from server.lib.llm import openai_client as oc


def test_sampling_params_for_reasoning_models():
    assert oc.build_sampling_params("gpt-5", 0.2, 500) == {"max_completion_tokens": 500}
    assert oc.build_sampling_params("gpt-5-mini", 0, None) == {}
    assert oc.build_sampling_params("o3-mini", 0.5, 100) == {"max_completion_tokens": 100}
    assert oc.build_sampling_params("gpt-4o", 0.2, 500) == {"temperature": 0.2, "max_tokens": 500}


def _fake_completion_client(captured):
    def create(**kwargs):
        captured.append(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="hi"))],
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1, total_tokens=2),
            model=kwargs["model"],
        )
    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))


def test_chat_completion_sends_valid_params_to_gpt5():
    captured = []
    with patch.object(oc, "_get_client", return_value=_fake_completion_client(captured)):
        client = oc.AuditedOpenAIClient()
        client.chat_completion([{"role": "user", "content": "x"}], model="gpt-5", temperature=0.3, max_tokens=256)
        client.chat_completion([{"role": "user", "content": "x"}], model="gpt-4o", temperature=0.3, max_tokens=256)
    gpt5, gpt4o = captured
    assert "temperature" not in gpt5 and "max_tokens" not in gpt5
    assert gpt5["max_completion_tokens"] == 256
    assert gpt4o["temperature"] == 0.3 and gpt4o["max_tokens"] == 256


# ---------------------------------------------------------------------------
# 4. Slack linking + /fc-simulate keys
# ---------------------------------------------------------------------------
from server.api import slack_bot as sb


def test_link_code_flow_links_company_beyond_first_100(db):
    for i in range(120):
        _company(db, name=f"Other {i}")
    target = _company(db, name="Target")
    user = SimpleNamespace(id=9)
    # This test is about the company lookup, not authorization: stub the role gate.
    with patch.object(sb, "get_user_company", return_value=target), \
         patch.object(sb, "get_user_company_role", return_value="owner"):
        issued = sb.create_slack_link_code(target.id, db=db, current_user=user)
    code = issued["code"]

    assert sb._get_company_from_slack(db, "T1", "C1") is None
    linked = sb._link_with_code(db, code.lower(), "T1", "C1", "U1")
    assert linked is not None and linked.id == target.id
    found = sb._get_company_from_slack(db, "T1", "")
    assert found is not None and found.id == target.id
    # Single use.
    assert sb._link_with_code(db, code, "T2", "C2", "U1") is None


def test_expired_link_code_rejected(db):
    c = _company(db, name="Late")
    with patch.object(sb, "get_user_company", return_value=c):
        code = sb.create_slack_link_code(c.id, db=db, current_user=SimpleNamespace(id=1))["code"]
    meta = dict(c.metadata_json)
    meta[sb.LINK_CODE_META_KEY] = dict(meta[sb.LINK_CODE_META_KEY], expires_at=time.time() - 1)
    c.metadata_json = meta
    db.commit()
    assert sb._link_with_code(db, code, "T9", "C9", "U") is None
    assert sb._get_company_from_slack(db, "T9", "") is None


def test_relinking_team_moves_it(db):
    a = _company(db, name="A")
    b = _company(db, name="B")
    for company in (a, b):
        with patch.object(sb, "get_user_company", return_value=company):
            code = sb.create_slack_link_code(company.id, db=db, current_user=SimpleNamespace(id=1))["code"]
        sb._link_with_code(db, code, "TEAM", "", "U")
    assert sb._get_company_from_slack(db, "TEAM", "").id == b.id


def test_fc_link_slash_command_end_to_end(db, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from server.core.db import get_db

    monkeypatch.setenv("SLACK_SIGNING_SECRET", "test-secret")
    monkeypatch.setattr(sb, "_get_metrics_snapshot", lambda db, company: {"runway_months": 14.0})
    c = _company(db, name="Linked Co")
    with patch.object(sb, "get_user_company", return_value=c):
        code = sb.create_slack_link_code(c.id, db=db, current_user=SimpleNamespace(id=1))["code"]

    app = FastAPI()
    app.include_router(sb.router)
    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)

    def send(command, text=""):
        body = urllib.parse.urlencode({
            "command": command, "text": text, "team_id": "TX", "channel_id": "CX", "user_id": "UX",
        })
        ts = str(int(time.time()))
        sig = "v0=" + hmac.new(b"test-secret", f"v0:{ts}:{body}".encode(), hashlib.sha256).hexdigest()
        return client.post("/slack/commands", content=body, headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Slack-Request-Timestamp": ts,
            "X-Slack-Signature": sig,
        })

    assert "No company linked" in send("/fc-runway").json()["text"]
    assert "Linked" in send("/fc-link", code).json()["text"]
    assert "Linked Co" in str(send("/fc-runway").json())


def _member(db, company, user_id=2, role="viewer"):
    member = WorkspaceMember(
        company_id=company.id, user_id=user_id, role=role, status="active", invited_by=1,
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


def test_viewer_cannot_issue_inspect_or_revoke_a_slack_link(db):
    c = _company(db, name="Shared Co")
    _member(db, c, user_id=2, role="viewer")
    viewer = SimpleNamespace(id=2)

    for call in (
        lambda: sb.create_slack_link_code(c.id, db=db, current_user=viewer),
        lambda: sb.get_slack_link_status(c.id, db=db, current_user=viewer),
        lambda: sb.unlink_slack(c.id, db=db, current_user=viewer),
    ):
        with pytest.raises(HTTPException) as exc:
            call()
        assert exc.value.status_code == 403

    db.refresh(c)
    assert sb.LINK_CODE_META_KEY not in (c.metadata_json or {})


def test_admin_can_issue_and_revoke_a_slack_link(db):
    c = _company(db, name="Admin Co")
    _member(db, c, user_id=3, role="admin")
    admin = SimpleNamespace(id=3)

    code = sb.create_slack_link_code(c.id, db=db, current_user=admin)["code"]
    assert len(code) == 10
    assert sb.get_slack_link_status(c.id, db=db, current_user=admin)["linked"] is False
    assert sb.unlink_slack(c.id, db=db, current_user=admin) == {"linked": False}

    db.refresh(c)
    assert sb.LINK_CODE_META_KEY not in (c.metadata_json or {})


def test_removing_the_linking_member_revokes_the_slack_link(db):
    from server.api import workspace as ws

    c = _company(db, name="Removal Co")
    leaver = _member(db, c, user_id=2, role="admin")
    code = sb.create_slack_link_code(c.id, db=db, current_user=SimpleNamespace(id=2))["code"]
    assert sb._link_with_code(db, code, "T-REMOVE", "C1", "U1") is not None
    db.refresh(c)
    assert (c.metadata_json or {})[sb.SLACK_META_KEY]["linked_by_user_id"] == 2

    result = ws.remove_member(leaver.id, db=db, current_user=SimpleNamespace(id=1))

    assert result == {"status": "removed"}
    db.refresh(c)
    assert sb.SLACK_META_KEY not in (c.metadata_json or {})
    assert sb._get_company_from_slack(db, "T-REMOVE", "") is None


def test_removing_another_member_leaves_the_link_alone(db):
    from server.api import workspace as ws

    c = _company(db, name="Keep Co")
    bystander = _member(db, c, user_id=2, role="viewer")
    code = sb.create_slack_link_code(c.id, db=db, current_user=SimpleNamespace(id=1))["code"]
    assert sb._link_with_code(db, code, "T-KEEP", "C1", "U1") is not None

    ws.remove_member(bystander.id, db=db, current_user=SimpleNamespace(id=1))

    db.refresh(c)
    assert (c.metadata_json or {})[sb.SLACK_META_KEY]["team_id"] == "T-KEEP"

def test_slack_command_rejects_a_forged_signature(db, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from server.core.db import get_db

    monkeypatch.setenv("SLACK_SIGNING_SECRET", "test-secret")
    app = FastAPI()
    app.include_router(sb.router)
    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)

    body = urllib.parse.urlencode({
        "command": "/fc-runway", "text": "", "team_id": "TX", "channel_id": "CX", "user_id": "UX",
    })
    ts = str(int(time.time()))
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Slack-Request-Timestamp": ts,
    }
    forged = "v0=" + hmac.new(
        b"not-the-secret", f"v0:{ts}:{body}".encode(), hashlib.sha256
    ).hexdigest()

    assert client.post(
        "/slack/commands", content=body, headers={**headers, "X-Slack-Signature": forged}
    ).status_code == 401
    assert client.post("/slack/commands", content=body, headers=headers).status_code == 401

    stale = str(int(time.time()) - 600)
    stale_sig = "v0=" + hmac.new(
        b"test-secret", f"v0:{stale}:{body}".encode(), hashlib.sha256
    ).hexdigest()
    assert client.post("/slack/commands", content=body, headers={
        **headers,
        "X-Slack-Request-Timestamp": stale,
        "X-Slack-Signature": stale_sig,
    }).status_code == 401

def test_simulate_reads_engine_shape():
    from server.utils.survival import survival_pct
    out = {"runway": {"p10": 9.0, "p50": 14.5, "p90": 20.0}, "survival": {"12m": 90.0, "18m": 71.3}}
    assert sb._runway_p50(out) == 14.5
    assert survival_pct(out.get("survival"), 18) == 71.3
    assert sb._runway_p50({}) is None


# ---------------------------------------------------------------------------
# 5. Intelligence graph peer privacy
# ---------------------------------------------------------------------------
from server.services import intelligence_graph as ig


def _peer(db, name, sharing=True, sample=False, revenue=10000, stage="seed"):
    c = _company(db, name=name, stage=stage, industry="saas", data_sharing_enabled=sharing,
                 metadata_json={"is_sample": True} if sample else {})
    _record(db, c.id, revenue=revenue)
    return c


def _profile(me):
    return {"company_id": me.id, "stage": "seed", "industry": "saas", "mrr": 5000, "runway_months": 10}


def test_peer_insights_need_five_opted_in_non_sample_peers(db):
    me = _peer(db, "Me", revenue=5000)
    for i in range(4):
        _peer(db, f"P{i}", revenue=10000 + i)
    _peer(db, "Sample", sample=True)
    _peer(db, "Private", sharing=False)
    insights = ig._generate_peer_insights(db, _profile(me))
    assert [i["type"] for i in insights] == ["insufficient_peers"]

    _peer(db, "P4", revenue=99999)
    insights = ig._generate_peer_insights(db, _profile(me))
    rev = [i for i in insights if i["type"] == "revenue_benchmark"]
    assert rev and rev[0]["peer_count"] == 5


def test_growth_benchmarks_hide_thin_buckets(db):
    me = _peer(db, "Me", revenue=5000)
    for i in range(4):
        _peer(db, f"Seed{i}")
    _peer(db, "Sample", sample=True)
    _peer(db, "Private", sharing=False)
    for i in range(5):
        _peer(db, f"A{i}", stage="series_a", revenue=50000 + i)
    with patch.object(ig, "get_company_profile", return_value={"stage": "seed"}):
        out = ig.get_growth_benchmarks(db, me.id)
    assert "seed" not in out["stage_benchmarks"]
    assert out["insufficient_peers"] == {"seed": 4}
    assert out["stage_benchmarks"]["series_a"]["sample_size"] == 5
    assert out["total_companies_analyzed"] == 9


# ---------------------------------------------------------------------------
# 6. Competitor signal URLs
# ---------------------------------------------------------------------------
from server.api import competitors as comp_api


@pytest.mark.parametrize("url,expected", [
    ("https://example.com/a", "https://example.com/a"),
    ("http://example.com", "http://example.com"),
    ("javascript:alert(1)", None),
    ("JavaScript:alert(1)", None),
    ("data:text/html,hi", None),
    ("//example.com", None),
    ("/relative", None),
    ("https://", None),
    (None, None),
    (42, None),
])
def test_safe_http_url(url, expected):
    assert comp_api._safe_http_url(url) == expected


def test_scan_drops_non_http_urls():
    content = '[{"title": "A", "url": "javascript:alert(1)"}, {"title": "B", "url": "https://ok.example/b"}]'
    resp = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])
    fake = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **k: resp)))
    competitor = SimpleNamespace(name="Rival", website=None, blog_url=None, linkedin_url=None, x_handle=None)
    with patch.object(comp_api, "_get_openai_client", return_value=fake):
        items = comp_api._scan_competitor_web(competitor)
    assert [i["url"] for i in items] == [None, "https://ok.example/b"]


def test_signal_dict_sanitizes_stored_urls():
    s = SimpleNamespace(id=1, competitor_id=1, source_type="web", title="t", url="javascript:x",
                        summary=None, sentiment=None, threat_level=None, impact=None,
                        published_at=None, created_at=None, is_read=False)
    assert comp_api._signal_dict(s)["url"] is None


# ---------------------------------------------------------------------------
# 7. Per-user LLM rate limit
# ---------------------------------------------------------------------------
from server.core import llm_rate_limit as rl


def test_llm_rate_limit_per_user(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_LLM_PER_USER", "3")
    for _ in range(3):
        rl.check_llm_rate_limit(1)
    with pytest.raises(HTTPException) as exc:
        rl.check_llm_rate_limit(1)
    assert exc.value.status_code == 429
    rl.check_llm_rate_limit(2)  # other users unaffected


def test_rate_limit_wired_on_llm_routes(monkeypatch):
    from server.api import ai_graphics
    dep = inspect.signature(ai_graphics.generate_image).parameters["current_user"].default
    assert dep.dependency is rl.llm_rate_limit

    # The document generator is the most expensive route: five section calls per
    # request, so it must be metered like the single-call ones.
    doc_dep = inspect.signature(dg.generate_document).parameters["current_user"].default
    assert doc_dep.dependency is rl.llm_rate_limit

    monkeypatch.setenv("RATE_LIMIT_LLM_PER_USER", "1")
    rl.check_llm_rate_limit(5)

    async def never(*a, **k):
        raise AssertionError("should be rate limited first")

    with patch.object(bs, "search_benchmarks_with_perplexity", never):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(bs.search_industry_benchmarks(bs.BenchmarkSearchRequest(industry="x"), db=None, current_user=_user(5)))
    assert exc.value.status_code == 429
