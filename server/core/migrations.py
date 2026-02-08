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


def ensure_company_description_column(engine: Engine) -> None:
    """Ensure the description column exists in companies table for business summary."""
    with engine.connect() as conn:
        try:
            conn.execute(text(
                "ALTER TABLE companies ADD COLUMN IF NOT EXISTS description TEXT"
            ))
            conn.commit()
            logger.info("Companies description column migration complete")
        except Exception as e:
            logger.debug(f"description column may already exist: {e}")


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


def ensure_fundraising_tables(engine: Engine) -> None:
    """Ensure all fundraising-related tables exist."""
    with engine.connect() as conn:
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS company_cap_tables (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    company_id INTEGER NOT NULL REFERENCES companies(id),
                    name VARCHAR(255) NOT NULL DEFAULT 'Current Cap Table',
                    as_of_date DATE,
                    currency VARCHAR(10) DEFAULT 'USD',
                    cap_table_json JSONB DEFAULT '{}'::jsonb,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_cap_tables_company ON company_cap_tables(company_id)"))
            
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS fundraising_rounds (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    company_id INTEGER NOT NULL REFERENCES companies(id),
                    name VARCHAR(255) NOT NULL,
                    target_raise FLOAT,
                    pre_money FLOAT,
                    post_money FLOAT,
                    instrument VARCHAR(20) DEFAULT 'equity',
                    option_pool_refresh_percent FLOAT,
                    use_of_funds_json JSONB DEFAULT '{}'::jsonb,
                    status VARCHAR(20) DEFAULT 'planned',
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_fundraising_rounds_company ON fundraising_rounds(company_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_fundraising_rounds_status ON fundraising_rounds(status)"))
            
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS round_terms (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    round_id UUID NOT NULL REFERENCES fundraising_rounds(id),
                    terms_json JSONB DEFAULT '{}'::jsonb,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_round_terms_round ON round_terms(round_id)"))
            
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS investors (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    company_id INTEGER NOT NULL REFERENCES companies(id),
                    name VARCHAR(255) NOT NULL,
                    type VARCHAR(50) DEFAULT 'vc',
                    geography VARCHAR(100),
                    stage_focus VARCHAR(100),
                    thesis_tags JSONB DEFAULT '[]'::jsonb,
                    contact_json JSONB DEFAULT '{}'::jsonb,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_investors_company ON investors(company_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_investors_type ON investors(type)"))
            
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS investor_pipeline (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    round_id UUID NOT NULL REFERENCES fundraising_rounds(id),
                    investor_id UUID NOT NULL REFERENCES investors(id),
                    stage VARCHAR(50) DEFAULT 'sourced',
                    probability FLOAT DEFAULT 0.0,
                    last_contacted_at TIMESTAMP,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_investor_pipeline_round ON investor_pipeline(round_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_investor_pipeline_investor ON investor_pipeline(investor_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_investor_pipeline_stage ON investor_pipeline(stage)"))
            
            conn.commit()
            logger.info("Fundraising tables migration complete")
        except Exception as e:
            logger.debug(f"Fundraising tables may already exist: {e}")


def ensure_conversations_tables(engine: Engine) -> None:
    """Ensure the conversations tables exist for enhanced copilot memory."""
    with engine.connect() as conn:
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id SERIAL PRIMARY KEY,
                    company_id INTEGER NOT NULL REFERENCES companies(id),
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    title VARCHAR(255),
                    last_scenario_id INTEGER REFERENCES scenarios(id),
                    context_metadata JSONB DEFAULT '{}',
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_conversations_company ON conversations(company_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_conversations_active ON conversations(is_active)"))
            
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS conversation_messages (
                    id SERIAL PRIMARY KEY,
                    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                    role VARCHAR(20) NOT NULL,
                    content TEXT NOT NULL,
                    intent_type VARCHAR(50),
                    scenario_id INTEGER REFERENCES scenarios(id),
                    simulation_id INTEGER,
                    chart_data JSONB,
                    message_metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_conv_messages_conv ON conversation_messages(conversation_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_conv_messages_created ON conversation_messages(created_at)"))
            
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS conversation_recommendations (
                    id SERIAL PRIMARY KEY,
                    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                    message_id INTEGER REFERENCES conversation_messages(id),
                    recommendation_type VARCHAR(50) NOT NULL,
                    recommendation_text TEXT NOT NULL,
                    priority INTEGER DEFAULT 0,
                    context_data JSONB,
                    feedback VARCHAR(20),
                    feedback_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_conv_recs_conv ON conversation_recommendations(conversation_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_conv_recs_type ON conversation_recommendations(recommendation_type)"))
            
            conn.commit()
            logger.info("Conversations tables migration complete")
        except Exception as e:
            logger.debug(f"Conversations tables may already exist: {e}")


def ensure_truth_scan_tables(engine: Engine) -> None:
    """Create Truth Scan validation layer tables."""
    with engine.connect() as conn:
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS truth_scan_uploads (
                    id VARCHAR(36) PRIMARY KEY,
                    company_id INTEGER NOT NULL REFERENCES companies(id),
                    source_kind VARCHAR(20) NOT NULL,
                    import_session_id INTEGER REFERENCES import_sessions(id),
                    dataset_id INTEGER REFERENCES datasets(id),
                    manual_baseline_payload JSONB,
                    file_hash_sha256 VARCHAR(64),
                    status VARCHAR(20) DEFAULT 'received' NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_tsu_company ON truth_scan_uploads(company_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_tsu_import_session ON truth_scan_uploads(import_session_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_tsu_dataset ON truth_scan_uploads(dataset_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_tsu_hash ON truth_scan_uploads(file_hash_sha256)"))
            
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS truth_datasets (
                    id VARCHAR(36) PRIMARY KEY,
                    company_id INTEGER NOT NULL REFERENCES companies(id),
                    source_upload_id VARCHAR(36) NOT NULL REFERENCES truth_scan_uploads(id),
                    version INTEGER NOT NULL,
                    finalized BOOLEAN DEFAULT FALSE,
                    is_latest BOOLEAN DEFAULT FALSE,
                    assumptions JSONB NOT NULL DEFAULT '{}',
                    facts JSONB NOT NULL DEFAULT '{}',
                    derived JSONB NOT NULL DEFAULT '{}',
                    coverage JSONB NOT NULL DEFAULT '{}',
                    confidence_summary JSONB NOT NULL DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_td_company ON truth_datasets(company_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_td_upload ON truth_datasets(source_upload_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_td_version ON truth_datasets(version)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_td_finalized ON truth_datasets(finalized)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_td_latest ON truth_datasets(is_latest)"))
            
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS validation_reports (
                    id VARCHAR(36) PRIMARY KEY,
                    company_id INTEGER NOT NULL REFERENCES companies(id),
                    source_upload_id VARCHAR(36) NOT NULL REFERENCES truth_scan_uploads(id),
                    truth_dataset_id VARCHAR(36) NOT NULL REFERENCES truth_datasets(id),
                    summary JSONB NOT NULL DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_vr_company ON validation_reports(company_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_vr_upload ON validation_reports(source_upload_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_vr_dataset ON validation_reports(truth_dataset_id)"))
            
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS validation_issues (
                    id VARCHAR(36) PRIMARY KEY,
                    report_id VARCHAR(36) NOT NULL REFERENCES validation_reports(id),
                    severity VARCHAR(20) NOT NULL,
                    category VARCHAR(20) NOT NULL,
                    metric_key VARCHAR(50),
                    message VARCHAR(500) NOT NULL,
                    evidence JSONB NOT NULL DEFAULT '{}',
                    suggestion JSONB,
                    can_autofix BOOLEAN DEFAULT FALSE,
                    autofix_patch JSONB,
                    status VARCHAR(20) DEFAULT 'open' NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW(),
                    resolved_at TIMESTAMP
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_vi_report ON validation_issues(report_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_vi_metric ON validation_issues(metric_key)"))
            
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS truth_decision_logs (
                    id VARCHAR(36) PRIMARY KEY,
                    source_upload_id VARCHAR(36) NOT NULL REFERENCES truth_scan_uploads(id),
                    issue_id VARCHAR(36) REFERENCES validation_issues(id),
                    action VARCHAR(30) NOT NULL,
                    patch JSONB NOT NULL DEFAULT '{}',
                    rationale TEXT,
                    actor VARCHAR(10) DEFAULT 'system',
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_tdl_upload ON truth_decision_logs(source_upload_id)"))
            
            conn.commit()
            logger.info("Truth Scan tables migration complete")
        except Exception as e:
            logger.debug(f"Truth Scan tables may already exist: {e}")


def ensure_truth_scan_columns(engine: Engine) -> None:
    """Add Truth Scan related columns to existing tables."""
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE import_sessions ADD COLUMN IF NOT EXISTS truth_scan_upload_id VARCHAR(36)"))
            conn.execute(text("ALTER TABLE import_sessions ADD COLUMN IF NOT EXISTS truth_dataset_id VARCHAR(36)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_is_truth_upload ON import_sessions(truth_scan_upload_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_is_truth_dataset ON import_sessions(truth_dataset_id)"))
            
            conn.execute(text("ALTER TABLE companies ADD COLUMN IF NOT EXISTS latest_truth_dataset_id VARCHAR(36)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_comp_truth ON companies(latest_truth_dataset_id)"))
            
            conn.commit()
            logger.info("Truth Scan columns migration complete")
        except Exception as e:
            logger.debug(f"Truth Scan columns may already exist: {e}")


def ensure_company_states_table(engine: Engine) -> None:
    """Ensure the company_states table exists for canonical state tracking."""
    with engine.connect() as conn:
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS company_states (
                    id SERIAL PRIMARY KEY,
                    company_id INTEGER NOT NULL UNIQUE REFERENCES companies(id),
                    environment VARCHAR(20) NOT NULL DEFAULT 'user',
                    state_json TEXT NOT NULL,
                    snapshot_id VARCHAR(64) NOT NULL,
                    fundraising_rounds_json TEXT DEFAULT '[]',
                    cash_balance INTEGER,
                    monthly_burn INTEGER,
                    revenue_monthly INTEGER,
                    revenue_growth_rate VARCHAR(20),
                    expenses_monthly INTEGER,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_company_states_company ON company_states(company_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_company_states_snapshot ON company_states(snapshot_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_company_states_updated ON company_states(updated_at)"))
            conn.execute(text("ALTER TABLE company_states ADD COLUMN IF NOT EXISTS fundraising_rounds_json TEXT DEFAULT '[]'"))
            conn.commit()
            logger.info("Company states table migration complete")
        except Exception as e:
            logger.debug(f"Company states table may already exist: {e}")


def ensure_simulation_runs_provenance(engine: Engine) -> None:
    """Add provenance columns to simulation_runs table for deterministic snapshotting."""
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE simulation_runs ADD COLUMN IF NOT EXISTS data_snapshot_id VARCHAR(64)"))
            conn.execute(text("ALTER TABLE simulation_runs ADD COLUMN IF NOT EXISTS inputs_json JSONB"))
            conn.execute(text("ALTER TABLE simulation_runs ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'completed'"))
            conn.execute(text("ALTER TABLE simulation_runs ADD COLUMN IF NOT EXISTS error_message TEXT"))
            conn.execute(text("ALTER TABLE simulation_runs ADD COLUMN IF NOT EXISTS completed_at TIMESTAMP"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_simruns_snapshot ON simulation_runs(data_snapshot_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_simruns_status ON simulation_runs(status)"))
            conn.commit()
            logger.info("Simulation runs provenance columns migration complete")
        except Exception as e:
            logger.debug(f"Simulation runs provenance columns may already exist: {e}")


def ensure_scenarios_overrides(engine: Engine) -> None:
    """Add overrides_json column to scenarios table for deterministic scenario inputs."""
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE scenarios ADD COLUMN IF NOT EXISTS overrides_json JSONB DEFAULT '{}'"))
            conn.execute(text("ALTER TABLE scenarios ADD COLUMN IF NOT EXISTS outputs_json JSONB"))
            conn.commit()
            logger.info("Scenarios overrides columns migration complete")
        except Exception as e:
            logger.debug(f"Scenarios overrides columns may already exist: {e}")


def ensure_email_events_table(engine: Engine) -> None:
    """Create email_events table for tracking Resend webhook events."""
    with engine.connect() as conn:
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS email_events (
                    id SERIAL PRIMARY KEY,
                    email_id VARCHAR(255) UNIQUE NOT NULL,
                    to_email VARCHAR(255),
                    subject TEXT,
                    delivered_at TIMESTAMP,
                    opened_at TIMESTAMP,
                    clicked_at TIMESTAMP,
                    classification VARCHAR(50),
                    events_json JSONB DEFAULT '[]',
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_email_events_email_id ON email_events(email_id)"))
            conn.commit()
            logger.info("Email events table migration complete")
        except Exception as e:
            logger.debug(f"Email events table may already exist: {e}")

    with engine.connect() as conn:
        new_cols = [
            ('from_email', 'VARCHAR(255)'),
            ('recipient_id', 'VARCHAR(255)'),
            ('campaign', 'VARCHAR(255)'),
            ('sent_at', 'TIMESTAMP'),
            ('bounced_at', 'TIMESTAMP'),
            ('complained_at', 'TIMESTAMP'),
            ('open_count', 'INTEGER DEFAULT 0'),
            ('click_count', 'INTEGER DEFAULT 0'),
            ('clicked_urls', 'JSONB DEFAULT \'[]\''),
            ('is_bot_open', 'BOOLEAN DEFAULT FALSE'),
            ('utm_source', 'VARCHAR(255)'),
            ('utm_medium', 'VARCHAR(255)'),
            ('utm_campaign', 'VARCHAR(255)'),
            ('utm_content', 'VARCHAR(255)'),
            ('utm_term', 'VARCHAR(255)'),
        ]
        for col_name, col_type in new_cols:
            try:
                conn.execute(text(f"ALTER TABLE email_events ADD COLUMN IF NOT EXISTS {col_name} {col_type}"))
            except Exception:
                pass
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_email_events_to_email ON email_events(to_email)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_email_events_campaign ON email_events(campaign)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_email_events_recipient_id ON email_events(recipient_id)"))
        except Exception:
            pass
        conn.commit()
        logger.info("Email events columns migration complete")

    with engine.connect() as conn:
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS email_link_clicks (
                    id SERIAL PRIMARY KEY,
                    email_id VARCHAR(255),
                    tracking_id VARCHAR(255) UNIQUE NOT NULL,
                    recipient_email VARCHAR(255),
                    recipient_id VARCHAR(255),
                    destination_url TEXT NOT NULL,
                    link_label VARCHAR(255),
                    clicked BOOLEAN DEFAULT FALSE,
                    click_count INTEGER DEFAULT 0,
                    first_clicked_at TIMESTAMP,
                    last_clicked_at TIMESTAMP,
                    user_agent TEXT,
                    ip_address VARCHAR(100),
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_link_clicks_tracking_id ON email_link_clicks(tracking_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_link_clicks_email_id ON email_link_clicks(email_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_link_clicks_recipient ON email_link_clicks(recipient_email)"))
            conn.commit()
            logger.info("Email link clicks table migration complete")
        except Exception as e:
            logger.debug(f"Email link clicks table may already exist: {e}")

    with engine.connect() as conn:
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS email_feedback (
                    id SERIAL PRIMARY KEY,
                    email_id VARCHAR(255),
                    recipient_email VARCHAR(255),
                    rating VARCHAR(50),
                    comment TEXT,
                    campaign VARCHAR(255),
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_email_feedback_email_id ON email_feedback(email_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_email_feedback_recipient ON email_feedback(recipient_email)"))
            conn.commit()
            logger.info("Email feedback table migration complete")
        except Exception as e:
            logger.debug(f"Email feedback table may already exist: {e}")


def ensure_metric_suggestions_tables(engine: Engine) -> None:
    """Create metric suggestions and related tables."""
    with engine.connect() as conn:
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS connector_capabilities (
                    id SERIAL PRIMARY KEY,
                    company_id INTEGER NOT NULL REFERENCES companies(id),
                    data_source_id INTEGER,
                    adapter_key VARCHAR(100) NOT NULL,
                    discovered_at TIMESTAMP DEFAULT NOW(),
                    capabilities JSONB DEFAULT '{}'
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_capability_company_adapter ON connector_capabilities(company_id, adapter_key)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_capability_data_source ON connector_capabilities(data_source_id)"))
            
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS metric_suggestions (
                    id SERIAL PRIMARY KEY,
                    company_id INTEGER NOT NULL REFERENCES companies(id),
                    data_source_id INTEGER,
                    suggestion_key VARCHAR(100) NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    description TEXT,
                    category VARCHAR(50) DEFAULT 'Finance',
                    metric_dsl_yaml TEXT NOT NULL,
                    dependencies JSONB,
                    confidence_score INTEGER DEFAULT 80,
                    reason JSONB,
                    status VARCHAR(50) DEFAULT 'new',
                    accepted_metric_id INTEGER REFERENCES metric_definitions(id),
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """))
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_suggestion_company_key ON metric_suggestions(company_id, suggestion_key)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_suggestion_status ON metric_suggestions(status)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_suggestion_category ON metric_suggestions(category)"))
            
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS suggestion_events (
                    id SERIAL PRIMARY KEY,
                    company_id INTEGER NOT NULL REFERENCES companies(id),
                    suggestion_id INTEGER NOT NULL REFERENCES metric_suggestions(id),
                    actor_id INTEGER REFERENCES users(id),
                    action VARCHAR(50) NOT NULL,
                    meta JSONB,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_sugg_event_suggestion ON suggestion_events(suggestion_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_sugg_event_action ON suggestion_events(action)"))
            
            conn.commit()
            logger.info("Metric suggestions tables migration complete")
        except Exception as e:
            logger.debug(f"Metric suggestions tables may already exist: {e}")


def ensure_metric_definitions_columns(engine: Engine) -> None:
    """Add missing columns to metric_definitions table and fix constraints."""
    with engine.connect() as conn:
        try:
            conn.execute(text("""
                ALTER TABLE metric_definitions
                    ADD COLUMN IF NOT EXISTS definition TEXT,
                    ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1,
                    ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'draft',
                    ADD COLUMN IF NOT EXISTS dependencies JSON,
                    ADD COLUMN IF NOT EXISTS tags JSON,
                    ADD COLUMN IF NOT EXISTS owners JSON,
                    ADD COLUMN IF NOT EXISTS published_at TIMESTAMP
            """))
            conn.execute(text("ALTER TABLE metric_definitions ALTER COLUMN formula DROP NOT NULL"))
            conn.execute(text("ALTER TABLE metric_definitions ALTER COLUMN source_connector DROP NOT NULL"))
            conn.commit()
            logger.info("Metric definitions columns migration complete")
        except Exception as e:
            logger.debug(f"Metric definitions columns may already exist: {e}")


def ensure_metric_values_columns(engine: Engine) -> None:
    """Add missing columns to metric_values table."""
    with engine.connect() as conn:
        try:
            conn.execute(text("""
                ALTER TABLE metric_values
                    ADD COLUMN IF NOT EXISTS metric_version INTEGER DEFAULT 1,
                    ADD COLUMN IF NOT EXISTS source_versions JSON,
                    ADD COLUMN IF NOT EXISTS compiled_sql VARCHAR(2000)
            """))
            conn.commit()
            logger.info("Metric values columns migration complete")
        except Exception as e:
            logger.debug(f"Metric values columns may already exist: {e}")


def ensure_team_members_table(engine: Engine) -> None:
    """Create team_members table if it doesn't exist."""
    with engine.connect() as conn:
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS team_members (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    email VARCHAR(255) NOT NULL,
                    role VARCHAR(255) NOT NULL,
                    type VARCHAR(50) NOT NULL DEFAULT 'full_time',
                    department VARCHAR(100) NOT NULL DEFAULT 'Engineering',
                    status VARCHAR(50) NOT NULL DEFAULT 'active',
                    start_date VARCHAR(50),
                    end_date VARCHAR(50),
                    salary_range TEXT,
                    skills JSON,
                    github_url VARCHAR(500),
                    linkedin_url VARCHAR(500),
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """))
            conn.commit()
            logger.info("Team members table migration complete")
        except Exception as e:
            logger.debug(f"Team members table may already exist: {e}")


def run_migrations(engine: Engine) -> None:
    """Run all pending migrations."""
    logger.info("Running database migrations...")
    ensure_financial_record_columns(engine)
    ensure_invites_table(engine)
    ensure_company_metadata_column(engine)
    ensure_company_description_column(engine)
    ensure_company_decisions_table(engine)
    ensure_company_scenarios_table(engine)
    ensure_company_sources_table(engine)
    ensure_company_workstreams_table(engine)
    ensure_company_alerts_table(engine)
    ensure_company_driver_models_table(engine)
    ensure_llm_audit_logs_table(engine)
    ensure_eval_runs_table(engine)
    ensure_fundraising_tables(engine)
    ensure_conversations_tables(engine)
    ensure_truth_scan_tables(engine)
    ensure_truth_scan_columns(engine)
    ensure_company_states_table(engine)
    ensure_simulation_runs_provenance(engine)
    ensure_scenarios_overrides(engine)
    ensure_email_events_table(engine)
    ensure_metric_suggestions_tables(engine)
    ensure_metric_definitions_columns(engine)
    ensure_metric_values_columns(engine)
    ensure_team_members_table(engine)
    logger.info("Database migrations completed successfully")
