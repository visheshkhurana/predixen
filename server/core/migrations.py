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


def ensure_company_amount_scale(engine: Engine) -> None:
    """Ensure the amount_scale column exists in companies table for denomination scaling."""
    with engine.connect() as conn:
        try:
            conn.execute(text(
                "ALTER TABLE companies ADD COLUMN IF NOT EXISTS amount_scale VARCHAR DEFAULT 'UNITS'"
            ))
            conn.commit()
            logger.info("Companies amount_scale column migration complete")
        except Exception as e:
            logger.debug(f"amount_scale column may already exist: {e}")


def ensure_cap_table_enhancements(engine: Engine) -> None:
    """Add new cap table columns and tables for the Carta-like redesign."""
    for col_name, col_type in [
        ("tax_id", "VARCHAR(100)"),
        ("address", "TEXT"),
    ]:
        try:
            with engine.connect() as conn:
                conn.execute(text(f"ALTER TABLE shareholders ADD COLUMN {col_name} {col_type}"))
                conn.commit()
        except Exception:
            pass

    for col_name, col_type in [
        ("liquidation_preference_multiple", "FLOAT DEFAULT 1.0"),
        ("participation_cap", "FLOAT"),
        ("is_participating", "BOOLEAN DEFAULT FALSE"),
        ("seniority", "INTEGER DEFAULT 1"),
    ]:
        try:
            with engine.connect() as conn:
                conn.execute(text(f"ALTER TABLE equity_holdings ADD COLUMN {col_name} {col_type}"))
                conn.commit()
        except Exception:
            pass

    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS convertible_securities (
                id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
                company_id INTEGER NOT NULL REFERENCES companies(id),
                shareholder_id VARCHAR(36) REFERENCES shareholders(id),
                type VARCHAR(30) NOT NULL,
                holder VARCHAR(255) NOT NULL,
                principal FLOAT NOT NULL,
                valuation_cap FLOAT,
                discount_rate FLOAT DEFAULT 0,
                interest_rate FLOAT DEFAULT 0,
                maturity_date DATE,
                issue_date DATE DEFAULT CURRENT_DATE,
                conversion_status VARCHAR(20) DEFAULT 'outstanding',
                converted_to_holding_id VARCHAR(36),
                terms_json JSONB DEFAULT '{}'::jsonb,
                notes TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS cap_table_scenarios (
                id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
                company_id INTEGER NOT NULL REFERENCES companies(id),
                name VARCHAR(255) NOT NULL,
                description TEXT,
                scenario_type VARCHAR(30) NOT NULL,
                inputs_json JSONB DEFAULT '{}'::jsonb,
                results_json JSONB,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS cap_table_audit_log (
                id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
                company_id INTEGER NOT NULL REFERENCES companies(id),
                entity_type VARCHAR(50) NOT NULL,
                entity_id VARCHAR(100) NOT NULL,
                action VARCHAR(30) NOT NULL,
                user_id VARCHAR(100),
                changes_json JSONB,
                timestamp TIMESTAMP DEFAULT NOW()
            )
        """))

        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_convertible_securities_company ON convertible_securities(company_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_cap_table_scenarios_company ON cap_table_scenarios(company_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_cap_table_audit_log_company ON cap_table_audit_log(company_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_cap_table_audit_log_entity ON cap_table_audit_log(entity_type, entity_id)"))
        except Exception:
            pass

        conn.commit()
    logger.info("Cap table enhancements migration complete")


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
    ensure_currency_tables(engine)
    ensure_company_amount_scale(engine)
    ensure_user_oauth_columns(engine)
    ensure_auth_tokens_tables(engine)
    ensure_beta_feedback_table(engine)
    ensure_rate_limits_table(engine)
    ensure_cap_table_enhancements(engine)
    ensure_twin_events_table(engine)
    ensure_simulation_outputs_table(engine)
    ensure_scenario_inputs_table(engine)
    ensure_scenario_events_table(engine)
    ensure_decision_options_table(engine)
    ensure_event_ledger_tables(engine)
    ensure_feature_flags_tables(engine)
    ensure_ai_governance_tables(engine)
    ensure_data_confidence_table(engine)
    ensure_graph_adjacency_tables(engine)
    ensure_autopilot_tables(engine)
    ensure_survival_simulations_table(engine)
    ensure_decision_outcome_columns(engine)
    ensure_company_data_sharing_column(engine)
    ensure_cross_company_patterns_table(engine)
    ensure_simulation_accuracy_tables(engine)
    ensure_copilot_feedback_table(engine)
    ensure_agent_simulation_runs_table(engine)
    ensure_subscription_trial_columns(engine)
    logger.info("Database migrations completed successfully")


def ensure_currency_tables(engine: Engine) -> None:
    """Create exchange_rates table and add currency columns to financial_records."""
    is_sqlite = engine.dialect.name == "sqlite"
    create_exchange_rates_sql = """
            CREATE TABLE IF NOT EXISTS exchange_rates (
                id SERIAL PRIMARY KEY,
                base_currency VARCHAR(3) NOT NULL,
                quote_currency VARCHAR(3) NOT NULL,
                rate FLOAT NOT NULL,
                rate_date DATE NOT NULL,
                source VARCHAR(50) DEFAULT 'ecb',
                fetched_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(base_currency, quote_currency, rate_date)
            )
        """
    if is_sqlite:
        create_exchange_rates_sql = """
            CREATE TABLE IF NOT EXISTS exchange_rates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                base_currency VARCHAR(3) NOT NULL,
                quote_currency VARCHAR(3) NOT NULL,
                rate FLOAT NOT NULL,
                rate_date DATE NOT NULL,
                source VARCHAR(50) DEFAULT 'ecb',
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(base_currency, quote_currency, rate_date)
            )
        """

    with engine.connect() as conn:
        try:
            conn.execute(text(create_exchange_rates_sql))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_exchange_rates_base ON exchange_rates(base_currency)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_exchange_rates_date ON exchange_rates(rate_date)
            """))
            for col_name, col_type, default in [
                ('original_currency', "VARCHAR(3)", "'USD'"),
                ('fx_rate_to_base', 'FLOAT', '1.0'),
                ('base_currency', "VARCHAR(3)", "'USD'"),
            ]:
                try:
                    conn.execute(text(
                        f"ALTER TABLE financial_records ADD COLUMN IF NOT EXISTS {col_name} {col_type} DEFAULT {default}"
                    ))
                except Exception as e:
                    logger.debug(f"Column {col_name} may already exist: {e}")
            conn.commit()
        except Exception as e:
            logger.debug(f"Currency tables migration may already exist: {e}")
    logger.info("Currency tables migration complete")


def ensure_user_oauth_columns(engine: Engine) -> None:
    """Add OAuth columns to users table for social login support."""
    columns = [
        ('oauth_provider', 'VARCHAR(20)'),
        ('oauth_id', 'VARCHAR(255)'),
        ('avatar_url', 'VARCHAR(500)'),
        ('display_name', 'VARCHAR(255)'),
    ]
    with engine.connect() as conn:
        for col_name, col_type in columns:
            try:
                conn.execute(text(
                    f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col_name} {col_type}"
                ))
            except Exception as e:
                logger.debug(f"Column users.{col_name} may already exist: {e}")
        try:
            conn.execute(text(
                "ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL"
            ))
        except Exception as e:
            logger.debug(f"password_hash nullable change may already be applied: {e}")
        try:
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_users_oauth_id ON users(oauth_id)"
            ))
        except Exception as e:
            logger.debug(f"OAuth index may already exist: {e}")
        conn.commit()
    logger.info("User OAuth columns migration complete")


def ensure_auth_tokens_tables(engine: Engine) -> None:
    with engine.connect() as conn:
        try:
            conn.execute(text(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_email_verified BOOLEAN DEFAULT FALSE"
            ))
        except Exception as e:
            logger.debug(f"is_email_verified column may already exist: {e}")

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                token VARCHAR NOT NULL UNIQUE,
                expires_at TIMESTAMP NOT NULL,
                used BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS email_verification_tokens (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                token VARCHAR NOT NULL UNIQUE,
                expires_at TIMESTAMP NOT NULL,
                used BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS refresh_tokens (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                token VARCHAR NOT NULL UNIQUE,
                expires_at TIMESTAMP NOT NULL,
                revoked BOOLEAN DEFAULT FALSE,
                replaced_by VARCHAR,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))

        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_password_reset_token ON password_reset_tokens(token)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_email_verification_token ON email_verification_tokens(token)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_refresh_token ON refresh_tokens(token)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_refresh_token_user ON refresh_tokens(user_id)"))
        except Exception as e:
            logger.debug(f"Token indexes may already exist: {e}")

        conn.commit()
    logger.info("Auth tokens tables migration complete")


def ensure_rate_limits_table(engine: Engine) -> None:
    """Create rate_limits table for database-backed rate limiting."""
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS rate_limits (
                id SERIAL PRIMARY KEY,
                key VARCHAR(255) NOT NULL,
                endpoint VARCHAR(100) NOT NULL,
                request_count INTEGER NOT NULL DEFAULT 0,
                window_start TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                UNIQUE(key, endpoint)
            )
        """))
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_rate_limits_key_endpoint ON rate_limits(key, endpoint)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_rate_limits_window_start ON rate_limits(window_start)"))
        except Exception as e:
            logger.debug(f"Rate limits indexes may already exist: {e}")
        conn.commit()
    logger.info("Rate limits table migration complete")


def ensure_beta_feedback_table(engine: Engine) -> None:
    """Create beta_feedback table for in-app feedback collection."""
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS beta_feedback (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                email VARCHAR(255),
                type VARCHAR(20) NOT NULL DEFAULT 'general',
                message TEXT NOT NULL,
                page VARCHAR(500) DEFAULT '',
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))
        conn.commit()
    logger.info("Beta feedback table migration complete")


def ensure_twin_events_table(engine: Engine) -> None:
    """Create twin_events table for Digital Twin event tracking."""
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS twin_events (
                id SERIAL PRIMARY KEY,
                company_id INTEGER NOT NULL REFERENCES companies(id),
                event_type VARCHAR(100) NOT NULL,
                source VARCHAR(100) NOT NULL,
                payload JSON,
                created_at TIMESTAMP DEFAULT NOW() NOT NULL
            )
        """))
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_twin_events_company_id ON twin_events(company_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_twin_events_event_type ON twin_events(event_type)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_twin_events_company_type ON twin_events(company_id, event_type)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_twin_events_created ON twin_events(created_at)"))
        except Exception:
            pass
        conn.commit()
    logger.info("Twin events table migration complete")


def ensure_simulation_outputs_table(engine: Engine) -> None:
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS simulation_outputs (
                id SERIAL PRIMARY KEY,
                run_id INTEGER NOT NULL,
                metric VARCHAR(100) NOT NULL,
                month INTEGER NOT NULL,
                p10 FLOAT,
                p50 FLOAT,
                p90 FLOAT,
                mean FLOAT,
                std_dev FLOAT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_sim_outputs_run_id ON simulation_outputs(run_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_sim_outputs_metric ON simulation_outputs(run_id, metric)"))
        except Exception:
            pass
        conn.commit()
    logger.info("Simulation outputs table migration complete")


def ensure_scenario_inputs_table(engine: Engine) -> None:
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS scenario_inputs (
                id SERIAL PRIMARY KEY,
                scenario_id INTEGER NOT NULL,
                input_type VARCHAR(100) NOT NULL,
                parameter_name VARCHAR(200) NOT NULL,
                parameter_value FLOAT,
                parameter_text VARCHAR(500),
                start_month INTEGER,
                end_month INTEGER,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_scenario_inputs_scenario ON scenario_inputs(scenario_id)"))
        except Exception:
            pass
        conn.commit()
    logger.info("Scenario inputs table migration complete")


def ensure_scenario_events_table(engine: Engine) -> None:
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS scenario_events (
                id SERIAL PRIMARY KEY,
                scenario_id INTEGER NOT NULL,
                event_type VARCHAR(100) NOT NULL,
                event_month INTEGER NOT NULL,
                description VARCHAR(500),
                impact_metric VARCHAR(100),
                impact_value FLOAT,
                probability FLOAT DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_scenario_events_scenario ON scenario_events(scenario_id)"))
        except Exception:
            pass
        conn.commit()
    logger.info("Scenario events table migration complete")


def ensure_decision_options_table(engine: Engine) -> None:
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS decision_options (
                id SERIAL PRIMARY KEY,
                decision_id INTEGER NOT NULL,
                option_label VARCHAR(300) NOT NULL,
                description TEXT,
                estimated_impact FLOAT,
                risk_level VARCHAR(50),
                recommended BOOLEAN DEFAULT FALSE,
                chosen BOOLEAN DEFAULT FALSE,
                simulation_run_id INTEGER,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_decision_options_decision ON decision_options(decision_id)"))
        except Exception:
            pass
        conn.commit()
    logger.info("Decision options table migration complete")


def ensure_event_ledger_tables(engine: Engine) -> None:
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS events (
                id SERIAL PRIMARY KEY,
                company_id INTEGER NOT NULL,
                user_id INTEGER,
                event_type VARCHAR(100) NOT NULL,
                aggregate_type VARCHAR(100) NOT NULL,
                aggregate_id INTEGER,
                timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                version INTEGER DEFAULT 1
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS event_payloads (
                id SERIAL PRIMARY KEY,
                event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
                payload_json TEXT NOT NULL
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS event_consumers (
                consumer_name VARCHAR(255) PRIMARY KEY,
                last_event_id INTEGER DEFAULT 0
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS event_projections (
                projection_name VARCHAR(255) PRIMARY KEY,
                state_json TEXT NOT NULL
            )
        """))
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_events_company ON events(company_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_events_type ON events(event_type)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_events_aggregate ON events(aggregate_type, aggregate_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_events_timestamp ON events(timestamp)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_event_payloads_event ON event_payloads(event_id)"))
        except Exception:
            pass
        conn.commit()
    logger.info("Event ledger tables migration complete")


def ensure_feature_flags_tables(engine: Engine) -> None:
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS feature_flags (
                key VARCHAR(255) PRIMARY KEY,
                description TEXT,
                enabled BOOLEAN DEFAULT FALSE
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS company_flags (
                id SERIAL PRIMARY KEY,
                company_id INTEGER NOT NULL,
                flag_key VARCHAR(255) NOT NULL REFERENCES feature_flags(key),
                enabled BOOLEAN DEFAULT FALSE,
                UNIQUE(company_id, flag_key)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS user_flags (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                flag_key VARCHAR(255) NOT NULL REFERENCES feature_flags(key),
                enabled BOOLEAN DEFAULT FALSE,
                UNIQUE(user_id, flag_key)
            )
        """))
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_company_flags_company ON company_flags(company_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_user_flags_user ON user_flags(user_id)"))
        except Exception:
            pass
        conn.commit()
    logger.info("Feature flags tables migration complete")


def ensure_ai_governance_tables(engine: Engine) -> None:
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS ai_agent_permissions (
                agent_name VARCHAR(255) PRIMARY KEY,
                allowed_actions TEXT,
                max_daily_requests INTEGER DEFAULT 1000,
                requires_human_approval BOOLEAN DEFAULT FALSE
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS ai_agent_logs (
                id SERIAL PRIMARY KEY,
                agent_name VARCHAR(255) NOT NULL,
                task VARCHAR(500),
                input_json TEXT,
                output_json TEXT,
                cost FLOAT DEFAULT 0,
                timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                company_id INTEGER
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS ai_agent_budgets (
                id SERIAL PRIMARY KEY,
                company_id INTEGER NOT NULL,
                agent_name VARCHAR(255) NOT NULL,
                monthly_budget FLOAT DEFAULT 100.0,
                usage FLOAT DEFAULT 0,
                UNIQUE(company_id, agent_name)
            )
        """))
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_ai_logs_agent ON ai_agent_logs(agent_name)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_ai_logs_timestamp ON ai_agent_logs(timestamp)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_ai_logs_company ON ai_agent_logs(company_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_ai_budgets_company ON ai_agent_budgets(company_id)"))
        except Exception:
            pass
        conn.commit()
    logger.info("AI governance tables migration complete")


def ensure_data_confidence_table(engine: Engine) -> None:
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS data_confidence_scores (
                id SERIAL PRIMARY KEY,
                company_id INTEGER NOT NULL,
                metric_name VARCHAR(100) NOT NULL,
                freshness_score FLOAT DEFAULT 0,
                coverage_score FLOAT DEFAULT 0,
                accuracy_score FLOAT DEFAULT 0,
                confidence_score FLOAT DEFAULT 0,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                UNIQUE(company_id, metric_name)
            )
        """))
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_confidence_company ON data_confidence_scores(company_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_confidence_metric ON data_confidence_scores(metric_name)"))
        except Exception:
            pass
        conn.commit()
    logger.info("Data confidence scores table migration complete")


def ensure_graph_adjacency_tables(engine: Engine) -> None:
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS graph_nodes (
                id SERIAL PRIMARY KEY,
                company_id INTEGER NOT NULL,
                node_type VARCHAR(100) NOT NULL,
                entity_id INTEGER,
                label VARCHAR(500),
                properties_json TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS graph_edges (
                id SERIAL PRIMARY KEY,
                company_id INTEGER NOT NULL,
                source_node_id INTEGER NOT NULL REFERENCES graph_nodes(id),
                target_node_id INTEGER NOT NULL REFERENCES graph_nodes(id),
                relationship VARCHAR(100) NOT NULL,
                weight FLOAT DEFAULT 1.0,
                properties_json TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_graph_nodes_company ON graph_nodes(company_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_graph_nodes_type ON graph_nodes(node_type)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_graph_nodes_entity ON graph_nodes(company_id, node_type, entity_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_graph_edges_source ON graph_edges(source_node_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_graph_edges_target ON graph_edges(target_node_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_graph_edges_company ON graph_edges(company_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_graph_edges_rel ON graph_edges(relationship)"))
        except Exception:
            pass
        conn.commit()
    logger.info("Graph adjacency tables migration complete")


def ensure_autopilot_tables(engine: Engine) -> None:
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS autopilot_runs (
                id SERIAL PRIMARY KEY,
                company_id INTEGER NOT NULL,
                briefing_json TEXT,
                risk_count INTEGER DEFAULT 0,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """))
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_autopilot_company ON autopilot_runs(company_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_autopilot_created ON autopilot_runs(created_at)"))
        except Exception:
            pass
        conn.commit()
    logger.info("Autopilot tables migration complete")


def ensure_decision_outcome_columns(engine: Engine) -> None:
    """Add outcome tracking columns to company_decisions table."""
    outcome_columns = [
        ('metrics_snapshot_at_decision', 'JSONB'),
        ('metrics_snapshot_at_followup', 'JSONB'),
        ('outcome_recorded_at', 'TIMESTAMP'),
        ('outcome_delta_json', 'JSONB'),
        ('outcome_rating', 'VARCHAR(20)'),
        ('followup_days', 'INTEGER DEFAULT 60'),
        ('implemented_at', 'TIMESTAMP'),
    ]
    with engine.connect() as conn:
        for col_name, col_type in outcome_columns:
            try:
                conn.execute(text(
                    f'ALTER TABLE company_decisions ADD COLUMN IF NOT EXISTS {col_name} {col_type}'
                ))
            except Exception as e:
                logger.debug(f"Column {col_name} may already exist or error: {e}")
        try:
            conn.execute(text("""
                DO $$ BEGIN
                    ALTER TABLE company_decisions
                        ADD CONSTRAINT ck_outcome_rating_values
                        CHECK (outcome_rating IS NULL OR outcome_rating IN ('positive', 'neutral', 'negative'));
                EXCEPTION WHEN duplicate_object THEN NULL;
                END $$;
            """))
        except Exception:
            pass
        try:
            conn.execute(text("""
                DO $$ BEGIN
                    ALTER TABLE company_decisions
                        ADD CONSTRAINT ck_followup_days_range
                        CHECK (followup_days IS NULL OR (followup_days >= 7 AND followup_days <= 365));
                EXCEPTION WHEN duplicate_object THEN NULL;
                END $$;
            """))
        except Exception:
            pass
        conn.commit()
    logger.info("Decision outcome columns migration complete")


def ensure_survival_simulations_table(engine: Engine) -> None:
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS survival_simulations (
                id SERIAL PRIMARY KEY,
                sim_id VARCHAR(20) UNIQUE NOT NULL,
                inputs_json TEXT,
                results_json TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """))
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_survival_sim_id ON survival_simulations(sim_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_survival_created ON survival_simulations(created_at)"))
        except Exception:
            pass
        conn.commit()
    logger.info("Survival simulations table migration complete")


def ensure_company_data_sharing_column(engine: Engine) -> None:
    with engine.connect() as conn:
        try:
            conn.execute(text(
                "ALTER TABLE companies ADD COLUMN IF NOT EXISTS data_sharing_enabled BOOLEAN DEFAULT FALSE"
            ))
            conn.commit()
            logger.info("Companies data_sharing_enabled column migration complete")
        except Exception as e:
            logger.debug(f"data_sharing_enabled column may already exist: {e}")


def ensure_cross_company_patterns_table(engine: Engine) -> None:
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS cross_company_patterns (
                id SERIAL PRIMARY KEY,
                pattern_type VARCHAR(100) NOT NULL,
                industry VARCHAR(100),
                stage VARCHAR(100),
                decision_type VARCHAR(100),
                sample_size INTEGER DEFAULT 0,
                success_rate FLOAT DEFAULT 0,
                median_impact FLOAT DEFAULT 0,
                p25_impact FLOAT DEFAULT 0,
                p75_impact FLOAT DEFAULT 0,
                metadata_json JSONB DEFAULT '{}'::jsonb,
                contributing_companies INTEGER DEFAULT 0,
                computed_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(pattern_type, industry, stage, decision_type)
            )
        """))
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_ccp_type ON cross_company_patterns(pattern_type)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_ccp_industry ON cross_company_patterns(industry)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_ccp_stage ON cross_company_patterns(stage)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_ccp_decision ON cross_company_patterns(decision_type)"))
        except Exception:
            pass
        conn.commit()
    logger.info("Cross-company patterns table migration complete")


def ensure_simulation_accuracy_tables(engine: Engine) -> None:
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS simulation_accuracy (
                id SERIAL PRIMARY KEY,
                company_id INTEGER NOT NULL,
                simulation_run_id INTEGER,
                scenario_id INTEGER,
                prediction_month INTEGER NOT NULL,
                predicted_revenue FLOAT,
                actual_revenue FLOAT,
                predicted_burn FLOAT,
                actual_burn FLOAT,
                predicted_cash FLOAT,
                actual_cash FLOAT,
                predicted_churn FLOAT,
                actual_churn FLOAT,
                variance_pct_json JSONB,
                accuracy_score FLOAT,
                computed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS calibration_biases (
                id SERIAL PRIMARY KEY,
                company_id INTEGER NOT NULL,
                metric VARCHAR(50) NOT NULL,
                bias_pct FLOAT NOT NULL DEFAULT 0.0,
                sample_count INTEGER DEFAULT 0,
                confidence VARCHAR(20) DEFAULT 'low',
                is_active INTEGER DEFAULT 1,
                applied_at TIMESTAMP WITH TIME ZONE,
                computed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """))
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_sim_accuracy_company ON simulation_accuracy(company_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_sim_accuracy_run ON simulation_accuracy(simulation_run_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_sim_accuracy_computed ON simulation_accuracy(computed_at)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_cal_biases_company ON calibration_biases(company_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_cal_biases_active ON calibration_biases(company_id, is_active)"))
        except Exception:
            pass
        try:
            conn.execute(text("""
                ALTER TABLE simulation_accuracy
                ALTER COLUMN variance_pct_json TYPE JSONB USING variance_pct_json::jsonb
            """))
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE simulation_accuracy ADD COLUMN IF NOT EXISTS predicted_churn FLOAT"))
            conn.execute(text("ALTER TABLE simulation_accuracy ADD COLUMN IF NOT EXISTS actual_churn FLOAT"))
        except Exception:
            pass
        conn.commit()
    logger.info("Simulation accuracy and calibration biases tables migration complete")


def ensure_copilot_feedback_table(engine: Engine) -> None:
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS copilot_feedback (
                id SERIAL PRIMARY KEY,
                company_id INTEGER NOT NULL REFERENCES companies(id),
                user_id INTEGER NOT NULL REFERENCES users(id),
                conversation_id VARCHAR(100),
                message_index INTEGER,
                rating VARCHAR(20) NOT NULL,
                feedback_text TEXT,
                context_snapshot_json JSONB,
                response_type VARCHAR(50),
                tags JSONB DEFAULT '[]'::jsonb,
                message_id VARCHAR(100),
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_cf_company ON copilot_feedback(company_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_cf_user ON copilot_feedback(user_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_cf_rating ON copilot_feedback(rating)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_cf_response_type ON copilot_feedback(response_type)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_cf_message_id ON copilot_feedback(message_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_cf_created ON copilot_feedback(created_at)"))
        except Exception:
            pass
        conn.commit()
    logger.info("Copilot feedback table migration complete")


def ensure_agent_simulation_runs_table(engine: Engine) -> None:
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS agent_simulation_runs (
                id SERIAL PRIMARY KEY,
                company_id INTEGER NOT NULL,
                scenario_json TEXT,
                num_rounds INTEGER DEFAULT 24,
                seed INTEGER,
                survival_probability FLOAT,
                funding_probability FLOAT,
                final_cash FLOAT,
                final_runway FLOAT,
                results_json TEXT NOT NULL,
                events_json TEXT,
                memory_json TEXT,
                status VARCHAR(20) DEFAULT 'completed',
                error_message TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                completed_at TIMESTAMP,
                share_token VARCHAR(64) UNIQUE
            )
        """))
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_asr_company ON agent_simulation_runs(company_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_asr_share ON agent_simulation_runs(share_token)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_asr_created ON agent_simulation_runs(created_at)"))
        except Exception:
            pass
        conn.commit()
    logger.info("Agent simulation runs table migration complete")


def ensure_subscription_trial_columns(engine: Engine) -> None:
    """Add trial_start and trial_end columns to subscriptions table."""
    new_columns = [
        ('trial_start', 'TIMESTAMP'),
        ('trial_end', 'TIMESTAMP'),
    ]
    with engine.connect() as conn:
        for col_name, col_type in new_columns:
            try:
                conn.execute(text(
                    f"ALTER TABLE subscriptions ADD COLUMN {col_name} {col_type}"
                ))
                logger.info(f"Added column {col_name} to subscriptions")
            except Exception:
                pass
        conn.commit()
    logger.info("Subscription trial columns migration complete")
