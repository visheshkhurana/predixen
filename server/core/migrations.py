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


def ensure_company_sources_table(engine: Engine) -> None:
    """Ensure the company_sources table exists for citations."""
    with engine.connect() as conn:
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS company_sources (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    company_id INTEGER NOT NULL REFERENCES companies(id),
                    kind VARCHAR(20) NOT NULL,
                    title TEXT,
                    url TEXT,
                    doc_id TEXT,
                    page INTEGER,
                    table_id TEXT,
                    row_ref TEXT,
                    cell_ref TEXT,
                    snippet TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_company_sources_company ON company_sources(company_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_company_sources_kind ON company_sources(kind)"))
            conn.commit()
            logger.info("Company sources table migration complete")
        except Exception as e:
            logger.debug(f"Company sources table may already exist: {e}")


def ensure_company_workstreams_table(engine: Engine) -> None:
    """Ensure the company_workstreams table exists for operating cadence."""
    with engine.connect() as conn:
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS company_workstreams (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    company_id INTEGER NOT NULL REFERENCES companies(id),
                    name VARCHAR(255) NOT NULL,
                    cadence VARCHAR(20) NOT NULL,
                    enabled BOOLEAN DEFAULT TRUE,
                    config_json JSONB DEFAULT '{}'::jsonb,
                    last_run_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_company_workstreams_company ON company_workstreams(company_id)"))
            conn.commit()
            logger.info("Company workstreams table migration complete")
        except Exception as e:
            logger.debug(f"Company workstreams table may already exist: {e}")


def ensure_company_alerts_table(engine: Engine) -> None:
    """Ensure the company_alerts table exists for alerts/reminders."""
    with engine.connect() as conn:
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS company_alerts (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    company_id INTEGER NOT NULL REFERENCES companies(id),
                    type VARCHAR(50) NOT NULL,
                    severity VARCHAR(20) DEFAULT 'medium',
                    message TEXT,
                    rule_json JSONB DEFAULT '{}'::jsonb,
                    triggered_at TIMESTAMP DEFAULT NOW(),
                    resolved_at TIMESTAMP,
                    status VARCHAR(20) DEFAULT 'open'
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_company_alerts_company ON company_alerts(company_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_company_alerts_status ON company_alerts(status)"))
            conn.commit()
            logger.info("Company alerts table migration complete")
        except Exception as e:
            logger.debug(f"Company alerts table may already exist: {e}")


def ensure_company_driver_models_table(engine: Engine) -> None:
    """Ensure the company_driver_models table exists for forecasting."""
    with engine.connect() as conn:
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS company_driver_models (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    company_id INTEGER NOT NULL REFERENCES companies(id),
                    model_name VARCHAR(255) NOT NULL,
                    template VARCHAR(50) NOT NULL,
                    drivers_json JSONB DEFAULT '{}'::jsonb,
                    assumptions_json JSONB DEFAULT '{}'::jsonb,
                    outputs_json JSONB DEFAULT '{}'::jsonb,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_company_driver_models_company ON company_driver_models(company_id)"))
            conn.commit()
            logger.info("Company driver models table migration complete")
        except Exception as e:
            logger.debug(f"Company driver models table may already exist: {e}")


def ensure_llm_audit_logs_table(engine: Engine) -> None:
    """Ensure the llm_audit_logs table exists for OpenAI API audit logging."""
    with engine.connect() as conn:
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS llm_audit_logs (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    company_id INTEGER REFERENCES companies(id),
                    user_id INTEGER REFERENCES users(id),
                    endpoint TEXT NOT NULL,
                    model TEXT NOT NULL,
                    pii_mode VARCHAR(20) DEFAULT 'standard',
                    prompt_hash VARCHAR(64) NOT NULL,
                    input_chars_original INTEGER NOT NULL,
                    input_chars_redacted INTEGER NOT NULL,
                    pii_findings_json JSONB DEFAULT '[]'::jsonb,
                    redacted_prompt_preview TEXT,
                    redacted_output_preview TEXT,
                    tokens_in INTEGER,
                    tokens_out INTEGER,
                    latency_ms INTEGER,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_llm_audit_logs_company ON llm_audit_logs(company_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_llm_audit_logs_user ON llm_audit_logs(user_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_llm_audit_logs_created ON llm_audit_logs(created_at)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_llm_audit_logs_pii_mode ON llm_audit_logs(pii_mode)"))
            conn.commit()
            logger.info("LLM audit logs table migration complete")
        except Exception as e:
            logger.debug(f"LLM audit logs table may already exist: {e}")


def ensure_eval_runs_table(engine: Engine) -> None:
    """Ensure the eval_runs table exists for quality evaluation tracking."""
    with engine.connect() as conn:
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS eval_runs (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    suite_name VARCHAR(255) NOT NULL,
                    inputs_json JSONB DEFAULT '{}'::jsonb,
                    outputs_json JSONB DEFAULT '{}'::jsonb,
                    scores_json JSONB DEFAULT '{}'::jsonb,
                    overall_score FLOAT,
                    status VARCHAR(50) DEFAULT 'pending',
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    completed_at TIMESTAMP
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_eval_runs_suite ON eval_runs(suite_name)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_eval_runs_status ON eval_runs(status)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_eval_runs_created ON eval_runs(created_at)"))
            conn.commit()
            logger.info("Eval runs table migration complete")
        except Exception as e:
            logger.debug(f"Eval runs table may already exist: {e}")


def run_migrations(engine: Engine) -> None:
    """Run all pending migrations."""
    logger.info("Running database migrations...")
    ensure_financial_record_columns(engine)
    ensure_invites_table(engine)
    ensure_company_metadata_column(engine)
    ensure_company_decisions_table(engine)
    ensure_company_scenarios_table(engine)
    ensure_company_sources_table(engine)
    ensure_company_workstreams_table(engine)
    ensure_company_alerts_table(engine)
    ensure_company_driver_models_table(engine)
    ensure_llm_audit_logs_table(engine)
    ensure_eval_runs_table(engine)
    logger.info("Database migrations completed successfully")
