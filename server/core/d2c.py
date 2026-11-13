"""D2C unit economics: one definition of contribution margin for every reader.

Indian D2C founders run the business on contribution margin per order, not
MRR. The layers, all ex-GST and per period:

    net_revenue = gross_sales - discounts - rto_value - returns_value
    CM1 = net_revenue - cogs                         (product margin)
    CM2 = CM1 - fulfilment - payment_costs           (after getting it there)
    CM3 = CM2 - marketing                            (after acquiring the order)

MER (marketing efficiency ratio) = net_revenue / marketing spend, from the
store's revenue, never an ad platform's attributed revenue. Break-even MER =
net_revenue / CM2: below it, marketing costs more than the margin it buys
(CM3 < 0). It needs CM2, and is undefined when CM2 is not positive.

where

    fulfilment    = forward shipping on every shipped order
                  + reverse shipping on every RTO
                  + packaging on every shipped order
                  + reverse logistics on customer returns
    payment_costs = gateway % on prepaid net value + COD fee on delivered COD orders

RTO (return to origin) is an order that was shipped and came back undelivered,
mostly COD. It earns nothing and costs shipping both ways, which is why it is
the margin killer SaaS-shaped tools never show. Customer returns are delivered
orders sent back after delivery.

Per-order figures divide by DELIVERED orders (shipped minus RTO): a founder
asks "what do I keep on an order that actually reached someone".

Every input is optional except orders and sales. A missing cost is reported as
missing, never silently treated as zero, so the caller can say "add your
shipping cost to see CM2" instead of showing a CM2 that is really CM1.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class D2CPeriodInputs:
    """One period (usually a month) of D2C operating data, ex-GST, in base currency units."""

    orders_shipped: int
    gross_sales: float  # order value before discounts, of all shipped orders
    discounts: float = 0.0
    rto_orders: int = 0
    customer_returns_value: float = 0.0
    customer_returns_orders: int = 0
    cogs: Optional[float] = None  # landed cost of goods for DELIVERED, kept orders
    forward_shipping_per_order: Optional[float] = None
    rto_shipping_per_order: Optional[float] = None  # reverse leg; forward is already in forward_shipping
    packaging_per_order: Optional[float] = None
    return_shipping_per_order: Optional[float] = None
    cod_share: Optional[float] = None  # fraction of delivered orders paid COD, 0..1
    payment_gateway_pct: Optional[float] = None  # fraction of prepaid value, e.g. 0.02
    cod_fee_per_order: Optional[float] = None
    marketing_spend: Optional[float] = None
    new_customers: Optional[int] = None


@dataclass
class D2CUnitEconomics:
    delivered_orders: int
    net_revenue: float
    aov: Optional[float]  # net revenue per delivered order
    rto_rate: Optional[float]
    rto_cost: Optional[float]  # logistics burnt on RTO orders
    cm1: Optional[float]
    cm2: Optional[float]
    cm3: Optional[float]
    cm1_pct: Optional[float]
    cm2_pct: Optional[float]
    cm3_pct: Optional[float]
    cm1_per_order: Optional[float]
    cm2_per_order: Optional[float]
    cm3_per_order: Optional[float]
    mer: Optional[float]  # net revenue / marketing spend (blended ROAS)
    break_even_mer: Optional[float]  # MER at which CM3 is zero: net revenue / CM2
    cac: Optional[float]
    missing: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, object]:
        return dict(self.__dict__)


def _pct(part: Optional[float], whole: float) -> Optional[float]:
    if part is None or whole <= 0:
        return None
    return part / whole


def _per(total: Optional[float], count: int) -> Optional[float]:
    if total is None or count <= 0:
        return None
    return total / count


def compute_unit_economics(inp: D2CPeriodInputs) -> D2CUnitEconomics:
    if inp.orders_shipped < 0 or inp.rto_orders < 0:
        raise ValueError("order counts cannot be negative")
    if inp.rto_orders > inp.orders_shipped:
        raise ValueError("rto_orders cannot exceed orders_shipped")
    if inp.cod_share is not None and not 0 <= inp.cod_share <= 1:
        raise ValueError("cod_share must be a fraction between 0 and 1")
    if inp.payment_gateway_pct is not None and not 0 <= inp.payment_gateway_pct < 1:
        raise ValueError("payment_gateway_pct must be a fraction, e.g. 0.02 for 2%")

    missing: List[str] = []
    shipped = inp.orders_shipped
    delivered = shipped - inp.rto_orders

    net_order_value = inp.gross_sales - inp.discounts
    value_per_shipped = net_order_value / shipped if shipped else 0.0
    rto_value = value_per_shipped * inp.rto_orders
    net_revenue = net_order_value - rto_value - inp.customer_returns_value

    # CM1
    if inp.cogs is None:
        missing.append("cogs")
        cm1 = None
    else:
        cm1 = net_revenue - inp.cogs

    # Fulfilment
    fulfilment: Optional[float] = 0.0
    rto_cost: Optional[float] = 0.0
    if inp.forward_shipping_per_order is None:
        missing.append("forward_shipping_per_order")
        fulfilment = None
        rto_cost = None
    else:
        fulfilment += inp.forward_shipping_per_order * shipped
        rto_cost += inp.forward_shipping_per_order * inp.rto_orders
    if inp.rto_orders:
        if inp.rto_shipping_per_order is None:
            missing.append("rto_shipping_per_order")
            fulfilment = None
            rto_cost = None
        elif fulfilment is not None:
            fulfilment += inp.rto_shipping_per_order * inp.rto_orders
            rto_cost += inp.rto_shipping_per_order * inp.rto_orders
    if inp.packaging_per_order is not None:
        if fulfilment is not None:
            fulfilment += inp.packaging_per_order * shipped
        if rto_cost is not None:
            rto_cost += inp.packaging_per_order * inp.rto_orders
    if inp.customer_returns_orders and inp.return_shipping_per_order is not None and fulfilment is not None:
        fulfilment += inp.return_shipping_per_order * inp.customer_returns_orders

    # Payment costs, on delivered orders only (an RTO is never paid for).
    payment: Optional[float] = None
    if inp.cod_share is None or (inp.payment_gateway_pct is None and inp.cod_fee_per_order is None):
        missing.append("payment_costs")
    else:
        net_delivered_value = value_per_shipped * delivered
        prepaid_value = net_delivered_value * (1 - inp.cod_share)
        cod_orders = delivered * inp.cod_share
        payment = (inp.payment_gateway_pct or 0.0) * prepaid_value + (inp.cod_fee_per_order or 0.0) * cod_orders

    cm2 = cm1 - fulfilment - payment if None not in (cm1, fulfilment, payment) else None

    if inp.marketing_spend is None:
        missing.append("marketing_spend")
        cm3 = None
        mer = None
    else:
        cm3 = cm2 - inp.marketing_spend if cm2 is not None else None
        mer = net_revenue / inp.marketing_spend if inp.marketing_spend > 0 else None

    cac = None
    if inp.marketing_spend is not None and inp.new_customers:
        cac = inp.marketing_spend / inp.new_customers

    return D2CUnitEconomics(
        delivered_orders=delivered,
        net_revenue=net_revenue,
        aov=_per(net_revenue, delivered),
        rto_rate=(inp.rto_orders / shipped) if shipped else None,
        rto_cost=rto_cost,
        cm1=cm1,
        cm2=cm2,
        cm3=cm3,
        cm1_pct=_pct(cm1, net_revenue),
        cm2_pct=_pct(cm2, net_revenue),
        cm3_pct=_pct(cm3, net_revenue),
        cm1_per_order=_per(cm1, delivered),
        cm2_per_order=_per(cm2, delivered),
        cm3_per_order=_per(cm3, delivered),
        mer=mer,
        break_even_mer=(net_revenue / cm2) if cm2 is not None and cm2 > 0 else None,
        cac=cac,
        missing=missing,
    )
