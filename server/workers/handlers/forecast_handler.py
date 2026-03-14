import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def handle_forecast(payload: Dict[str, Any]) -> Dict[str, Any]:
    from server.core.db import SessionLocal
    from server.core.cache import cache_delete, cache_key

    company_id = payload.get("company_id")
    forecast_type = payload.get("type", "holt_winters")
    horizon = payload.get("horizon_months", 12)

    logger.info(f"Running forecast ({forecast_type}) for company {company_id}")

    db = SessionLocal()
    try:
        from server.forecasting.engine import ForecastEngine
        engine = ForecastEngine()

        from server.models.financial import FinancialRecord
        records = (
            db.query(FinancialRecord)
            .filter(FinancialRecord.company_id == company_id)
            .order_by(FinancialRecord.period_start.asc())
            .all()
        )

        if not records:
            return {"company_id": company_id, "status": "no_data"}

        revenue_series = [r.revenue or 0 for r in records]
        result = engine.forecast(revenue_series, horizon=horizon, method=forecast_type)

        cache_delete(cache_key("forecast", str(company_id)))

        logger.info(f"Forecast completed for company {company_id}")
        return {"company_id": company_id, "status": "completed", "forecast": result}

    except Exception as e:
        logger.error(f"Forecast failed for company {company_id}: {e}")
        raise
    finally:
        db.close()
