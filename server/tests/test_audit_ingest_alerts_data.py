"""Data-correctness fixes from the 10-16 audit: Termina import burn, alerts
churn/runway, and the dead analytics token.

The extractor OpenAI-key fallback lives in #155 (server/core/openai_credentials.py).
This branch does not add a second resolver.

Run: .venv/bin/python -m pytest server/tests/test_audit_ingest_alerts_data.py -o addopts="" -q
"""
import asyncio
import io
import os
import re
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest
from starlette.datastructures import UploadFile

import server.api.datasets as datasets_api
from server.api.alerts import _perform_health_analysis
from server.models.financial import FinancialRecord

REPO_ROOT = Path(__file__).resolve().parents[2]


class _Query:
    def __init__(self, first=None, rows=None):
        self._first, self._rows = first, rows or []

    def filter(self, *a, **k):
        return self

    def order_by(self, *a, **k):
        return self

    def first(self):
        return self._first

    def all(self):
        return self._rows


class _DB:
    def __init__(self, company, rows=None):
        self.company, self.rows, self.added = company, rows or [], []

    def query(self, model):
        if model is FinancialRecord:
            return _Query(rows=self.rows)
        return _Query(first=self.company)

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        pass


def _costs(r):
    return (r.cogs or 0) + (r.opex or 0) + (r.payroll or 0) + (r.other_costs or 0)


# 1. Termina import: net burn is a result, not a cost line ------------------

def _upload(monkeypatch, endpoint, processor_name, baseline, filename):
    monkeypatch.setattr(
        datasets_api, processor_name, lambda path, **kwargs: {"baseline_data": baseline}
    )
    import server.services.sample_data as sd
    monkeypatch.setattr(sd, "on_real_financials_written", lambda *a, **k: None)
    db = _DB(company=SimpleNamespace(id=1))
    f = UploadFile(file=io.BytesIO(b"x"), filename=filename)
    asyncio.run(endpoint(company_id=1, file=f, save_as_baseline=True, db=db,
                         current_user=SimpleNamespace(id=1)))
    return [o for o in db.added if isinstance(o, FinancialRecord)][0]


def test_pdf_import_stores_extracted_net_burn_not_burn_plus_costs(monkeypatch):
    baseline = {"monthly_revenue": 10_000, "gross_margin": 70,
                "operating_expenses": 40_000, "net_burn": 50_000, "cash_balance": 600_000}
    rec = _upload(monkeypatch, datasets_api.upload_termina_pdf, "process_termina_pdf",
                  baseline, "r.pdf")
    assert _costs(rec) - rec.revenue == pytest.approx(50_000)
    assert rec.opex == pytest.approx(40_000)


def test_excel_import_stores_extracted_net_burn(monkeypatch):
    baseline = {"monthly_revenue": 10_000, "gross_margin": 70, "opex": 40_000,
                "net_burn": 50_000, "cash_balance": 600_000}
    rec = _upload(monkeypatch, datasets_api.upload_termina_excel, "process_termina_excel",
                  baseline, "r.xlsx")
    assert _costs(rec) - rec.revenue == pytest.approx(50_000)


def test_cost_lines_trimmed_when_named_lines_exceed_stated_burn():
    from server.ingest.termina_costs import termina_cost_lines
    lines = termina_cost_lines(revenue=10_000, cogs=3_000, opex=40_000, payroll=0, net_burn=20_000)
    assert sum(lines.values()) - 10_000 == pytest.approx(20_000)
    assert all(v >= 0 for v in lines.values())


# 2/3. Alerts health: no fake churn, profitable runway is not 0 ------------

def _record(month, revenue, opex, cash):
    return SimpleNamespace(period_start=date(2026, month, 1), revenue=revenue, opex=opex,
                           payroll=0, cogs=0, other_costs=0, cash_balance=cash)


def test_health_churn_is_not_fabricated():
    rows = [_record(m, 10_000, 30_000, 500_000 - m * 20_000) for m in (1, 2, 3)]
    out = _perform_health_analysis(1, None, _DB(SimpleNamespace(id=1), rows), SimpleNamespace(id=1))
    churn = out["drivers"].get("churn_rate")
    if churn is not None:
        assert churn["current_value"] is None
        assert churn["status"] == "unknown"


def test_profitable_single_record_runway_is_not_zero():
    rows = [_record(1, 50_000, 20_000, 300_000)]
    out = _perform_health_analysis(1, None, _DB(SimpleNamespace(id=1), rows), SimpleNamespace(id=1))
    runway = out["drivers"]["runway_months"]
    assert runway["current_value"] != 0
    assert runway["current_value"] >= 900  # the client's "Sustainable" sentinel
    assert runway["status"] == "healthy"


# 4. The dead static analytics token must not come back ------------------------

# Built from parts so this file does not itself contain the literal.
_DEAD_TOKEN = "founderconsole" + "-analytics-" + "2026"
_SKIP_DIRS = {".git", "node_modules", ".venv", "dist", "build", "__pycache__", ".cache"}


def test_dead_analytics_token_not_in_tree():
    hits = []
    static_token_url = re.compile(r"email-tracking/analytics\?token=[A-Za-z0-9_-]+")
    for dirpath, dirnames, filenames in os.walk(REPO_ROOT):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for name in filenames:
            if not name.endswith((".py", ".ts", ".tsx", ".js", ".md", ".json", ".html", ".txt")):
                continue
            path = Path(dirpath) / name
            try:
                text = path.read_text(errors="ignore")
            except OSError:
                continue
            if _DEAD_TOKEN in text or static_token_url.search(text):
                hits.append(str(path.relative_to(REPO_ROOT)))
    assert not hits, f"static analytics token found in: {hits}"
