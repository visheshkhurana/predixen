"""Store and read D2C monthly inputs, and compute unit economics from them."""

from __future__ import annotations

from dataclasses import fields
from datetime import date, timedelta
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from sqlalchemy.orm import Session

from server.core.d2c import D2CPeriodInputs, compute_unit_economics
from server.models.d2c_month import D2CAdSpend, D2CMonth

INPUT_FIELDS = tuple(f.name for f in fields(D2CPeriodInputs))
MANUAL = "manual"

# Fields where one connector knows better than another. Shopify counts orders
# placed; the shipping partner counts what actually shipped and what came
# back, so its numbers are kept even if a Shopify sync runs later.
PREFERRED_SOURCE = {
    "orders_shipped": "shiprocket",
    "rto_orders": "shiprocket",
    "cod_share": "shiprocket",
}


def month_start(value: date) -> date:
    return value.replace(day=1)


def upsert_month(
    db: Session,
    company_id: int,
    period: date,
    values: Mapping[str, Any],
    source: str,
) -> D2CMonth:
    """Write the given fields for one month.

    A connector never overwrites a field the founder set by hand; a manual
    write always wins. A value of None from a connector is ignored (it does
    not know the field); a None from a manual write clears it.
    """
    period = month_start(period)
    row = (
        db.query(D2CMonth)
        .filter(D2CMonth.company_id == company_id, D2CMonth.period == period)
        .one_or_none()
    )
    if row is None:
        row = D2CMonth(company_id=company_id, period=period, field_sources={})
        db.add(row)

    sources = dict(row.field_sources or {})
    for name, value in values.items():
        if name not in INPUT_FIELDS:
            continue
        if source != MANUAL:
            current = sources.get(name)
            if value is None or current == MANUAL:
                continue
            preferred = PREFERRED_SOURCE.get(name)
            if preferred and current == preferred and source != preferred:
                continue
        setattr(row, name, value)
        if value is None:
            sources.pop(name, None)
        else:
            sources[name] = source
    row.field_sources = sources
    db.flush()
    return row


def inputs_from_row(row: D2CMonth) -> Optional[D2CPeriodInputs]:
    """The engine needs orders and sales; without them there is nothing to compute."""
    if row.orders_shipped is None or row.gross_sales is None:
        return None
    kwargs = {name: getattr(row, name) for name in INPUT_FIELDS}
    for name, default in (("discounts", 0.0), ("rto_orders", 0), ("customer_returns_value", 0.0), ("customer_returns_orders", 0)):
        if kwargs[name] is None:
            kwargs[name] = default
    return D2CPeriodInputs(**kwargs)


def month_view(row: D2CMonth, ad_rows: Optional[List[D2CAdSpend]] = None, company_currency: Optional[str] = None) -> Dict[str, Any]:
    inputs = {name: getattr(row, name) for name in INPUT_FIELDS}
    view: Dict[str, Any] = {
        "period": row.period.isoformat(),
        "inputs": inputs,
        "sources": dict(row.field_sources or {}),
        "unit_economics": None,
        "error": None,
        "ad_spend": ad_spend_view(ad_rows or [], company_currency, row.marketing_spend,
                                  (row.field_sources or {}).get("marketing_spend")),
    }
    engine_inputs = inputs_from_row(row)
    if engine_inputs is None:
        view["missing"] = [n for n in ("orders_shipped", "gross_sales") if inputs[n] is None]
        return view
    try:
        view["unit_economics"] = compute_unit_economics(engine_inputs).as_dict()
    except ValueError as exc:
        view["error"] = str(exc)
    return view


def list_months(db: Session, company_id: int, limit: int = 12) -> List[Dict[str, Any]]:
    rows = (
        db.query(D2CMonth)
        .filter(D2CMonth.company_id == company_id)
        .order_by(D2CMonth.period.desc())
        .limit(limit)
        .all()
    )
    currency = _company_currency(db, company_id)
    periods = [r.period for r in rows]
    ads: Dict[date, List[D2CAdSpend]] = {}
    if periods:
        for ad in (
            db.query(D2CAdSpend)
            .filter(D2CAdSpend.company_id == company_id, D2CAdSpend.period.in_(periods))
            .order_by(D2CAdSpend.source, D2CAdSpend.account_id)
            .all()
        ):
            ads.setdefault(ad.period, []).append(ad)
    return [month_view(r, ads.get(r.period, []), currency) for r in rows]


def month_view_for(db: Session, company_id: int, row: D2CMonth) -> Dict[str, Any]:
    ads = (
        db.query(D2CAdSpend)
        .filter(D2CAdSpend.company_id == company_id, D2CAdSpend.period == row.period)
        .order_by(D2CAdSpend.source, D2CAdSpend.account_id)
        .all()
    )
    return month_view(row, ads, _company_currency(db, company_id))


def shopify_values(summary: Mapping[str, Any]) -> Dict[str, Any]:
    """Map the Shopify sync summary onto engine inputs.

    Shopify's net_sales_ex_gst is already after discounts, so it becomes
    gross_sales with discounts left to the engine as 0; refunds are returns.
    Orders are placed orders until a shipping partner reports shipped ones.
    """
    return {
        "orders_shipped": summary.get("orders"),
        "gross_sales": summary.get("net_sales_ex_gst"),
        "discounts": 0.0 if summary.get("net_sales_ex_gst") is not None else None,
        "customer_returns_value": summary.get("refunds"),
        "cod_share": summary.get("cod_share"),
        "new_customers": None,
    }


# --- Ad spend (one row per month x platform x ad account) --------------------
#
# marketing_spend precedence: a manual entry wins. Otherwise it is the sum of
# every ad platform's spend for the month in the company's currency. Each
# platform's sync replaces only its own rows for the month, so re-syncing Meta
# never double counts and adding Google Ads later just adds rows to the sum.
# If any account's spend cannot be put in the company's currency (no stored
# market rate), the total is left empty rather than mixing currencies or
# leaving that account out; the Profit screen shows why.

AD_SOURCE_LABELS = {"meta_ads": "Meta Ads", "google_ads": "Google Ads"}
FX_RATE_MAX_AGE_DAYS = 7  # a rate dated after month end, up to a week later, still counts


def _company_currency(db: Session, company_id: int) -> Optional[str]:
    from server.models.company import Company

    company = db.query(Company).filter(Company.id == company_id).one_or_none()
    if company is None or not company.currency:
        return None
    return company.currency.upper()


def month_end_rate(db: Session, from_currency: str, to_currency: str, period: date) -> Optional[Tuple[float, date]]:
    """A stored market rate (not the static fallback table) for the month's end.

    Uses the newest stored rate dated within the month or up to a week after
    it, direct or crossed through USD. Returns None when there is none: the
    caller then refuses to convert instead of guessing.
    """
    from server.models.exchange_rate import ExchangeRate

    if from_currency == to_currency:
        return 1.0, period
    start = month_start(period)
    end = (start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    latest = end + timedelta(days=FX_RATE_MAX_AGE_DAYS)

    def newest(base: str, quote: str) -> Optional[Any]:
        return (
            db.query(ExchangeRate)
            .filter(
                ExchangeRate.base_currency == base,
                ExchangeRate.quote_currency == quote,
                ExchangeRate.rate_date >= start,
                ExchangeRate.rate_date <= latest,
                ExchangeRate.source != "static_fallback",
                ExchangeRate.rate > 0,
            )
            .order_by(ExchangeRate.rate_date.desc())
            .first()
        )

    direct = newest(from_currency, to_currency)
    if direct:
        return direct.rate, direct.rate_date
    inverse = newest(to_currency, from_currency)
    if inverse:
        return 1.0 / inverse.rate, inverse.rate_date
    def per_usd(currency: str) -> Optional[Tuple[float, Optional[date]]]:
        if currency == "USD":
            return 1.0, None
        r = newest("USD", currency)
        return (r.rate, r.rate_date) if r else None

    src, dst = per_usd(from_currency), per_usd(to_currency)
    if src and dst:
        dates = [d for d in (src[1], dst[1]) if d is not None]
        return dst[0] / src[0], min(dates)
    return None


def replace_ad_spend(
    db: Session,
    company_id: int,
    period: date,
    source: str,
    accounts: Iterable[Mapping[str, Any]],
) -> None:
    """Store one platform's spend for one month, replacing what it sent before,
    then recompute marketing_spend for that month."""
    period = month_start(period)
    company_currency = _company_currency(db, company_id)
    db.query(D2CAdSpend).filter(
        D2CAdSpend.company_id == company_id,
        D2CAdSpend.period == period,
        D2CAdSpend.source == source,
    ).delete(synchronize_session=False)

    for acct in accounts:
        spend = float(acct.get("spend") or 0.0)
        currency = (acct.get("currency") or "").upper() or None
        spend_company = fx_rate = fx_date = None
        if currency and company_currency:
            found = month_end_rate(db, currency, company_currency, period)
            if found:
                fx_rate, fx_date = found
                spend_company = round(spend * fx_rate, 2)
                if currency == company_currency:
                    fx_rate = fx_date = None
        db.add(D2CAdSpend(
            company_id=company_id,
            period=period,
            source=source,
            account_id=str(acct.get("account_id")),
            account_name=acct.get("account_name"),
            currency=currency,
            spend=spend,
            spend_company=spend_company,
            fx_rate=fx_rate,
            fx_rate_date=fx_date,
            impressions=acct.get("impressions"),
            clicks=acct.get("clicks"),
            purchases=acct.get("purchases"),
            purchase_value=acct.get("purchase_value"),
        ))
    db.flush()
    recompute_marketing_spend(db, company_id, period)


def remove_ad_source(db: Session, company_id: int, source: str) -> int:
    """Drop a disconnected platform's rows and recompute the months they fed."""
    periods = [
        p for (p,) in db.query(D2CAdSpend.period)
        .filter(D2CAdSpend.company_id == company_id, D2CAdSpend.source == source)
        .distinct()
        .all()
    ]
    removed = db.query(D2CAdSpend).filter(
        D2CAdSpend.company_id == company_id, D2CAdSpend.source == source
    ).delete(synchronize_session=False)
    db.flush()
    for period in periods:
        recompute_marketing_spend(db, company_id, period)
    return removed


def recompute_marketing_spend(db: Session, company_id: int, period: date) -> D2CMonth:
    period = month_start(period)
    row = (
        db.query(D2CMonth)
        .filter(D2CMonth.company_id == company_id, D2CMonth.period == period)
        .one_or_none()
    )
    ads = (
        db.query(D2CAdSpend)
        .filter(D2CAdSpend.company_id == company_id, D2CAdSpend.period == period)
        .all()
    )
    if row is None:
        if not ads:
            return None  # nothing to record
        row = D2CMonth(company_id=company_id, period=period, field_sources={})
        db.add(row)

    sources = dict(row.field_sources or {})
    current = sources.get("marketing_spend")
    if current == MANUAL:
        return row  # the founder's number stands; ad rows are still shown beside it

    if not ads or any(a.spend_company is None for a in ads):
        # No platform data, or a currency we cannot convert: no total rather
        # than a wrong one. Only clear a value the ad platforms set.
        if current is not None:
            row.marketing_spend = None
            sources.pop("marketing_spend", None)
    else:
        row.marketing_spend = round(sum(a.spend_company for a in ads), 2)
        sources["marketing_spend"] = "+".join(sorted({a.source for a in ads}))
    row.field_sources = sources
    db.flush()
    return row


def ad_spend_view(
    ads: List[D2CAdSpend],
    company_currency: Optional[str],
    marketing_spend: Optional[float] = None,
    marketing_source: Optional[str] = None,
) -> Dict[str, Any]:
    """Spend by platform and account for the Profit screen.

    platform_roas is purchase value / spend as the ad platform reports it.
    It is labelled platform-reported and never feeds MER.
    """
    accounts = []
    by_source: Dict[str, Dict[str, Any]] = {}
    for a in ads:
        roas = (a.purchase_value / a.spend) if a.purchase_value is not None and a.spend else None
        accounts.append({
            "source": a.source,
            "source_label": AD_SOURCE_LABELS.get(a.source, a.source),
            "account_id": a.account_id,
            "account_name": a.account_name,
            "currency": a.currency,
            "spend": a.spend,
            "spend_company": a.spend_company,
            "fx_rate": a.fx_rate,
            "fx_rate_date": a.fx_rate_date.isoformat() if a.fx_rate_date else None,
            "impressions": a.impressions,
            "clicks": a.clicks,
            "purchases": a.purchases,
            "purchase_value": a.purchase_value,
            "platform_roas": round(roas, 4) if roas is not None else None,
            "currency_mismatch": a.spend_company is None,
        })
        src = by_source.setdefault(a.source, {
            "source": a.source,
            "source_label": AD_SOURCE_LABELS.get(a.source, a.source),
            "spend_company": 0.0,
            "purchase_value_company": 0.0,
            "has_purchase_value": False,
            "complete": True,
        })
        if a.spend_company is None:
            src["complete"] = False
        else:
            src["spend_company"] += a.spend_company
            if a.purchase_value is not None:
                rate = (a.spend_company / a.spend) if a.spend else (a.fx_rate or (1.0 if a.currency == company_currency else None))
                if rate is not None:
                    src["purchase_value_company"] += a.purchase_value * rate
                    src["has_purchase_value"] = True

    sources = []
    for src in by_source.values():
        spend = round(src["spend_company"], 2) if src["complete"] else None
        value = round(src["purchase_value_company"], 2) if src["complete"] and src["has_purchase_value"] else None
        sources.append({
            "source": src["source"],
            "source_label": src["source_label"],
            "spend": spend,
            "platform_purchase_value": value,
            "platform_roas": round(value / spend, 4) if value is not None and spend else None,
        })

    mismatched = [a for a in accounts if a["currency_mismatch"]]
    return {
        "company_currency": company_currency,
        "accounts": accounts,
        "sources": sources,
        "total": round(sum(a.spend_company for a in ads), 2) if ads and not mismatched else None,
        "currency_mismatch": [
            {"source_label": a["source_label"], "account_id": a["account_id"], "currency": a["currency"], "spend": a["spend"]}
            for a in mismatched
        ],
        "marketing_spend_source": marketing_source,
        "manual_override": marketing_source == MANUAL and bool(ads),
    }
