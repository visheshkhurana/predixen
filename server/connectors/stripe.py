"""
Stripe connector for payment and revenue data integration.

Provides:
- Revenue and payment transaction data
- Subscription MRR/ARR metrics
- Customer payment data
- Invoice and billing information
- Refund tracking
- Customer count and churn metrics
- ARPU calculation
- Monthly revenue breakdown (last 12 months)
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import calendar
import logging
import httpx
import base64

from .base import (
    BaseConnector,
    ConnectorConfig,
    ProviderCategory,
    AuthType,
    SyncResult,
    InvoiceRecord,
    LedgerEntry,
    EmployeeRecord,
    PayrollRunRecord,
)
from .registry import ConnectorRegistry

logger = logging.getLogger(__name__)


@ConnectorRegistry.register
class StripeConnector(BaseConnector):
    PROVIDER_ID = "stripe"
    PROVIDER_NAME = "Stripe"
    PROVIDER_DESCRIPTION = "Payment processing and subscription billing platform. Import revenue, MRR/ARR, and customer payment data."
    PROVIDER_CATEGORY = ProviderCategory.ACCOUNTING
    AUTH_TYPE = AuthType.API_KEY
    DOCS_URL = "https://stripe.com/docs/api"

    SUPPORTS_EMPLOYEES = False
    SUPPORTS_PAYROLL = False
    SUPPORTS_LEDGER = True
    SUPPORTS_INVOICES = True

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.api_key = config.credentials.get("api_key") or config.credentials.get("secret_key")
        self.base_url = "https://api.stripe.com/v1"
        self.client: Optional[httpx.AsyncClient] = None

    def _get_auth_header(self) -> Dict[str, str]:
        encoded = base64.b64encode(f"{self.api_key}:".encode()).decode()
        return {
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

    async def _get_client(self) -> httpx.AsyncClient:
        if self.client is None or self.client.is_closed:
            self.client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=self._get_auth_header(),
                timeout=30.0,
            )
        return self.client

    async def authenticate(self) -> bool:
        if not self.api_key:
            logger.warning("Stripe API key not provided")
            return False
        try:
            client = await self._get_client()
            response = await client.get("/balance")
            if response.status_code == 200:
                self._authenticated = True
                logger.info("Stripe authentication successful")
                return True
            else:
                logger.warning(f"Stripe auth failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Stripe auth error: {e}")
            return False

    async def test_connection(self) -> bool:
        return await self.authenticate()

    async def fetch_invoices(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[InvoiceRecord]:
        client = await self._get_client()
        invoices = []
        params: Dict[str, Any] = {"limit": 100}
        if start_date:
            params["created[gte]"] = int(start_date.timestamp())
        if end_date:
            params["created[lte]"] = int(end_date.timestamp())

        try:
            has_more = True
            while has_more:
                response = await client.get("/invoices", params=params)
                if response.status_code != 200:
                    logger.warning(f"Stripe invoices fetch failed: {response.status_code}")
                    break
                data = response.json()
                for inv in data.get("data", []):
                    amount = (inv.get("amount_paid", 0) or 0) / 100.0
                    tax = (inv.get("tax", 0) or 0) / 100.0
                    total = (inv.get("total", 0) or 0) / 100.0
                    status_map = {"paid": "paid", "open": "pending", "void": "cancelled", "draft": "draft"}
                    invoices.append(InvoiceRecord(
                        external_id=inv.get("id", ""),
                        date=datetime.fromtimestamp(inv.get("created", 0)),
                        due_date=datetime.fromtimestamp(inv["due_date"]) if inv.get("due_date") else None,
                        customer_name=inv.get("customer_name") or inv.get("customer_email", ""),
                        amount=amount,
                        tax=tax,
                        total=total,
                        currency=(inv.get("currency") or "usd").upper(),
                        status=status_map.get(inv.get("status", ""), inv.get("status", "unknown")),
                        metadata={"stripe_id": inv.get("id"), "subscription": inv.get("subscription")},
                    ))
                has_more = data.get("has_more", False)
                if has_more and data.get("data"):
                    params["starting_after"] = data["data"][-1]["id"]
                else:
                    has_more = False
        except Exception as e:
            logger.error(f"Error fetching Stripe invoices: {e}")
        return invoices

    async def fetch_ledger(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[LedgerEntry]:
        client = await self._get_client()
        entries = []
        params: Dict[str, Any] = {"limit": 100, "type": "charge"}
        if start_date:
            params["created[gte]"] = int(start_date.timestamp())
        if end_date:
            params["created[lte]"] = int(end_date.timestamp())

        try:
            response = await client.get("/balance_transactions", params=params)
            if response.status_code == 200:
                data = response.json()
                for txn in data.get("data", []):
                    amount = (txn.get("amount", 0) or 0) / 100.0
                    fee = (txn.get("fee", 0) or 0) / 100.0
                    net = (txn.get("net", 0) or 0) / 100.0
                    entries.append(LedgerEntry(
                        external_id=txn.get("id", ""),
                        date=datetime.fromtimestamp(txn.get("created", 0)),
                        account_code="STRIPE_REVENUE",
                        account_name="Stripe Revenue",
                        debit=0.0,
                        credit=amount,
                        description=txn.get("description") or f"Stripe {txn.get('type', 'charge')}",
                        category="revenue",
                        metadata={"fee": fee, "net": net, "type": txn.get("type")},
                    ))
        except Exception as e:
            logger.error(f"Error fetching Stripe balance transactions: {e}")
        return entries

    async def get_mrr(self) -> float:
        client = await self._get_client()
        mrr = 0.0
        try:
            params: Dict[str, Any] = {"status": "active", "limit": 100}
            has_more = True
            while has_more:
                response = await client.get("/subscriptions", params=params)
                if response.status_code != 200:
                    logger.warning(f"Stripe subscriptions fetch failed: {response.status_code}")
                    break
                data = response.json()
                for sub in data.get("data", []):
                    for item in sub.get("items", {}).get("data", []):
                        price = item.get("price", {})
                        amount = (price.get("unit_amount", 0) or 0) / 100.0
                        interval = price.get("recurring", {}).get("interval", "month")
                        qty = item.get("quantity", 1) or 1
                        if interval == "year":
                            mrr += (amount * qty) / 12
                        elif interval == "month":
                            mrr += amount * qty
                        elif interval == "week":
                            mrr += amount * qty * 4.33
                has_more = data.get("has_more", False)
                if has_more and data.get("data"):
                    params["starting_after"] = data["data"][-1]["id"]
                else:
                    has_more = False
        except Exception as e:
            logger.error(f"Error calculating Stripe MRR: {e}")
        return mrr

    async def get_arr(self) -> float:
        return await self.get_mrr() * 12

    async def get_refunds(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        client = await self._get_client()
        params: Dict[str, Any] = {"limit": 100}
        if start_date:
            params["created[gte]"] = int(start_date.timestamp())
        if end_date:
            params["created[lte]"] = int(end_date.timestamp())

        total_refund_amount = 0.0
        refund_count = 0

        try:
            has_more = True
            while has_more:
                response = await client.get("/refunds", params=params)
                if response.status_code != 200:
                    logger.warning(f"Stripe refunds fetch failed: {response.status_code}")
                    break
                data = response.json()
                for refund in data.get("data", []):
                    total_refund_amount += (refund.get("amount", 0) or 0) / 100.0
                    refund_count += 1
                has_more = data.get("has_more", False)
                if has_more and data.get("data"):
                    params["starting_after"] = data["data"][-1]["id"]
                else:
                    has_more = False
        except Exception as e:
            logger.error(f"Error fetching Stripe refunds: {e}")

        return {
            "total_refund_amount": total_refund_amount,
            "refund_count": refund_count,
        }

    async def get_customer_count(self) -> Dict[str, Any]:
        client = await self._get_client()
        total_customers = 0
        new_customers_30d = 0
        thirty_days_ago = int((datetime.utcnow() - timedelta(days=30)).timestamp())

        try:
            response = await client.get("/customers", params={"limit": 1})
            if response.status_code == 200:
                data = response.json()
                total_customers = data.get("total_count", 0)
                if total_customers == 0 and data.get("data"):
                    params: Dict[str, Any] = {"limit": 100}
                    has_more = True
                    count = 0
                    while has_more:
                        resp = await client.get("/customers", params=params)
                        if resp.status_code != 200:
                            break
                        d = resp.json()
                        count += len(d.get("data", []))
                        has_more = d.get("has_more", False)
                        if has_more and d.get("data"):
                            params["starting_after"] = d["data"][-1]["id"]
                        else:
                            has_more = False
                    total_customers = count

            new_resp = await client.get("/customers", params={
                "limit": 100,
                "created[gte]": thirty_days_ago,
            })
            if new_resp.status_code == 200:
                new_data = new_resp.json()
                new_customers_30d = len(new_data.get("data", []))
                if new_data.get("has_more", False):
                    has_more = True
                    params_new: Dict[str, Any] = {
                        "limit": 100,
                        "created[gte]": thirty_days_ago,
                    }
                    while has_more:
                        if new_data.get("data"):
                            params_new["starting_after"] = new_data["data"][-1]["id"]
                        resp = await client.get("/customers", params=params_new)
                        if resp.status_code != 200:
                            break
                        new_data = resp.json()
                        new_customers_30d += len(new_data.get("data", []))
                        has_more = new_data.get("has_more", False)
        except Exception as e:
            logger.error(f"Error fetching Stripe customer count: {e}")

        return {
            "total_customers": total_customers,
            "new_customers_30d": new_customers_30d,
        }

    async def get_churn_metrics(self) -> Dict[str, Any]:
        client = await self._get_client()
        canceled_count = 0
        active_count = 0
        thirty_days_ago = int((datetime.utcnow() - timedelta(days=30)).timestamp())

        try:
            params_c: Dict[str, Any] = {
                "status": "canceled",
                "limit": 100,
            }
            has_more = True
            while has_more:
                canceled_resp = await client.get("/subscriptions", params=params_c)
                if canceled_resp.status_code != 200:
                    break
                canceled_data = canceled_resp.json()
                for sub in canceled_data.get("data", []):
                    canceled_at = sub.get("canceled_at") or sub.get("ended_at")
                    if canceled_at and canceled_at >= thirty_days_ago:
                        canceled_count += 1
                has_more = canceled_data.get("has_more", False)
                if has_more and canceled_data.get("data"):
                    params_c["starting_after"] = canceled_data["data"][-1]["id"]
                else:
                    has_more = False

            all_params: Dict[str, Any] = {"status": "active", "limit": 100}
            has_more_a = True
            while has_more_a:
                a_resp = await client.get("/subscriptions", params=all_params)
                if a_resp.status_code != 200:
                    break
                a_data = a_resp.json()
                active_count += len(a_data.get("data", []))
                has_more_a = a_data.get("has_more", False)
                if has_more_a and a_data.get("data"):
                    all_params["starting_after"] = a_data["data"][-1]["id"]
                else:
                    has_more_a = False
        except Exception as e:
            logger.error(f"Error fetching Stripe churn metrics: {e}")

        total_base = active_count + canceled_count
        churn_rate = (canceled_count / total_base * 100) if total_base > 0 else 0.0

        return {
            "canceled_subscriptions_30d": canceled_count,
            "active_subscriptions": active_count,
            "churn_rate_pct": round(churn_rate, 2),
        }

    async def get_monthly_revenue_breakdown(self, months: int = 12) -> List[Dict[str, Any]]:
        client = await self._get_client()
        breakdown: List[Dict[str, Any]] = []
        now = datetime.utcnow()

        try:
            for i in range(months - 1, -1, -1):
                month_offset = now.month - i
                year = now.year + (month_offset - 1) // 12
                month = ((month_offset - 1) % 12) + 1
                _, last_day = calendar.monthrange(year, month)
                start = datetime(year, month, 1)
                end = datetime(year, month, last_day, 23, 59, 59)

                params: Dict[str, Any] = {
                    "limit": 100,
                    "created[gte]": int(start.timestamp()),
                    "created[lte]": int(end.timestamp()),
                }

                month_revenue = 0.0
                month_count = 0
                has_more = True
                while has_more:
                    response = await client.get("/charges", params=params)
                    if response.status_code != 200:
                        break
                    data = response.json()
                    for charge in data.get("data", []):
                        if charge.get("paid") and not charge.get("refunded"):
                            month_revenue += (charge.get("amount", 0) or 0) / 100.0
                            month_count += 1
                    has_more = data.get("has_more", False)
                    if has_more and data.get("data"):
                        params["starting_after"] = data["data"][-1]["id"]
                    else:
                        has_more = False

                breakdown.append({
                    "month": start.strftime("%Y-%m"),
                    "revenue": round(month_revenue, 2),
                    "transaction_count": month_count,
                })
        except Exception as e:
            logger.error(f"Error fetching Stripe monthly revenue breakdown: {e}")

        return breakdown

    async def get_revenue_metrics(self) -> Dict[str, Any]:
        client = await self._get_client()
        metrics: Dict[str, Any] = {
            "mrr": 0.0,
            "arr": 0.0,
            "total_revenue": 0.0,
            "active_subscriptions": 0,
            "new_customers": 0,
            "new_customers_30d": 0,
            "total_customers": 0,
            "churned_customers": 0,
            "churn_rate_pct": 0.0,
            "arpu": 0.0,
            "total_refund_amount": 0.0,
            "refund_count": 0,
            "monthly_revenue_breakdown": [],
        }
        try:
            mrr = await self.get_mrr()
            metrics["mrr"] = mrr
            metrics["arr"] = mrr * 12

            churn_data = await self.get_churn_metrics()
            metrics["churned_customers"] = churn_data["canceled_subscriptions_30d"]
            metrics["churn_rate_pct"] = churn_data["churn_rate_pct"]
            metrics["active_subscriptions"] = churn_data["active_subscriptions"]

            customer_data = await self.get_customer_count()
            metrics["total_customers"] = customer_data["total_customers"]
            metrics["new_customers"] = customer_data["new_customers_30d"]
            metrics["new_customers_30d"] = customer_data["new_customers_30d"]

            if metrics["total_customers"] > 0:
                metrics["arpu"] = round(mrr / metrics["total_customers"], 2)

            refund_data = await self.get_refunds()
            metrics["total_refund_amount"] = refund_data["total_refund_amount"]
            metrics["refund_count"] = refund_data["refund_count"]

            monthly_breakdown = await self.get_monthly_revenue_breakdown()
            metrics["monthly_revenue_breakdown"] = monthly_breakdown
            metrics["total_revenue"] = sum(m["revenue"] for m in monthly_breakdown)
        except Exception as e:
            logger.error(f"Error getting Stripe revenue metrics: {e}")
        return metrics

    async def sync_all(self) -> SyncResult:
        sync_started = datetime.utcnow()
        errors = []
        total_records = 0

        try:
            if not await self.authenticate():
                return SyncResult(
                    success=False,
                    provider_id=self.PROVIDER_ID,
                    sync_type="full",
                    errors=["Authentication failed - check your Stripe API key"],
                    sync_started=sync_started,
                )

            invoices = await self.fetch_invoices()
            total_records += len(invoices)

            ledger = await self.fetch_ledger()
            total_records += len(ledger)

            mrr = await self.get_mrr()

            refund_data = await self.get_refunds()
            total_records += refund_data["refund_count"]

            customer_data = await self.get_customer_count()
            churn_data = await self.get_churn_metrics()
            monthly_breakdown = await self.get_monthly_revenue_breakdown()

            financials = self.map_to_financials(
                invoices=invoices,
                ledger_entries=ledger,
            )
            financials["mrr"] = mrr
            financials["arr"] = mrr * 12
            financials["total_refund_amount"] = refund_data["total_refund_amount"]
            financials["refund_count"] = refund_data["refund_count"]
            financials["total_customers"] = customer_data["total_customers"]
            financials["new_customers_30d"] = customer_data["new_customers_30d"]
            financials["canceled_subscriptions_30d"] = churn_data["canceled_subscriptions_30d"]
            financials["active_subscriptions"] = churn_data["active_subscriptions"]
            financials["churn_rate_pct"] = churn_data["churn_rate_pct"]
            financials["arpu"] = round(mrr / customer_data["total_customers"], 2) if customer_data["total_customers"] > 0 else 0.0
            financials["monthly_revenue_breakdown"] = monthly_breakdown

            self._last_sync = datetime.utcnow()

            return SyncResult(
                success=len(errors) == 0,
                provider_id=self.PROVIDER_ID,
                sync_type="full",
                records_synced=total_records,
                errors=errors,
                sync_started=sync_started,
                sync_completed=datetime.utcnow(),
                metadata={"financials": financials},
            )
        except Exception as e:
            logger.error(f"Stripe sync failed: {e}")
            return SyncResult(
                success=False,
                provider_id=self.PROVIDER_ID,
                sync_type="full",
                errors=[str(e)],
                sync_started=sync_started,
                sync_completed=datetime.utcnow(),
            )

    async def close(self):
        if self.client and not self.client.is_closed:
            await self.client.aclose()
            self.client = None
