"""Shopify sync for an Indian D2C store.

The old sync summed only financial_status=paid orders (dropping COD, which
Shopify leaves pending until the courier remits), read the newest 500 orders
of all time, kept GST inside revenue, and dated everything to today.
"""

import asyncio
from datetime import date, datetime
from unittest.mock import AsyncMock, patch

import pytest

from server.connectors import shopify
from server.connectors.base import ConnectorConfig


def _order(**kw):
    base = {
        "id": 1,
        "test": False,
        "cancelled_at": None,
        "financial_status": "paid",
        "gateway": "razorpay",
        "payment_gateway_names": ["Razorpay Secure"],
        "taxes_included": True,
        "total_line_items_price": "1180.00",
        "total_discounts": "0.00",
        "subtotal_price": "1180.00",
        "total_tax": "180.00",
        "refunds": [],
        "customer": {"id": 11},
    }
    base.update(kw)
    return base


COD = dict(financial_status="pending", gateway="Cash on Delivery (COD)",
           payment_gateway_names=["Cash on Delivery (COD)"])


def test_cod_orders_count_as_sales():
    summary = shopify.summarize_orders([_order(id=1), _order(id=2, customer={"id": 12}, **COD)])
    assert summary["orders"] == 2
    assert summary["cod_orders"] == 1
    assert summary["cod_share"] == 0.5
    assert summary["revenue"] == pytest.approx(2000.0), "both orders, GST removed"


def test_gst_is_removed_only_when_prices_include_it():
    inclusive = shopify.summarize_orders([_order()])
    exclusive = shopify.summarize_orders([_order(taxes_included=False, subtotal_price="1000.00")])
    assert inclusive["net_sales_ex_gst"] == pytest.approx(1000.0)
    assert exclusive["net_sales_ex_gst"] == pytest.approx(1000.0)
    assert inclusive["gst_collected"] == pytest.approx(180.0)


def test_discounts_and_refunds():
    order = _order(
        total_line_items_price="1500.00",
        total_discounts="320.00",
        subtotal_price="1180.00",
        refunds=[{"transactions": [
            {"kind": "refund", "status": "success", "amount": "200.00"},
            {"kind": "refund", "status": "failure", "amount": "999.00"},
        ]}],
    )
    summary = shopify.summarize_orders([order])
    assert summary["gross_sales"] == pytest.approx(1500.0)
    assert summary["discounts"] == pytest.approx(320.0)
    assert summary["refunds"] == pytest.approx(200.0)
    assert summary["revenue"] == pytest.approx(800.0)


def test_cancelled_and_test_orders_earn_nothing():
    summary = shopify.summarize_orders([
        _order(id=1),
        _order(id=2, cancelled_at="2026-10-04T10:00:00+05:30"),
        _order(id=3, test=True),
    ])
    assert summary["orders"] == 1
    assert summary["cancelled_orders"] == 1
    assert summary["revenue"] == pytest.approx(1000.0)


def test_empty_month():
    summary = shopify.summarize_orders([])
    assert summary["orders"] == 0 and summary["cod_share"] is None and summary["aov"] is None


def test_last_complete_month():
    assert shopify.last_complete_month(date(2026, 11, 4)) == (date(2026, 10, 1), date(2026, 10, 31))
    assert shopify.last_complete_month(date(2026, 1, 15)) == (date(2025, 12, 1), date(2025, 12, 31))


def _connector():
    return shopify.ShopifyConnector(ConnectorConfig(
        provider_id="shopify", company_id=1,
        credentials={"shop_domain": "brand.myshopify.com", "access_token": "x"},
    ))


def test_api_version_is_current_and_overridable(monkeypatch):
    monkeypatch.delenv("SHOPIFY_API_VERSION", raising=False)
    assert _connector()._get_base_url().endswith("/admin/api/2026-10")
    monkeypatch.setenv("SHOPIFY_API_VERSION", "2027-01")
    assert _connector()._get_base_url().endswith("/admin/api/2027-01")


def test_sync_declares_the_month_and_reads_every_order():
    conn = _connector()
    orders = [_order(id=i, customer={"id": i}) for i in range(600)] + [_order(id=999, **COD)]
    get_orders = AsyncMock(return_value=orders)
    with patch.object(conn, "authenticate", AsyncMock(return_value=True)), \
            patch.object(conn, "get_orders", get_orders), \
            patch.object(conn, "get_products", AsyncMock(return_value=[])), \
            patch.object(shopify, "datetime", wraps=datetime) as dt:
        dt.utcnow.return_value = datetime(2026, 11, 4, 9, 0)
        result = asyncio.run(conn.sync_all())

    assert result.success
    fin = result.metadata["financials"]
    assert (fin["period_start"], fin["period_end"]) == ("2026-10-01", "2026-10-31")
    assert fin["revenue"] == pytest.approx(601 * 1000.0), "all 601 orders, COD included"
    assert fin["d2c"]["cod_orders"] == 1
    kwargs = get_orders.call_args.kwargs
    assert kwargs["limit"] == shopify.MAX_ORDERS_PER_SYNC
    assert kwargs["start_date"].date() == date(2026, 10, 1)
    assert kwargs["end_date"].date() == date(2026, 10, 31)
    get_orders.assert_awaited_once()
