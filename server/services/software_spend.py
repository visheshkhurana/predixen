"""Software spend from connectors: building the payload and storing it.

Connectors hand over `result.metadata["software_spend"]`:

    {"months": [{"period": "2026-11-01", "vendors": [
        {"vendor": "Notion", "amount": 96.0, "currency": "USD",
         "basis": "card", "transactions": 1}, ...]}]}

The sync route calls `replace_month` per month; `summary` feeds the view.
"""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Mapping, Optional

from sqlalchemy.orm import Session

from server.models.software_spend import SoftwareSpend

# Card categories that mean software. Ramp uses names like "SaaS / Software";
# Brex sends a category or the merchant MCC. MCCs: 5734 computer software
# stores, 5817/5818 digital goods (apps/software), 7372 programming/data
# processing, 4816 computer network/information services.
SOFTWARE_CATEGORY = re.compile(r"software|saas|subscription|cloud|hosting", re.IGNORECASE)
SOFTWARE_MCCS = {"5734", "5817", "5818", "7372", "4816"}


def is_software_category(category: Optional[str]) -> bool:
    if not category:
        return False
    text = str(category).strip()
    return text in SOFTWARE_MCCS or bool(SOFTWARE_CATEGORY.search(text))


def _month(value: Any) -> date:
    if isinstance(value, datetime):
        value = value.date()
    return value.replace(day=1)


def card_software_months(entries: Iterable[Any], default_currency: str = "USD") -> Dict[str, Any]:
    """Group card ledger entries in software categories by month and merchant.

    Refunds (credits) reduce the merchant's month; a month and merchant that
    nets to zero or less is left out.
    """
    totals: Dict[tuple, Dict[str, Any]] = {}
    for entry in entries:
        if (entry.metadata or {}).get("type") != "card_transaction":
            continue
        if not is_software_category(entry.category):
            continue
        vendor = ((entry.metadata or {}).get("merchant_name") or entry.description or "").strip() or "Unknown vendor"
        currency = ((entry.metadata or {}).get("currency") or default_currency).upper()
        key = (_month(entry.date), vendor, currency)
        row = totals.setdefault(key, {"amount": 0.0, "transactions": 0})
        row["amount"] += float(entry.debit or 0.0) - float(entry.credit or 0.0)
        row["transactions"] += 1

    months: Dict[date, List[Dict[str, Any]]] = defaultdict(list)
    for (period, vendor, currency), row in totals.items():
        if row["amount"] <= 0:
            continue
        months[period].append({
            "vendor": vendor,
            "amount": round(row["amount"], 2),
            "currency": currency,
            "basis": "card",
            "transactions": row["transactions"],
        })
    return {
        "months": [
            {"period": period.isoformat(), "vendors": sorted(vendors, key=lambda v: -v["amount"])}
            for period, vendors in sorted(months.items())
        ]
    }


def replace_month(
    db: Session,
    company_id: int,
    period: date,
    source: str,
    vendors: Iterable[Mapping[str, Any]],
) -> None:
    """Store one source's software spend for one month, replacing what it sent before."""
    from server.services.d2c_months import _company_currency, month_end_rate

    period = _month(period)
    company_currency = _company_currency(db, company_id)
    db.query(SoftwareSpend).filter(
        SoftwareSpend.company_id == company_id,
        SoftwareSpend.period == period,
        SoftwareSpend.source == source,
    ).delete(synchronize_session=False)

    seen = set()
    for item in vendors:
        vendor = str(item.get("vendor") or "").strip()[:255]
        if not vendor or vendor in seen:
            continue
        seen.add(vendor)
        amount = float(item.get("amount") or 0.0)
        currency = (item.get("currency") or "").upper()[:3] or None
        amount_company = None
        if currency and company_currency:
            found = month_end_rate(db, currency, company_currency, period)
            if found:
                amount_company = round(amount * found[0], 2)
        db.add(SoftwareSpend(
            company_id=company_id,
            period=period,
            source=source,
            vendor=vendor,
            currency=currency,
            amount=amount,
            amount_company=amount_company,
            basis=item.get("basis") or "card",
            transactions=item.get("transactions"),
            seats=item.get("seats"),
            active_users=item.get("active_users"),
            details=item.get("details"),
        ))


def store_payload(db: Session, company_id: int, source: str, payload: Any) -> int:
    """Apply a connector's software_spend payload. Returns months written."""
    if not isinstance(payload, Mapping):
        return 0
    written = 0
    for month in payload.get("months") or []:
        if isinstance(month, Mapping) and month.get("period"):
            replace_month(
                db, company_id, date.fromisoformat(str(month["period"])[:10]),
                source, month.get("vendors") or [],
            )
            written += 1
    return written


def summary(db: Session, company_id: int, months: int = 6) -> Dict[str, Any]:
    """Software spend per month (newest first) with vendor lines.

    A month's total is in the company's currency and counts only lines that
    could be converted; `unconverted` lists the rest so nothing is hidden.
    """
    from server.services.d2c_months import _company_currency

    rows = (
        db.query(SoftwareSpend)
        .filter(SoftwareSpend.company_id == company_id)
        .order_by(SoftwareSpend.period.desc(), SoftwareSpend.amount.desc())
        .all()
    )
    by_month: Dict[date, List[SoftwareSpend]] = defaultdict(list)
    for row in rows:
        by_month[row.period].append(row)

    out = []
    for period in sorted(by_month, reverse=True)[:max(1, months)]:
        lines = by_month[period]
        out.append({
            "period": period.isoformat(),
            "total_company": round(sum(r.amount_company for r in lines if r.amount_company is not None), 2),
            "unconverted": [
                {"vendor": r.vendor, "amount": r.amount, "currency": r.currency}
                for r in lines if r.amount_company is None
            ],
            "vendors": [
                {
                    "vendor": r.vendor,
                    "source": r.source,
                    "basis": r.basis,
                    "amount": r.amount,
                    "currency": r.currency,
                    "amount_company": r.amount_company,
                    "transactions": r.transactions,
                    "seats": r.seats,
                    "active_users": r.active_users,
                    "unused_seats": (r.details or {}).get("unused_seats"),
                }
                for r in lines
            ],
        })
    return {
        "company_id": company_id,
        "currency": _company_currency(db, company_id),
        "months": out,
        "sources": sorted({r.source for r in rows}),
    }
