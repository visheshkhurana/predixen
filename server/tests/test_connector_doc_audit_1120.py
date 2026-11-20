"""Fixes from the 2026-11-20 audit of connectors against vendor API docs.

Each test pins a number that came out wrong against the documented API shape.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from server.connectors.base import ConnectorConfig, InvoiceRecord, LedgerEntry
from server.connectors.chargebee import ChargebeeConnector
from server.connectors.hubspot import hubspot_deal_for_snapshot
from server.connectors.money import to_major
from server.connectors.pipedrive import pipedrive_deal_for_snapshot
from server.connectors.ramp import _card_holder_name, ramp_money
from server.connectors.recurly import RecurlyConnector
from server.connectors.salesforce import SalesforceConnector, salesforce_opportunity_for_snapshot
from server.connectors.stripe import price_unit_minor, subscription_item_mrr
from server.connectors.zoho_crm import deal_status
from server.services import crm_pipeline


def _cfg(provider: str, **creds) -> ConnectorConfig:
    return ConnectorConfig(provider_id=provider, company_id=1, credentials=creds)


# --- CRM probability scale ------------------------------------------------

def test_percent_scale_reads_one_percent_as_one_percent():
    # Zoho CRM / Pipedrive / Salesforce send 0..100. "auto" read 1 as 100%.
    assert crm_pipeline.probability(1, scale="percent") == 0.01
    assert crm_pipeline.probability(75, scale="percent") == 0.75
    assert crm_pipeline.probability(1, scale="fraction") == 1.0
    assert crm_pipeline.probability(0.4, scale="fraction") == 0.4


def test_zoho_one_percent_deal_is_open_and_lightly_weighted():
    deal = {"Stage": "Qualification", "Probability": 1, "Amount": 1000}
    assert deal_status(deal) == "open"
    snap = crm_pipeline.build_snapshot(
        [{"amount": 1000, "currency": "USD", "stage": "Qualification", "status": "open",
          "close_date": None, "probability": crm_pipeline.probability(1, scale="percent")}],
        "USD",
    )
    assert snap["weighted_value"] == 10.0


def test_hubspot_stays_on_fraction_scale():
    deal = {"properties": {"amount": "1000", "dealstage": "s1", "hs_deal_stage_probability": "1",
                           "hs_is_closed": "false", "hs_is_closed_won": "false"}}
    out = hubspot_deal_for_snapshot(deal)
    assert out["probability"] == 1.0


def test_pipedrive_falls_back_to_stage_deal_probability():
    deal = {"value": 1000, "currency": "USD", "stage_id": 7, "status": "open", "probability": None}
    out = pipedrive_deal_for_snapshot(deal, {"7": "Proposal"}, {"7": 60})
    assert out["probability"] == 0.6
    # A deal-level override wins over the stage.
    deal["probability"] = 20
    assert pipedrive_deal_for_snapshot(deal, {"7": "Proposal"}, {"7": 60})["probability"] == 0.2


# --- Salesforce -----------------------------------------------------------

def test_salesforce_opportunity_status_and_percent_probability():
    assert salesforce_opportunity_for_snapshot({"IsWon": True, "IsClosed": True})["status"] == "won"
    assert salesforce_opportunity_for_snapshot({"IsWon": False, "IsClosed": True})["status"] == "lost"
    open_opp = salesforce_opportunity_for_snapshot({"IsClosed": False, "Probability": 1, "Amount": 500})
    assert open_opp["status"] == "open" and open_opp["probability"] == 0.01


def _inv(day: date, total: float, currency: str, status: str = "paid") -> InvoiceRecord:
    return InvoiceRecord(external_id=f"{day}-{total}", date=datetime.combine(day, datetime.min.time()),
                         customer_name="c", amount=total, total=total, currency=currency, status=status)


def test_salesforce_revenue_is_this_month_in_org_currency():
    conn = SalesforceConnector(_cfg("salesforce", instance_url="https://x.my.salesforce.com", access_token="t"))
    conn._org_currency = "INR"
    today = date.today()
    old = today.replace(day=1) - timedelta(days=40)
    out = conn.map_to_financials(invoices=[
        _inv(today, 1000, "INR"), _inv(old, 99999, "INR"), _inv(today, 50, "USD"),
    ])
    assert out["revenue"] == 1000
    assert out["revenue_currency"] == "INR"
    assert out["revenue_other_currencies"] == ["USD"]
    assert out["period_start"] == today.replace(day=1).isoformat()


# --- Stripe ---------------------------------------------------------------

def test_stripe_quarterly_price_is_a_third_per_month():
    item = {"quantity": 1, "price": {"unit_amount": 30000, "currency": "usd",
                                     "recurring": {"interval": "month", "interval_count": 3}}}
    assert subscription_item_mrr(item) == 100.0


def test_stripe_yearly_and_daily():
    yearly = {"quantity": 2, "price": {"unit_amount": 120000, "currency": "usd",
                                       "recurring": {"interval": "year", "interval_count": 1}}}
    assert subscription_item_mrr(yearly) == 200.0
    daily = {"quantity": 1, "price": {"unit_amount": 100, "currency": "usd",
                                      "recurring": {"interval": "day", "interval_count": 1}}}
    assert round(subscription_item_mrr(daily), 4) == round(365 / 12, 4)


def test_stripe_zero_decimal_currency_is_not_divided():
    item = {"quantity": 1, "price": {"unit_amount": 5000, "currency": "jpy",
                                     "recurring": {"interval": "month"}}}
    assert subscription_item_mrr(item) == 5000.0
    assert to_major(5000, "usd") == 50.0


def test_stripe_tiered_prices():
    graduated = {"tiers_mode": "graduated", "unit_amount": None, "tiers": [
        {"up_to": 10, "unit_amount": 1000}, {"up_to": None, "unit_amount": 500},
    ]}
    assert price_unit_minor(graduated, 15) == 10 * 1000 + 5 * 500
    volume = {"tiers_mode": "volume", "unit_amount": None, "tiers": [
        {"up_to": 10, "unit_amount": 1000}, {"up_to": None, "unit_amount": 500, "flat_amount": 200},
    ]}
    assert price_unit_minor(volume, 15) == 15 * 500 + 200
    assert price_unit_minor({"unit_amount": None, "unit_amount_decimal": "12.5"}, 2) == 25.0


# --- Chargebee ------------------------------------------------------------

def test_chargebee_mrr_comes_from_subscriptions_not_invoice_history():
    conn = ChargebeeConnector(_cfg("chargebee", site="acme", api_key="k"))
    today = date.today()
    old = today.replace(day=1) - timedelta(days=60)
    out = conn.map_to_financials(
        invoices=[_inv(today, 300, "USD"), _inv(old, 5000, "USD")],
        subscriptions=[
            {"status": "active", "mrr": 10000, "currency_code": "USD"},
            {"status": "non_renewing", "mrr": 5000, "currency_code": "USD"},
            {"status": "cancelled", "mrr": 99900, "currency_code": "USD"},
        ],
    )
    assert out["mrr"] == 150.0 and out["mrr_currency"] == "USD"
    assert out["revenue"] == 300 and out["revenue_currency"] == "USD"


# --- Recurly --------------------------------------------------------------

def _entry(category: str, debit: float, credit: float, amount: float) -> LedgerEntry:
    return LedgerEntry(external_id=category, date=datetime.now(), account_code="", account_name="",
                       debit=debit, credit=credit, description="", category=category,
                       metadata={"amount": amount})


def test_recurly_refunds_reduce_collections_and_pending_is_not_failed():
    conn = RecurlyConnector(_cfg("recurly", api_key="k"))
    out = conn.map_to_financials(ledger_entries=[
        _entry("Subscription Revenue", 0, 100, 100),
        _entry("Refund", 30, 0, 30),
        _entry("Failed Payment", 0, 0, 40),
        _entry("Pending", 0, 0, 999),
    ])
    assert out["total_collected"] == 70
    assert out["total_refunded"] == 30
    assert out["total_failed"] == 40


# --- Ramp -----------------------------------------------------------------

def test_ramp_names_and_zero_decimal_fallback():
    assert _card_holder_name({"first_name": "Ada", "last_name": "Lovelace"}) == "Ada Lovelace"
    assert ramp_money({"value": 1200, "currency": "JPY"}) == 1200.0
    assert ramp_money({"value": 1200, "currency": "USD"}) == 12.0
    assert ramp_money({"amount": 1200, "minor_unit_conversion_rate": 100}) == 12.0


# --- Deel / Gusto ---------------------------------------------------------

def test_deel_rate_unit_is_scale_not_invoice_frequency():
    from server.connectors.deel import annual_compensation
    # Deel's own example: scale hourly, invoiced monthly.
    amount, cur = annual_compensation({"amount": 50, "scale": "hourly", "frequency": "monthly",
                                       "currency_code": "USD"})
    assert amount == 50 * 2080 and cur == "USD"


def test_gusto_requests_off_cycle_payrolls():
    import inspect
    from server.connectors import gusto
    assert '"payroll_types": "regular,off_cycle"' in inspect.getsource(gusto.GustoConnector.fetch_payroll_runs)
