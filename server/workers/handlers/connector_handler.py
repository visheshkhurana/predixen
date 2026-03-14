import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def handle_connector_sync(payload: Dict[str, Any]) -> Dict[str, Any]:
    from server.core.db import SessionLocal
    from server.core.cache import cache_delete, cache_key

    company_id = payload.get("company_id")
    connector_type = payload.get("connector_type")
    config_id = payload.get("config_id")

    logger.info(f"Starting connector sync: {connector_type} for company {company_id}")

    db = SessionLocal()
    try:
        from server.connectors import load_all_connectors
        connectors = load_all_connectors()

        connector_cls = connectors.get(connector_type)
        if not connector_cls:
            raise ValueError(f"Unknown connector type: {connector_type}")

        from server.models.company import Company
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise ValueError(f"Company {company_id} not found")

        connector = connector_cls()
        credentials = payload.get("credentials", {})
        connector.authenticate(credentials)

        result = connector.sync_all()

        if result:
            financials = connector.map_to_financials(result)
            if financials:
                from server.models.financial import FinancialRecord
                from datetime import date
                record = FinancialRecord(
                    company_id=company_id,
                    period_start=financials.get("period_start", date.today().replace(day=1)),
                    period_end=financials.get("period_end", date.today()),
                    revenue=financials.get("revenue", 0),
                    cogs=financials.get("cogs", 0),
                    opex=financials.get("opex", 0),
                    payroll=financials.get("payroll", 0),
                    cash_balance=financials.get("cash_balance", 0),
                    source_type=connector_type,
                )
                db.add(record)
                db.commit()

        cache_delete(cache_key("twin_state", str(company_id)))
        cache_delete(cache_key("kpis", str(company_id)))
        cache_delete(cache_key("financials", str(company_id)))

        try:
            from server.services.digital_twin import emit_twin_event
            emit_twin_event(db, company_id, "connector_sync", connector_type, {
                "connector": connector_type,
                "status": "completed",
            })
        except Exception as e:
            logger.warning(f"Failed to emit twin event: {e}")

        logger.info(f"Connector sync completed: {connector_type} for company {company_id}")
        return {"company_id": company_id, "connector": connector_type, "status": "completed"}

    except Exception as e:
        logger.error(f"Connector sync failed: {connector_type} for company {company_id}: {e}")
        raise
    finally:
        db.close()
