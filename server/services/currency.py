"""
Multi-currency service: cached exchange rates, conversion utilities.
Uses frankfurter.app (free, no API key, ECB rates) as primary source.
Falls back to static rates if API is unavailable.
"""
import httpx
import logging
from datetime import date, datetime, timedelta
from typing import Optional, Dict, List, Tuple
from sqlalchemy.orm import Session

from server.models.exchange_rate import ExchangeRate

logger = logging.getLogger(__name__)

SUPPORTED_CURRENCIES = [
    "USD", "EUR", "GBP", "INR", "CAD", "AUD", "SGD", "JPY",
    "AED", "CHF", "CNY", "HKD", "NZD", "SEK", "NOK", "DKK",
    "BRL", "MXN", "ZAR", "KRW", "THB", "IDR", "MYR", "PHP",
    "TWD", "ILS", "PLN", "CZK", "HUF", "TRY", "RON", "BGN",
    "ISK",
]

CURRENCY_SYMBOLS = {
    "USD": "$", "EUR": "\u20ac", "GBP": "\u00a3", "INR": "\u20b9",
    "CAD": "C$", "AUD": "A$", "SGD": "S$", "JPY": "\u00a5",
    "AED": "AED", "CHF": "CHF", "CNY": "\u00a5", "HKD": "HK$",
    "NZD": "NZ$", "SEK": "kr", "NOK": "kr", "DKK": "kr",
    "BRL": "R$", "MXN": "MX$", "ZAR": "R", "KRW": "\u20a9",
    "THB": "\u0e3f", "IDR": "Rp", "MYR": "RM", "PHP": "\u20b1",
    "TWD": "NT$", "ILS": "\u20aa", "PLN": "z\u0142", "CZK": "K\u010d",
    "HUF": "Ft", "TRY": "\u20ba", "RON": "lei", "BGN": "лв",
    "ISK": "kr",
}

CURRENCY_NAMES = {
    "USD": "US Dollar", "EUR": "Euro", "GBP": "British Pound",
    "INR": "Indian Rupee", "CAD": "Canadian Dollar", "AUD": "Australian Dollar",
    "SGD": "Singapore Dollar", "JPY": "Japanese Yen", "AED": "UAE Dirham",
    "CHF": "Swiss Franc", "CNY": "Chinese Yuan", "HKD": "Hong Kong Dollar",
    "NZD": "New Zealand Dollar", "SEK": "Swedish Krona", "NOK": "Norwegian Krone",
    "DKK": "Danish Krone", "BRL": "Brazilian Real", "MXN": "Mexican Peso",
    "ZAR": "South African Rand", "KRW": "South Korean Won", "THB": "Thai Baht",
    "IDR": "Indonesian Rupiah", "MYR": "Malaysian Ringgit", "PHP": "Philippine Peso",
    "TWD": "Taiwan Dollar", "ILS": "Israeli Shekel", "PLN": "Polish Zloty",
    "CZK": "Czech Koruna", "HUF": "Hungarian Forint", "TRY": "Turkish Lira",
    "RON": "Romanian Leu", "BGN": "Bulgarian Lev", "ISK": "Icelandic Krona",
}

STATIC_RATES_USD = {
    "USD": 1.0, "EUR": 0.92, "GBP": 0.79, "INR": 83.5,
    "CAD": 1.36, "AUD": 1.53, "SGD": 1.34, "JPY": 149.5,
    "AED": 3.67, "CHF": 0.88, "CNY": 7.24, "HKD": 7.82,
    "NZD": 1.64, "SEK": 10.45, "NOK": 10.62, "DKK": 6.87,
    "BRL": 4.97, "MXN": 17.15, "ZAR": 18.75, "KRW": 1325.0,
    "THB": 35.2, "IDR": 15650.0, "MYR": 4.72, "PHP": 56.2,
    "TWD": 31.5, "ILS": 3.65, "PLN": 4.02, "CZK": 22.8,
    "HUF": 355.0, "TRY": 30.5, "RON": 4.58, "BGN": 1.80,
    "ISK": 137.5,
}

_rate_cache: Dict[str, Tuple[float, datetime]] = {}
CACHE_TTL_HOURS = 6


async def fetch_live_rates(base: str = "USD") -> Optional[Dict[str, float]]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"https://api.frankfurter.app/latest?from={base}"
            )
            if resp.status_code == 200:
                data = resp.json()
                rates = data.get("rates", {})
                rates[base] = 1.0
                return rates
    except Exception as e:
        logger.warning(f"Failed to fetch live rates: {e}")
    return None


def get_static_rate(from_currency: str, to_currency: str) -> float:
    if from_currency == to_currency:
        return 1.0
    from_usd = STATIC_RATES_USD.get(from_currency, 1.0)
    to_usd = STATIC_RATES_USD.get(to_currency, 1.0)
    return to_usd / from_usd


def convert_amount(
    amount: float,
    from_currency: str,
    to_currency: str,
    rate: Optional[float] = None,
) -> Tuple[float, float]:
    if from_currency == to_currency:
        return amount, 1.0
    if rate is None:
        rate = get_static_rate(from_currency, to_currency)
    return round(amount * rate, 2), rate


async def refresh_rates(db: Session, base: str = "USD") -> Dict[str, float]:
    live = await fetch_live_rates(base)
    rates = live if live else dict(STATIC_RATES_USD)
    source = "ecb_live" if live else "static_fallback"
    today = date.today()

    for quote, rate_val in rates.items():
        if quote == base:
            continue
        existing = db.query(ExchangeRate).filter(
            ExchangeRate.base_currency == base,
            ExchangeRate.quote_currency == quote,
            ExchangeRate.rate_date == today,
        ).first()
        if existing:
            existing.rate = rate_val
            existing.source = source
            existing.fetched_at = datetime.utcnow()
        else:
            db.add(ExchangeRate(
                base_currency=base,
                quote_currency=quote,
                rate=rate_val,
                rate_date=today,
                source=source,
            ))

    db.commit()
    logger.info(f"Refreshed {len(rates)} exchange rates ({source})")
    return rates


def get_rate_from_db(
    db: Session, from_currency: str, to_currency: str, as_of: Optional[date] = None
) -> Optional[float]:
    if from_currency == to_currency:
        return 1.0

    target_date = as_of or date.today()

    direct = db.query(ExchangeRate).filter(
        ExchangeRate.base_currency == from_currency,
        ExchangeRate.quote_currency == to_currency,
        ExchangeRate.rate_date <= target_date,
    ).order_by(ExchangeRate.rate_date.desc()).first()

    if direct:
        return direct.rate

    from_usd = db.query(ExchangeRate).filter(
        ExchangeRate.base_currency == "USD",
        ExchangeRate.quote_currency == from_currency,
        ExchangeRate.rate_date <= target_date,
    ).order_by(ExchangeRate.rate_date.desc()).first()

    to_usd = db.query(ExchangeRate).filter(
        ExchangeRate.base_currency == "USD",
        ExchangeRate.quote_currency == to_currency,
        ExchangeRate.rate_date <= target_date,
    ).order_by(ExchangeRate.rate_date.desc()).first()

    if from_usd and to_usd and from_usd.rate > 0:
        return to_usd.rate / from_usd.rate

    return None


def get_best_rate(
    db: Session, from_currency: str, to_currency: str, as_of: Optional[date] = None
) -> Tuple[float, str]:
    if from_currency == to_currency:
        return 1.0, "identity"

    db_rate = get_rate_from_db(db, from_currency, to_currency, as_of)
    if db_rate:
        return db_rate, "database"

    return get_static_rate(from_currency, to_currency), "static_fallback"


def convert_financial_record_fields(
    data: dict, rate: float
) -> dict:
    monetary_fields = [
        "revenue", "cogs", "opex", "payroll", "other_costs", "cash_balance",
        "mrr", "arr", "gross_profit", "operating_income", "net_burn",
        "ltv", "cac", "arpu", "marketing_expense",
    ]
    converted = dict(data)
    for field in monetary_fields:
        if field in converted and converted[field] is not None:
            val = converted[field]
            if isinstance(val, (int, float)) and val != 0:
                converted[field] = round(val * rate, 2)
    return converted


def get_currencies_list() -> List[dict]:
    return [
        {
            "code": code,
            "name": CURRENCY_NAMES.get(code, code),
            "symbol": CURRENCY_SYMBOLS.get(code, code),
        }
        for code in SUPPORTED_CURRENCIES
    ]
