"""D2C unit economics calculator (CM1 / CM2 / CM3, RTO cost, MER).

Stateless: numbers in, numbers out, nothing stored. Public on purpose so the
marketing calculator and the app share one definition (server/core/d2c.py).
The general API rate limit applies.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from server.core.d2c import D2CPeriodInputs, compute_unit_economics

router = APIRouter(prefix="/d2c", tags=["d2c"])

_MONEY = dict(ge=0, le=1e12)
_PER_ORDER = dict(ge=0, le=1e7)


class UnitEconomicsRequest(BaseModel):
    orders_shipped: int = Field(ge=0, le=100_000_000)
    gross_sales: float = Field(**_MONEY)
    discounts: float = Field(default=0, **_MONEY)
    rto_orders: int = Field(default=0, ge=0, le=100_000_000)
    customer_returns_value: float = Field(default=0, **_MONEY)
    customer_returns_orders: int = Field(default=0, ge=0, le=100_000_000)
    cogs: Optional[float] = Field(default=None, **_MONEY)
    forward_shipping_per_order: Optional[float] = Field(default=None, **_PER_ORDER)
    rto_shipping_per_order: Optional[float] = Field(default=None, **_PER_ORDER)
    packaging_per_order: Optional[float] = Field(default=None, **_PER_ORDER)
    return_shipping_per_order: Optional[float] = Field(default=None, **_PER_ORDER)
    cod_share: Optional[float] = Field(default=None, ge=0, le=1)
    payment_gateway_pct: Optional[float] = Field(default=None, ge=0, lt=1)
    cod_fee_per_order: Optional[float] = Field(default=None, **_PER_ORDER)
    marketing_spend: Optional[float] = Field(default=None, **_MONEY)
    new_customers: Optional[int] = Field(default=None, ge=0, le=100_000_000)


@router.post("/unit-economics")
def unit_economics(req: UnitEconomicsRequest) -> dict:
    try:
        result = compute_unit_economics(D2CPeriodInputs(**req.model_dump()))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return result.as_dict()


# --- Per-company months ------------------------------------------------------

import re
from datetime import date

from fastapi import Depends
from sqlalchemy.orm import Session

from server.core.company_access import get_user_company, get_user_company_role
from server.core.db import get_db
from server.core.security import get_current_user
from server.models.user import User
from server.services import d2c_months

company_router = APIRouter(tags=["d2c"])

_WRITE_ROLES = {"owner", "admin", "editor"}
_PERIOD_RE = re.compile(r"^(\d{4})-(0[1-9]|1[0-2])$")


class MonthUpdate(BaseModel):
    """Manual entry for one month. Only the fields sent are changed."""

    orders_shipped: Optional[int] = Field(default=None, ge=0, le=100_000_000)
    gross_sales: Optional[float] = Field(default=None, **_MONEY)
    discounts: Optional[float] = Field(default=None, **_MONEY)
    rto_orders: Optional[int] = Field(default=None, ge=0, le=100_000_000)
    customer_returns_value: Optional[float] = Field(default=None, **_MONEY)
    customer_returns_orders: Optional[int] = Field(default=None, ge=0, le=100_000_000)
    cogs: Optional[float] = Field(default=None, **_MONEY)
    forward_shipping_per_order: Optional[float] = Field(default=None, **_PER_ORDER)
    rto_shipping_per_order: Optional[float] = Field(default=None, **_PER_ORDER)
    packaging_per_order: Optional[float] = Field(default=None, **_PER_ORDER)
    return_shipping_per_order: Optional[float] = Field(default=None, **_PER_ORDER)
    cod_share: Optional[float] = Field(default=None, ge=0, le=1)
    payment_gateway_pct: Optional[float] = Field(default=None, ge=0, lt=1)
    cod_fee_per_order: Optional[float] = Field(default=None, **_PER_ORDER)
    marketing_spend: Optional[float] = Field(default=None, **_MONEY)
    new_customers: Optional[int] = Field(default=None, ge=0, le=100_000_000)


def _parse_period(value: str) -> date:
    match = _PERIOD_RE.fullmatch(value or "")
    if not match:
        raise HTTPException(status_code=422, detail="period must be YYYY-MM")
    return date(int(match.group(1)), int(match.group(2)), 1)


@company_router.get("/companies/{company_id}/d2c/months")
def list_company_months(
    company_id: int,
    limit: int = 12,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    get_user_company(db, company_id, current_user)
    return {"months": d2c_months.list_months(db, company_id, limit=max(1, min(limit, 36)))}


@company_router.put("/companies/{company_id}/d2c/months/{period}")
def update_company_month(
    company_id: int,
    period: str,
    update: MonthUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    if get_user_company_role(db, company_id, current_user) not in _WRITE_ROLES:
        raise HTTPException(status_code=403, detail="Editing requires editor access")
    month = _parse_period(period)
    row = d2c_months.upsert_month(
        db, company_id, month, update.model_dump(exclude_unset=True), source=d2c_months.MANUAL
    )
    view = d2c_months.month_view(row)
    if view["error"]:
        db.rollback()
        raise HTTPException(status_code=422, detail=view["error"])
    db.commit()
    return view
