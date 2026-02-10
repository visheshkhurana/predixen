"""Currency management API: exchange rates, conversion, supported currencies."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date
from typing import Optional
from pydantic import BaseModel

from server.core.db import get_db
from server.core.security import get_current_user
from server.models.company import Company
from server.models.exchange_rate import ExchangeRate
from server.services.currency import (
    get_currencies_list,
    refresh_rates,
    get_best_rate,
    convert_amount,
    SUPPORTED_CURRENCIES,
    CURRENCY_SYMBOLS,
    CURRENCY_NAMES,
)

router = APIRouter(prefix="/currency", tags=["currency"])


@router.get("/supported")
def list_supported_currencies():
    return {
        "currencies": get_currencies_list(),
        "count": len(SUPPORTED_CURRENCIES),
    }


@router.get("/rates")
def get_rates(
    base: str = "USD",
    db: Session = Depends(get_db),
):
    if base not in SUPPORTED_CURRENCIES:
        raise HTTPException(400, f"Unsupported currency: {base}")

    today = date.today()
    rows = db.query(ExchangeRate).filter(
        ExchangeRate.base_currency == base,
        ExchangeRate.rate_date == today,
    ).all()

    if rows:
        rates = {r.quote_currency: r.rate for r in rows}
        rates[base] = 1.0
        source = rows[0].source if rows else "database"
    else:
        from server.services.currency import STATIC_RATES_USD, get_static_rate
        if base == "USD":
            rates = dict(STATIC_RATES_USD)
        else:
            rates = {c: get_static_rate(base, c) for c in SUPPORTED_CURRENCIES}
        source = "static_fallback"

    return {
        "base": base,
        "date": today.isoformat(),
        "source": source,
        "rates": rates,
    }


@router.post("/refresh")
async def trigger_refresh(
    base: str = "USD",
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    rates = await refresh_rates(db, base)
    return {
        "success": True,
        "base": base,
        "count": len(rates),
        "date": date.today().isoformat(),
    }


class ConvertRequest(BaseModel):
    amount: float
    from_currency: str
    to_currency: str


@router.post("/convert")
def convert(
    req: ConvertRequest,
    db: Session = Depends(get_db),
):
    if req.from_currency not in SUPPORTED_CURRENCIES:
        raise HTTPException(400, f"Unsupported: {req.from_currency}")
    if req.to_currency not in SUPPORTED_CURRENCIES:
        raise HTTPException(400, f"Unsupported: {req.to_currency}")

    rate, source = get_best_rate(db, req.from_currency, req.to_currency)
    converted, _ = convert_amount(req.amount, req.from_currency, req.to_currency, rate)

    return {
        "original": req.amount,
        "from": req.from_currency,
        "to": req.to_currency,
        "converted": converted,
        "rate": rate,
        "source": source,
    }


@router.get("/rate-history")
def rate_history(
    base: str = "USD",
    quote: str = "EUR",
    days: int = 30,
    db: Session = Depends(get_db),
):
    from datetime import timedelta
    start = date.today() - timedelta(days=days)
    rows = db.query(ExchangeRate).filter(
        ExchangeRate.base_currency == base,
        ExchangeRate.quote_currency == quote,
        ExchangeRate.rate_date >= start,
    ).order_by(ExchangeRate.rate_date).all()

    return {
        "base": base,
        "quote": quote,
        "history": [
            {"date": r.rate_date.isoformat(), "rate": r.rate, "source": r.source}
            for r in rows
        ],
    }
