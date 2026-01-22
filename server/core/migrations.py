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


def ensure_invites_table(engine: Engine) -> None:
    """Ensure the invites table exists."""
    with engine.connect() as conn:
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS invites (
                    id SERIAL PRIMARY KEY,
                    email VARCHAR(255) NOT NULL,
                    token VARCHAR(64) UNIQUE NOT NULL,
                    role VARCHAR(20) DEFAULT 'viewer',
                    invited_by_id INTEGER NOT NULL REFERENCES users(id),
                    accepted BOOLEAN DEFAULT FALSE,
                    accepted_at TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_invites_email ON invites(email)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_invites_token ON invites(token)"))
            conn.commit()
            logger.info("Invites table migration complete")
        except Exception as e:
            logger.debug(f"Invites table may already exist: {e}")


def ensure_company_metadata_column(engine: Engine) -> None:
    """Ensure the metadata_json column exists in companies table for CKB storage."""
    with engine.connect() as conn:
        try:
            conn.execute(text(
                "ALTER TABLE companies ADD COLUMN IF NOT EXISTS metadata_json JSONB DEFAULT '{}'"
            ))
            conn.commit()
            logger.info("Companies metadata_json column migration complete")
        except Exception as e:
            logger.debug(f"metadata_json column may already exist: {e}")


def ensure_company_decisions_table(engine: Engine) -> None:
    """Ensure the company_decisions table exists for copilot decision tracking."""
    with engine.connect() as conn:
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS company_decisions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    company_id INTEGER NOT NULL REFERENCES companies(id),
                    title VARCHAR(500) NOT NULL,
                    context TEXT,
                    options_json JSONB DEFAULT '[]'::jsonb,
                    recommendation_json JSONB DEFAULT '{}'::jsonb,
                    status VARCHAR(50) DEFAULT 'proposed',
                    owner VARCHAR(255),
                    tags JSONB DEFAULT '[]'::jsonb,
                    confidence VARCHAR(20) DEFAULT 'medium',
                    sources_json JSONB DEFAULT '[]'::jsonb,
                    created_from_message_id UUID,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_company_decisions_company ON company_decisions(company_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_company_decisions_status ON company_decisions(status)"))
            conn.commit()
            logger.info("Company decisions table migration complete")
        except Exception as e:
            logger.debug(f"Company decisions table may already exist: {e}")


def ensure_company_scenarios_table(engine: Engine) -> None:
    """Ensure the company_scenarios table exists for scenario forking."""
    with engine.connect() as conn:
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS company_scenarios (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    company_id INTEGER NOT NULL REFERENCES companies(id),
                    name VARCHAR(255) NOT NULL,
                    base_scenario_id UUID REFERENCES company_scenarios(id),
                    assumptions_json JSONB DEFAULT '{}'::jsonb,
                    outputs_json JSONB DEFAULT '{}'::jsonb,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_company_scenarios_company ON company_scenarios(company_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_company_scenarios_base ON company_scenarios(base_scenario_id)"))
            conn.commit()
            logger.info("Company scenarios table migration complete")
        except Exception as e:
            logger.debug(f"Company scenarios table may already exist: {e}")


def run_migrations(engine: Engine) -> None:
    """Run all pending migrations."""
    logger.info("Running database migrations...")
    ensure_financial_record_columns(engine)
    ensure_invites_table(engine)
    ensure_company_metadata_column(engine)
    ensure_company_decisions_table(engine)
    ensure_company_scenarios_table(engine)
    logger.info("Database migrations completed successfully")
