"""Tally first-sync on POST /connectors/companies/{id}/sync/tally.

Why this exists: India-stack founders hitting Tally would authenticate (or get
a 200 from Prime) and still land no numbers. Tally XML credits use a trailing
minus (`1234.00-`) which crashed float(); NAME often lives on an attribute;
and BaseConnector.map_to_financials never copied ledger groups into revenue /
opex / cash — the only fields /connectors will persist.

Production use→activation telemetry is not in this repo (PostHog connector is
blocked). These tests pin the code path that made Tally activation ~0.
"""
from datetime import date, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from server.connectors.base import (
    BaseConnector,
    ConnectorConfig,
    InvoiceRecord,
    LedgerEntry,
)
from server.connectors.tally import (
    TallyConnector,
    classify_tally_ledger,
    parse_tally_amount,
    tally_period_flow,
    tally_reporting_window,
)
from server.core.db import Base
from server.models.company import Company
from server.models.financial import FinancialRecord
from server.models.truth_scan import TruthScan


LEDGER_XML = """
<ENVELOPE>
  <BODY>
    <DATA>
      <COLLECTION>
        <LEDGER NAME="Sales">
          <PARENT>Sales Accounts</PARENT>
          <OPENINGBALANCE>0.00</OPENINGBALANCE>
          <CLOSINGBALANCE>250000.00-</CLOSINGBALANCE>
        </LEDGER>
        <LEDGER>
          <NAME.LIST><NAME>Purchases</NAME></NAME.LIST>
          <PARENT>Purchase Accounts</PARENT>
          <CLOSINGBALANCE>80,000.00Dr</CLOSINGBALANCE>
        </LEDGER>
        <LEDGER>
          <NAME>Rent</NAME>
          <PARENT>Indirect Expenses</PARENT>
          <CLOSINGBALANCE>25000.00Dr</CLOSINGBALANCE>
        </LEDGER>
        <LEDGER NAME="HDFC Bank">
          <PARENT>Bank Accounts</PARENT>
          <CLOSINGBALANCE>4,20,000.00</CLOSINGBALANCE>
        </LEDGER>
        <LEDGER>
          <NAME>Sundry Debtors</NAME>
          <PARENT>Sundry Debtors</PARENT>
          <CLOSINGBALANCE>15000.00</CLOSINGBALANCE>
        </LEDGER>
      </COLLECTION>
    </DATA>
  </BODY>
</ENVELOPE>
"""

# Mid-FY (15 Sep): YTD closing is not this month's P&L. Opening is 1 Sep stock.
MID_FY_LEDGER_XML = """
<ENVELOPE>
  <BODY>
    <DATA>
      <COLLECTION>
        <LEDGER NAME="Sales">
          <PARENT>Sales Accounts</PARENT>
          <OPENINGBALANCE>200000.00-</OPENINGBALANCE>
          <CLOSINGBALANCE>250000.00-</CLOSINGBALANCE>
        </LEDGER>
        <LEDGER>
          <NAME>Purchases</NAME>
          <PARENT>Purchase Accounts</PARENT>
          <OPENINGBALANCE>50000.00Dr</OPENINGBALANCE>
          <CLOSINGBALANCE>80000.00Dr</CLOSINGBALANCE>
        </LEDGER>
        <LEDGER>
          <NAME>Rent</NAME>
          <PARENT>Indirect Expenses</PARENT>
          <OPENINGBALANCE>20000.00Dr</OPENINGBALANCE>
          <CLOSINGBALANCE>25000.00Dr</CLOSINGBALANCE>
        </LEDGER>
        <LEDGER NAME="HDFC Bank">
          <PARENT>Bank Accounts</PARENT>
          <OPENINGBALANCE>400000.00</OPENINGBALANCE>
          <CLOSINGBALANCE>4,20,000.00</CLOSINGBALANCE>
        </LEDGER>
      </COLLECTION>
    </DATA>
  </BODY>
</ENVELOPE>
"""

UNBOUNDED_CLOSING_XML = """
<ENVELOPE>
  <BODY>
    <DATA>
      <COLLECTION>
        <LEDGER NAME="Sales">
          <PARENT>Sales Accounts</PARENT>
          <CLOSINGBALANCE>250000.00-</CLOSINGBALANCE>
        </LEDGER>
        <LEDGER>
          <NAME>Purchases</NAME>
          <PARENT>Purchase Accounts</PARENT>
          <CLOSINGBALANCE>80000.00Dr</CLOSINGBALANCE>
        </LEDGER>
        <LEDGER NAME="HDFC Bank">
          <PARENT>Bank Accounts</PARENT>
          <CLOSINGBALANCE>4,20,000.00</CLOSINGBALANCE>
        </LEDGER>
      </COLLECTION>
    </DATA>
  </BODY>
</ENVELOPE>
"""

SEP_START = datetime(2026, 9, 1)
SEP_END = datetime(2026, 9, 15)

VOUCHER_XML = """
<ENVELOPE>
  <BODY>
    <DATA>
      <COLLECTION>
        <VOUCHER>
          <DATE>20260401</DATE>
          <VOUCHERNUMBER>INV-1</VOUCHERNUMBER>
          <VOUCHERTYPENAME>Tax Invoice</VOUCHERTYPENAME>
          <PARTYLEDGERNAME>Acme</PARTYLEDGERNAME>
          <AMOUNT>12000.00-</AMOUNT>
        </VOUCHER>
        <VOUCHER>
          <DATE>20260402</DATE>
          <VOUCHERNUMBER>PAY-1</VOUCHERNUMBER>
          <VOUCHERTYPENAME>Payment</VOUCHERTYPENAME>
          <AMOUNT>5000.00</AMOUNT>
        </VOUCHER>
      </COLLECTION>
    </DATA>
  </BODY>
</ENVELOPE>
"""


def _tally() -> TallyConnector:
    return TallyConnector(ConnectorConfig(provider_id="tally", company_id=1))


def _entries_from_xml(xml: str, *, include_opening: bool = True) -> list:
    rows = _tally()._parse_xml_response(xml, "ledgers")
    entries = []
    for row in rows:
        closing = row["closing_balance"]
        meta = {
            "closing_balance": closing,
            "period_start": SEP_START.date().isoformat(),
            "period_end": SEP_END.date().isoformat(),
        }
        if include_opening and "opening_balance" in row:
            meta["opening_balance"] = row["opening_balance"]
        entries.append(
            LedgerEntry(
                external_id=row["name"],
                date=SEP_END,
                account_code=row["name"],
                account_name=row["name"],
                debit=closing if closing > 0 else 0,
                credit=abs(closing) if closing < 0 else 0,
                category=row["parent"],
                metadata=meta,
            )
        )
    return entries


class TestParseTallyAmount:
    def test_trailing_minus_is_credit(self):
        assert parse_tally_amount("250000.00-") == -250000.0

    def test_cr_dr_suffixes(self):
        assert parse_tally_amount("80000.00Dr") == 80000.0
        assert parse_tally_amount("80000.00Cr") == -80000.0

    def test_indian_comma_grouping(self):
        assert parse_tally_amount("4,20,000.00") == 420000.0

    def test_unparseable_does_not_raise(self):
        assert parse_tally_amount("not-a-number") == 0.0
        assert parse_tally_amount("") == 0.0
        assert parse_tally_amount(None) == 0.0

    def test_legacy_float_would_crash_on_tally_credit(self):
        with pytest.raises(ValueError):
            float("250000.00-".replace(",", "") or 0)


class TestParseTallyXml:
    def test_ledgers_survive_trailing_minus_and_name_attributes(self):
        parsed = _tally()._parse_xml_response(LEDGER_XML, "ledgers")
        by_name = {row["name"]: row for row in parsed}
        assert set(by_name) >= {"Sales", "Purchases", "Rent", "HDFC Bank"}
        assert by_name["Sales"]["closing_balance"] == -250000.0
        assert by_name["Sales"]["opening_balance"] == 0.0
        assert by_name["Sales"]["parent"] == "Sales Accounts"
        assert by_name["Purchases"]["closing_balance"] == 80000.0
        assert "opening_balance" not in by_name["Purchases"]
        assert by_name["HDFC Bank"]["closing_balance"] == 420000.0

    def test_tax_invoice_vouchers_parse_credit_amounts(self):
        parsed = _tally()._parse_xml_response(VOUCHER_XML, "vouchers")
        assert parsed[0]["type"] == "Tax Invoice"
        assert parsed[0]["amount"] == -12000.0


class TestTallyMapToFinancials:
    def test_classify_standard_indian_groups(self):
        assert classify_tally_ledger("Sales Accounts", "Sales") == "revenue"
        assert classify_tally_ledger("Purchase Accounts", "Purchases") == "cogs"
        assert classify_tally_ledger("Indirect Expenses", "Rent") == "opex"
        assert classify_tally_ledger("Bank Accounts", "HDFC Bank") == "cash"
        assert classify_tally_ledger("Sundry Debtors", "Acme") is None

    def test_period_flow_mid_fiscal_year_not_ytd_closing(self):
        assert tally_period_flow("revenue", -200000.0, -250000.0) == 50000.0
        assert tally_period_flow("cogs", 50000.0, 80000.0) == 30000.0
        assert tally_period_flow("opex", 20000.0, 25000.0) == 5000.0

    def test_ledger_export_is_date_bounded(self):
        xml = _tally()._build_xml_request("ledgers", {
            "from_date": "01-Sep-2026",
            "to_date": "15-Sep-2026",
        })
        assert "<SVFROMDATE>01-Sep-2026</SVFROMDATE>" in xml
        assert "<SVTODATE>15-Sep-2026</SVTODATE>" in xml

    def test_reporting_window_defaults_to_month_in_progress(self):
        start, end = tally_reporting_window(now=SEP_END)
        assert start == datetime(2026, 9, 1, 0, 0, 0)
        assert end == SEP_END

    def test_mid_fy_closing_does_not_become_monthly_pnl(self):
        financials = _tally().map_to_financials(
            ledger_entries=_entries_from_xml(MID_FY_LEDGER_XML)
        )
        assert financials["revenue"] == 50000.0
        assert financials["cogs"] == 30000.0
        assert financials["opex"] == 5000.0
        assert financials["cash_balance"] == 420000.0
        assert financials["period_start"] == "2026-09-01"
        assert financials["period_end"] == "2026-09-15"

    def test_unbounded_closing_is_not_written_as_monthly_flow(self):
        financials = _tally().map_to_financials(
            ledger_entries=_entries_from_xml(UNBOUNDED_CLOSING_XML, include_opening=False)
        )
        assert "revenue" not in financials
        assert "cogs" not in financials
        assert "opex" not in financials
        assert financials["cash_balance"] == 420000.0

    def test_base_map_does_not_land_tally_ledger_metrics(self):
        """The gap this PR closes: base mapping leaves sync with nothing to persist."""
        entries = _entries_from_xml(MID_FY_LEDGER_XML)
        base = BaseConnector.map_to_financials(_tally(), ledger_entries=entries)
        assert "revenue" not in base
        assert "opex" not in base
        assert "cash_balance" not in base
        assert "expense_breakdown" in base

    def test_build_financial_record_labels_the_reporting_window(self):
        from server.api.connectors import _build_financial_record

        financials = _tally().map_to_financials(
            ledger_entries=_entries_from_xml(MID_FY_LEDGER_XML)
        )
        record = _build_financial_record(
            1, "tally", "Tally ERP", financials, date(2026, 9, 30)
        )
        assert record.revenue == 50000.0
        assert record.cogs == 30000.0
        assert record.opex == 5000.0
        assert record.cash_balance == 420000.0
        assert record.period_start == date(2026, 9, 1)
        assert record.period_end == date(2026, 9, 15)
        assert record.source_type == "connector_tally"

    def test_sales_vouchers_fill_revenue_when_ledgers_have_no_sales_group(self):
        invoices = [
            InvoiceRecord(
                external_id="INV-1",
                date=datetime(2026, 9, 10),
                total=12000.0,
                currency="INR",
                status="completed",
            )
        ]
        financials = _tally().map_to_financials(invoices=invoices)
        assert financials["revenue"] == 12000.0


class TestConnectorSyncFailureVisibility:
    @pytest.fixture
    def db(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(
            engine,
            tables=[Company.__table__, FinancialRecord.__table__, TruthScan.__table__],
        )
        session = sessionmaker(bind=engine)()
        company = Company(
            id=1,
            name="co1",
            user_id=1,
            metadata_json={
                "connectors": {
                    "tally": {"connected": True, "last_error": None},
                    "stripe": {"connected": True, "last_error": None},
                }
            },
        )
        session.add(company)
        session.commit()
        yield session
        session.close()

    def test_failed_sync_persists_last_error_without_dropping_siblings(self, db):
        from server.api.connectors import persist_connector_last_error

        company = db.query(Company).filter(Company.id == 1).first()
        persist_connector_last_error(
            db,
            company,
            "tally",
            "Financial record must contain at least one financial metric",
        )
        db.expire_all()
        company = db.query(Company).filter(Company.id == 1).first()
        connectors = company.metadata_json["connectors"]
        assert "Financial record must contain" in connectors["tally"]["last_error"]
        assert connectors["tally"]["connected"] is True
        assert connectors["stripe"]["connected"] is True
        assert connectors["stripe"]["last_error"] is None

    def test_refresh_truth_scan_after_sync_writes_a_scan_row(self, db, monkeypatch):
        from server.api import connectors as connectors_api
        import server.truth.truth_scan as truth_scan_module

        def fake_compute(company, session, prefer_record_id=None):
            return {"metrics": {"monthly_revenue": 50000, "cash_balance": 420000}}

        monkeypatch.setattr(truth_scan_module, "compute_truth_scan", fake_compute)
        company = db.query(Company).filter(Company.id == 1).first()
        scan_id = connectors_api.refresh_truth_scan_after_sync(db, company, 1)
        assert scan_id is not None
        scan = db.query(TruthScan).filter(TruthScan.id == scan_id).one()
        assert scan.outputs_json["metrics"]["monthly_revenue"] == 50000

    def test_refresh_selects_inserted_record_when_same_day_second_sync(self, db, monkeypatch):
        from server.api import connectors as connectors_api
        import server.truth.truth_scan as truth_scan_module

        today = date(2026, 9, 15)
        older = FinancialRecord(
            company_id=1,
            period_start=date(2026, 9, 1),
            period_end=today,
            revenue=250000,
            cash_balance=400000,
        )
        newer = FinancialRecord(
            company_id=1,
            period_start=date(2026, 9, 1),
            period_end=today,
            revenue=50000,
            cash_balance=420000,
        )
        db.add_all([older, newer])
        db.commit()

        def fake_compute(company, session, prefer_record_id=None):
            rec = session.query(FinancialRecord).filter(
                FinancialRecord.id == prefer_record_id
            ).one()
            return {"metrics": {"monthly_revenue": rec.revenue, "cash_balance": rec.cash_balance}}

        monkeypatch.setattr(truth_scan_module, "compute_truth_scan", fake_compute)
        company = db.query(Company).filter(Company.id == 1).first()
        scan_id = connectors_api.refresh_truth_scan_after_sync(
            db, company, 1, financial_record_id=newer.id
        )
        scan = db.query(TruthScan).filter(TruthScan.id == scan_id).one()
        assert scan.outputs_json["metrics"]["monthly_revenue"] == 50000
        assert scan.outputs_json["metrics"]["cash_balance"] == 420000
