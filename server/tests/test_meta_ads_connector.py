"""Meta Ads: monthly spend per ad account, platform-reported purchases, and how
spend lands in marketing_spend (manual > ad platforms, summed, never mixed
across currencies). No call leaves the process: Graph is an httpx MockTransport."""

import asyncio
import json
from datetime import date, datetime
from unittest.mock import patch

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from server.connectors import meta_ads
from server.connectors.base import ConnectorConfig
from server.core.d2c import D2CPeriodInputs, compute_unit_economics
from server.models.company import Company
from server.models.d2c_month import D2CAdSpend, D2CMonth
from server.models.exchange_rate import ExchangeRate
from server.models.user import User
from server.services import d2c_months

NOW = datetime(2026, 11, 12, 9, 0)  # last full months: Aug, Sep, Oct 2026


def _insight(start, end, spend, purchases=None, value=None, pixel_only=False, currency="INR"):
    row = {"date_start": start, "date_stop": end, "spend": str(spend), "impressions": "1000",
           "clicks": "50", "account_currency": currency}
    if purchases is not None:
        kinds = ["offsite_conversion.fb_pixel_purchase"] if pixel_only else [
            "offsite_conversion.fb_pixel_purchase", "omni_purchase", "purchase"]
        row["actions"] = [{"action_type": "link_click", "value": "50"}] + [
            {"action_type": k, "value": str(purchases)} for k in kinds]
        row["action_values"] = [{"action_type": k, "value": str(value)} for k in kinds]
    return row


def _connector(handler, accounts="act_111, 222", lookback=3):
    conn = meta_ads.MetaAdsConnector(ConnectorConfig(
        provider_id="meta_ads", company_id=1,
        credentials={"access_token": "EAAtoken", "ad_account_ids": accounts},
        settings={"lookback_months": lookback},
    ))
    conn._client = httpx.AsyncClient(base_url=meta_ads.BASE_URL, transport=httpx.MockTransport(handler))
    sleeps = []

    async def fake_sleep(seconds):
        sleeps.append(seconds)

    conn._sleep = fake_sleep
    return conn, sleeps


def _run_sync(conn):
    with patch.object(meta_ads, "datetime", wraps=datetime) as dt:
        dt.utcnow.return_value = NOW
        return asyncio.run(conn.sync_all())


def _graph_error(code, message="err", status=400, subcode=None):
    err = {"message": message, "type": "OAuthException", "code": code}
    if subcode:
        err["error_subcode"] = subcode
    return httpx.Response(status, json={"error": err})


# --- pure parsing ------------------------------------------------------------

def test_account_ids_are_normalised():
    assert meta_ads.parse_account_ids("act_111, 222;act_111\n333") == ["act_111", "act_222", "act_333"]
    assert meta_ads.parse_account_ids(["act_9"]) == ["act_9"]
    with pytest.raises(ValueError):
        meta_ads.parse_account_ids("act_12x")


def test_full_months_are_complete_calendar_months():
    assert meta_ads.full_months(date(2026, 3, 1), 3) == [
        (date(2025, 12, 1), date(2025, 12, 31)),
        (date(2026, 1, 1), date(2026, 1, 31)),
        (date(2026, 2, 1), date(2026, 2, 28)),
    ]


def test_purchase_actions_use_one_type_never_a_sum():
    # omni_purchase includes the pixel purchases; adding them would double count.
    assert meta_ads.parse_purchases(_insight("2026-10-01", "2026-10-31", 100, 7, 7000)) == (7.0, 7000.0)
    assert meta_ads.parse_purchases(_insight("2026-10-01", "2026-10-31", 100, 3, 900, pixel_only=True)) == (3.0, 900.0)
    assert meta_ads.parse_purchases({"actions": [{"action_type": "link_click", "value": "9"}]}) == (None, None)


def test_monthly_bucketing():
    months = meta_ads.full_months(date(2026, 11, 12), 3)
    rows = [
        _insight("2026-10-01", "2026-10-31", 1000.5, 10, 4000),
        _insight("2026-09-01", "2026-09-15", 200, 1, 300),   # split rows for one month still sum
        _insight("2026-09-16", "2026-09-30", 300, 2, 700),
        _insight("2026-07-01", "2026-07-31", 999),            # outside the window: dropped
    ]
    b = meta_ads.bucket_monthly(rows, months)
    assert set(b) == {"2026-08-01", "2026-09-01", "2026-10-01"}
    assert b["2026-08-01"]["spend"] == 0.0 and b["2026-08-01"]["purchase_value"] is None, "no row = nothing spent"
    assert b["2026-09-01"]["spend"] == 500.0 and b["2026-09-01"]["purchases"] == 3.0
    assert b["2026-09-01"]["platform_roas"] == pytest.approx(2.0)
    assert b["2026-10-01"]["spend"] == 1000.5 and b["2026-10-01"]["impressions"] == 1000


# --- against a mocked Graph API ---------------------------------------------

def _happy_graph(seen, currency_222="INR"):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "graph.facebook.com"
        assert request.url.params["access_token"] == "EAAtoken"
        path = request.url.path
        seen.append((path, dict(request.url.params)))
        assert path.startswith(f"/{meta_ads.GRAPH_API_VERSION}/")
        if path.endswith("/act_111"):
            return httpx.Response(200, json={"id": "act_111", "name": "Brand IN", "currency": "INR", "account_status": 1})
        if path.endswith("/act_222"):
            return httpx.Response(200, json={"id": "act_222", "name": "Brand Intl", "currency": currency_222, "account_status": 1})
        if path.endswith("/act_111/insights"):
            if request.url.params.get("after") == "page2":
                return httpx.Response(200, json={"data": [_insight("2026-10-01", "2026-10-31", 60000, 120, 180000)]})
            return httpx.Response(200, json={
                "data": [_insight("2026-08-01", "2026-08-31", 40000, 80, 100000),
                         _insight("2026-09-01", "2026-09-30", 50000, 90, 120000)],
                "paging": {"cursors": {"after": "page2"},
                           "next": f"{meta_ads.BASE_URL}/act_111/insights?after=page2&access_token=EAAtoken"},
            })
        if path.endswith("/act_222/insights"):
            return httpx.Response(200, json={"data": [_insight("2026-10-01", "2026-10-31", 500, 5, 1500, currency=currency_222)]})
        return httpx.Response(404, json={"error": {"message": "unknown", "code": 803}})
    return handler


def test_sync_pulls_monthly_insights_and_follows_pagination():
    seen = []
    conn, _ = _connector(_happy_graph(seen))
    result = _run_sync(conn)
    assert result.success, result.errors
    months = {m["period"]: m["accounts"] for m in result.metadata["ad_spend"]["months"]}
    assert list(months) == ["2026-08-01", "2026-09-01", "2026-10-01"]
    oct_ = {a["account_id"]: a for a in months["2026-10-01"]}
    assert oct_["act_111"]["spend"] == 60000 and oct_["act_111"]["purchase_value"] == 180000
    assert oct_["act_111"]["currency"] == "INR" and oct_["act_222"]["spend"] == 500
    aug_222 = {a["account_id"]: a for a in months["2026-08-01"]}["act_222"]
    assert aug_222["spend"] == 0.0, "every connected account gets a row each month"

    insight_calls = [p for path, p in seen if path.endswith("/act_111/insights")]
    assert len(insight_calls) == 2, "follows paging.next"
    first = insight_calls[0]
    assert first["time_increment"] == "monthly" and first["level"] == "account"
    assert json.loads(first["time_range"]) == {"since": "2026-08-01", "until": "2026-10-31"}
    assert "actions" in first["fields"] and "action_values" in first["fields"]


def test_paging_link_to_another_host_is_refused():
    def handler(request):
        if request.url.path.endswith("/insights"):
            return httpx.Response(200, json={"data": [], "paging": {"next": "https://evil.example/steal"}})
        return httpx.Response(200, json={"name": "A", "currency": "INR"})
    conn, _ = _connector(handler, accounts="act_1")
    result = _run_sync(conn)
    assert not result.success and "Refusing" in result.errors[0]


def test_rate_limit_is_retried_with_backoff():
    calls = {"n": 0}

    def handler(request):
        if request.url.path.endswith("/insights"):
            calls["n"] += 1
            if calls["n"] <= 2:
                code = 17 if calls["n"] == 1 else 80004
                return _graph_error(code, "User request limit reached")
            return httpx.Response(200, json={"data": [_insight("2026-10-01", "2026-10-31", 10)]})
        return httpx.Response(200, json={"name": "A", "currency": "INR"})

    conn, sleeps = _connector(handler, accounts="act_1")
    result = _run_sync(conn)
    assert result.success, result.errors
    assert calls["n"] == 3
    assert sleeps == [2.0, 4.0], "exponential backoff between retries"


def test_rate_limit_honours_business_use_case_header_and_gives_up_clearly():
    usage = json.dumps({"1": [{"type": "ads_insights", "estimated_time_to_regain_access": 5}]})

    def handler(request):
        if request.url.path.endswith("/insights"):
            return httpx.Response(400, headers={"x-business-use-case-usage": usage},
                                  json={"error": {"message": "too many calls", "code": 80004}})
        return httpx.Response(200, json={"name": "A", "currency": "INR"})

    conn, sleeps = _connector(handler, accounts="act_1")
    result = _run_sync(conn)
    assert not result.success
    assert "rate-limiting" in result.errors[0]
    assert len(sleeps) == meta_ads.MAX_RETRIES
    assert all(s == meta_ads.BACKOFF_CAP_SECONDS for s in sleeps), "waits as told, capped"
    assert not result.metadata.get("needs_reauth")


def test_expired_token_flags_reauth():
    def handler(request):
        if request.url.path.endswith("/insights"):
            return _graph_error(190, "Error validating access token: Session has expired", subcode=463, status=401)
        return httpx.Response(200, json={"name": "A", "currency": "INR"})

    conn, _ = _connector(handler, accounts="act_1")
    result = _run_sync(conn)
    assert not result.success
    assert result.metadata["needs_reauth"] is True
    assert "Reconnect Meta Ads" in result.errors[0]


def test_expired_token_at_connect_is_a_clear_auth_error():
    conn, _ = _connector(lambda r: _graph_error(190, "Invalid OAuth access token"), accounts="act_1")
    assert asyncio.run(conn.authenticate()) is False
    assert "Reconnect Meta Ads" in conn.auth_error
    result = _run_sync(conn)
    assert result.metadata["needs_reauth"] is True


def test_permission_error_names_ads_read():
    conn, _ = _connector(lambda r: _graph_error(200, "Ad account owner has NOT grant ads_management or ads_read permission"),
                         accounts="act_1")
    assert asyncio.run(conn.authenticate()) is False
    assert "act_1" in conn.auth_error and "ads_read" in conn.auth_error
    result = _run_sync(conn)
    assert not result.success and not result.metadata.get("needs_reauth")


def test_missing_credentials():
    conn = meta_ads.MetaAdsConnector(ConnectorConfig(provider_id="meta_ads", company_id=1, credentials={}))
    assert asyncio.run(conn.authenticate()) is False and "access token" in conn.auth_error
    conn = meta_ads.MetaAdsConnector(ConnectorConfig(provider_id="meta_ads", company_id=1,
                                                     credentials={"access_token": "x", "ad_account_ids": "bogus"}))
    assert asyncio.run(conn.authenticate()) is False and "bogus" in conn.auth_error


def test_appsecret_proof_is_sent_when_the_app_secret_is_set(monkeypatch):
    monkeypatch.setenv("META_APP_SECRET", "s3cret")
    seen = []

    def handler(request):
        seen.append(dict(request.url.params))
        return httpx.Response(200, json={"name": "A", "currency": "INR"})

    conn, _ = _connector(handler, accounts="act_1")
    assert asyncio.run(conn.authenticate())
    assert len(seen[0]["appsecret_proof"]) == 64


# --- storage and precedence --------------------------------------------------

@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    User.metadata.create_all(engine, tables=[User.__table__, Company.__table__, D2CMonth.__table__,
                                             D2CAdSpend.__table__, ExchangeRate.__table__])
    session = sessionmaker(bind=engine)()
    owner = User(email="owner@brand.in", is_active=True)
    session.add(owner)
    session.flush()
    session.add(Company(id=1, name="Brand", user_id=owner.id, currency="INR"))
    session.commit()
    return session


OCT = date(2026, 10, 1)


def _acct(account_id, spend, currency="INR", value=None):
    return {"account_id": account_id, "account_name": account_id, "currency": currency, "spend": spend,
            "impressions": 1000, "clicks": 10, "purchases": 3, "purchase_value": value}


def _month(db):
    return db.query(D2CMonth).filter(D2CMonth.period == OCT).one()


def test_spend_is_summed_across_accounts_and_resync_does_not_double_count(db):
    d2c_months.replace_ad_spend(db, 1, OCT, "meta_ads", [_acct("act_1", 60000), _acct("act_2", 15000)])
    assert _month(db).marketing_spend == 75000
    assert _month(db).field_sources["marketing_spend"] == "meta_ads"
    d2c_months.replace_ad_spend(db, 1, OCT, "meta_ads", [_acct("act_1", 61000), _acct("act_2", 15000)])
    assert _month(db).marketing_spend == 76000, "a re-sync replaces, it does not add"
    assert db.query(D2CAdSpend).count() == 2


def test_a_second_ad_platform_adds_to_the_total_without_touching_meta(db):
    d2c_months.replace_ad_spend(db, 1, OCT, "meta_ads", [_acct("act_1", 60000)])
    d2c_months.replace_ad_spend(db, 1, OCT, "google_ads", [_acct("123-456-7890", 20000)])
    assert _month(db).marketing_spend == 80000
    assert _month(db).field_sources["marketing_spend"] == "google_ads+meta_ads"
    d2c_months.replace_ad_spend(db, 1, OCT, "meta_ads", [_acct("act_1", 50000)])
    assert _month(db).marketing_spend == 70000
    d2c_months.remove_ad_source(db, 1, "google_ads")
    assert _month(db).marketing_spend == 50000


def test_manual_spend_beats_meta_and_clearing_it_hands_back(db):
    d2c_months.upsert_month(db, 1, OCT, {"marketing_spend": 90000}, source="manual")
    d2c_months.replace_ad_spend(db, 1, OCT, "meta_ads", [_acct("act_1", 60000)])
    assert _month(db).marketing_spend == 90000, "the founder's number includes channels Meta doesn't know"
    view = d2c_months.month_view_for(db, 1, _month(db))
    assert view["ad_spend"]["manual_override"] is True
    assert view["ad_spend"]["total"] == 60000

    d2c_months.upsert_month(db, 1, OCT, {"marketing_spend": None}, source="manual")
    d2c_months.recompute_marketing_spend(db, 1, OCT)
    assert _month(db).marketing_spend == 60000


def test_other_currency_is_not_mixed_in_without_a_rate(db):
    d2c_months.replace_ad_spend(db, 1, OCT, "meta_ads", [_acct("act_1", 60000), _acct("act_2", 500, currency="USD", value=1500)])
    month = _month(db)
    assert month.marketing_spend is None, "no total rather than INR + USD added together"
    view = d2c_months.month_view_for(db, 1, month)["ad_spend"]
    assert view["total"] is None
    assert view["currency_mismatch"] == [{"source_label": "Meta Ads", "account_id": "act_2", "currency": "USD", "spend": 500}]
    usd = next(a for a in view["accounts"] if a["account_id"] == "act_2")
    assert usd["spend"] == 500 and usd["currency"] == "USD", "native amount kept"
    assert usd["platform_roas"] == pytest.approx(3.0)


def test_static_fallback_rates_are_not_used_but_stored_market_rates_are(db):
    db.add(ExchangeRate(base_currency="USD", quote_currency="INR", rate=83.0, rate_date=date(2026, 10, 31), source="static_fallback"))
    db.commit()
    d2c_months.replace_ad_spend(db, 1, OCT, "meta_ads", [_acct("act_2", 500, currency="USD")])
    assert _month(db).marketing_spend is None

    db.add(ExchangeRate(base_currency="USD", quote_currency="INR", rate=88.0, rate_date=date(2026, 10, 30), source="ecb_live"))
    db.commit()
    d2c_months.replace_ad_spend(db, 1, OCT, "meta_ads", [_acct("act_1", 60000), _acct("act_2", 500, currency="USD", value=1000)])
    assert _month(db).marketing_spend == 60000 + 44000
    view = d2c_months.month_view_for(db, 1, _month(db))["ad_spend"]
    usd = next(a for a in view["accounts"] if a["account_id"] == "act_2")
    assert usd["fx_rate"] == 88.0 and usd["fx_rate_date"] == "2026-10-30"
    assert view["sources"][0]["platform_purchase_value"] == pytest.approx(88000)


def test_a_mismatch_clears_a_total_the_platforms_set_but_not_a_manual_one(db):
    d2c_months.replace_ad_spend(db, 1, OCT, "meta_ads", [_acct("act_1", 60000)])
    assert _month(db).marketing_spend == 60000
    d2c_months.replace_ad_spend(db, 1, OCT, "meta_ads", [_acct("act_1", 60000), _acct("act_2", 1, currency="USD")])
    assert _month(db).marketing_spend is None and "marketing_spend" not in _month(db).field_sources


def test_meta_purchase_value_never_feeds_mer(db):
    d2c_months.upsert_month(db, 1, OCT, {"orders_shipped": 1000, "gross_sales": 1_000_000, "cogs": 300_000,
                                         "forward_shipping_per_order": 60, "cod_share": 0.5,
                                         "payment_gateway_pct": 0.02, "cod_fee_per_order": 20}, source="manual")
    d2c_months.replace_ad_spend(db, 1, OCT, "meta_ads", [_acct("act_1", 250_000, value=2_000_000)])
    view = d2c_months.month_view_for(db, 1, _month(db))
    ue = view["unit_economics"]
    assert ue["mer"] == pytest.approx(1_000_000 / 250_000), "store net revenue / spend"
    assert view["ad_spend"]["sources"][0]["platform_roas"] == pytest.approx(8.0), "Meta's own claim, shown apart"
    assert ue["break_even_mer"] == pytest.approx(ue["net_revenue"] / ue["cm2"])


def test_break_even_mer():
    ue = compute_unit_economics(D2CPeriodInputs(
        orders_shipped=100, gross_sales=100_000, cogs=40_000, forward_shipping_per_order=50,
        cod_share=0.0, payment_gateway_pct=0.0, marketing_spend=30_000))
    # net revenue 100k, CM2 = 100k - 40k - 5k = 55k -> break-even MER 1.818x; MER 3.33x
    assert ue.break_even_mer == pytest.approx(100_000 / 55_000)
    assert ue.cm3 == pytest.approx(25_000)
    no_cm2 = compute_unit_economics(D2CPeriodInputs(orders_shipped=10, gross_sales=1000))
    assert no_cm2.break_even_mer is None


def test_months_without_store_data_still_list_their_spend(db):
    d2c_months.replace_ad_spend(db, 1, OCT, "meta_ads", [_acct("act_1", 1000)])
    months = d2c_months.list_months(db, 1)
    assert months[0]["period"] == "2026-10-01"
    assert months[0]["ad_spend"]["total"] == 1000
    assert months[0]["unit_economics"] is None
