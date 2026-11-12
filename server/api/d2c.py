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
