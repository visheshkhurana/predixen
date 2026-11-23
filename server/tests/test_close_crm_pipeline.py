"""Close CRM feeds the CRM pipeline card. No network: httpx MockTransport.
https://developer.close.com/api/resources/opportunities/list.md"""

import asyncio
from datetime import date, timedelta

import httpx
import pytest

from server.connectors.base import ConnectorConfig
from server.connectors.close_crm import CloseCRMConnector, close_opportunity_for_snapshot
from server.services import crm_pipeline

TODAY = date.today()


def _opp(i, status, value_cents, stage="Sales: Active", won=None, lost=None, confidence=50, cur="USD"):
    return {"id": f"oppo_{i}", "status_type": status, "status_display_name": stage, "value": value_cents,
            "value_currency": cur, "confidence": confidence,
            "date_won": won.isoformat() if won else None,
            "date_lost": f"{lost.isoformat()}T10:00:00+00:00" if lost else None}


OPPS = [
    _opp(1, "active", 1_000_000, won=TODAY + timedelta(days=20), confidence=50),
    _opp(2, "active", 500_000, stage="Sales: Demo", confidence=20),
    _opp(3, "won", 300_000, stage="Sales: Won", won=TODAY - timedelta(days=5), confidence=100),
    _opp(4, "lost", 200_000, stage="Sales: Lost", lost=TODAY - timedelta(days=10), confidence=0),
    _opp(5, "active", 900_000, cur="EUR"),
]


def test_opportunity_mapping_uses_cents_confidence_and_status_dates():
    won = close_opportunity_for_snapshot(OPPS[2])
    assert won == {"amount": 3000.0, "currency": "USD", "stage": "Sales: Won", "status": "won",
                   "close_date": OPPS[2]["date_won"], "probability": 1.0}
    lost = close_opportunity_for_snapshot(OPPS[3])
    assert lost["status"] == "lost" and lost["close_date"].startswith((TODAY - timedelta(days=10)).isoformat())
    assert close_opportunity_for_snapshot({"status_type": "active", "value": None})["amount"] == 0.0


def test_snapshot_numbers():
    snap = crm_pipeline.build_snapshot([close_opportunity_for_snapshot(o) for o in OPPS], "USD", today=TODAY)
    assert snap["open_count"] == 2 and snap["open_value"] == 15000.0
    assert snap["weighted_value"] == 10000 * 0.5 + 5000 * 0.2
    assert snap["won_count_30d"] == 1 and snap["won_value_30d"] == 3000.0
    assert snap["lost_count_30d"] == 1 and snap["win_rate_90d"] == 0.5


@pytest.fixture
def mock_http(monkeypatch):
    seen = []
    orig = httpx.AsyncClient

    def handler(req):
        seen.append(req)
        if req.url.path.endswith("/opportunity/"):
            skip = int(req.url.params["_skip"])
            lim = int(req.url.params["_limit"])
            page = OPPS[skip: skip + min(lim, 2)]
            return httpx.Response(200, json={"data": page, "has_more": skip + len(page) < len(OPPS)})
        if req.url.path.endswith("/me/"):
            return httpx.Response(200, json={"id": "user_1"})
        return httpx.Response(200, json={"data": [], "has_more": False})

    class Patched(orig):
        def __init__(self, *a, **kw):
            kw["transport"] = httpx.MockTransport(handler)
            super().__init__(*a, **kw)

    monkeypatch.setattr(httpx, "AsyncClient", Patched)
    return seen


def test_sync_emits_pipeline_snapshot_and_reads_opportunities_once(mock_http):
    conn = CloseCRMConnector(ConnectorConfig(provider_id="close_crm", company_id=1, credentials={"api_key": "k"}))
    result = asyncio.run(conn.sync_all())
    assert result.success, result.errors
    snap = result.metadata["crm_pipeline"]
    assert snap["currency"] == "USD" and snap["open_count"] == 2
    assert snap["other_currencies"] == {"EUR": {"count": 1, "value": 9000.0}}
    opp_reqs = [r for r in mock_http if r.url.path.endswith("/opportunity/")]
    assert all(r.url.params["_order_by"] == "-date_updated" for r in opp_reqs)
    assert len(opp_reqs) == 3  # 5 opps, 2 per page, one pass shared with invoices
    assert result.metadata["opportunities_count"] == 5
