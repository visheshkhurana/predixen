"""Database migration helpers for adding new columns to existing tables."""
import logging
from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

def ensure_financial_record_columns(engine: Engine) -> None:
    """Ensure all required columns exist in financial_records table.
    
    This handles the case where the table was created before new columns were added.
    Uses IF NOT EXISTS to be idempotent.
    """
    new_columns = [
        ('mrr', 'FLOAT'),
        ('arr', 'FLOAT'),
        ('gross_profit', 'FLOAT'),
        ('gross_margin', 'FLOAT'),
        ('operating_income', 'FLOAT'),
        ('operating_margin', 'FLOAT'),
        ('net_burn', 'FLOAT'),
        ('burn_multiple', 'FLOAT'),  # Can be negative (e.g., -0.7)
        ('runway_months', 'FLOAT'),
        ('headcount', 'INTEGER'),
        ('customers', 'INTEGER'),
        ('mom_growth', 'FLOAT'),
        ('yoy_growth', 'FLOAT'),
        ('ndr', 'FLOAT'),
        ('ltv', 'FLOAT'),
        ('cac', 'FLOAT'),
        ('ltv_cac_ratio', 'FLOAT'),
        ('arpu', 'FLOAT'),
        ('marketing_expense', 'FLOAT'),
        ('source_type', 'VARCHAR(20)'),
        ('extraction_summary', 'TEXT'),
    ]
    
    with engine.connect() as conn:
        for col_name, col_type in new_columns:
            try:
                conn.execute(text(
                    f'ALTER TABLE financial_records ADD COLUMN IF NOT EXISTS {col_name} {col_type}'
                ))
            except Exception as e:
                logger.debug(f"Column {col_name} may already exist or error: {e}")
        conn.commit()
    
    logger.info("Financial records schema migration complete")


def run_migrations(engine: Engine) -> None:
    """Run all pending migrations."""
    logger.info("Running database migrations...")
    ensure_financial_record_columns(engine)
    logger.info("Database migrations completed successfully")
