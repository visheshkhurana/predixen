-- AI Governance DB Migration
-- Run this against your PostgreSQL database

CREATE TABLE IF NOT EXISTS ai_requests (
  id SERIAL PRIMARY KEY,
  request_id TEXT NOT NULL UNIQUE,
  company_id TEXT NOT NULL DEFAULT 'predixen',
  initiator TEXT NOT NULL DEFAULT 'founder',
  type TEXT NOT NULL DEFAULT 'decision',
  question TEXT NOT NULL,
  constraints JSONB,
  context_snapshot_id TEXT,
  status TEXT NOT NULL DEFAULT 'pending',
  source TEXT NOT NULL DEFAULT 'founder',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ai_agent_events (
  id SERIAL PRIMARY KEY,
  request_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  agent TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'idle',
  summary TEXT,
  confidence REAL,
  severity TEXT DEFAULT 'normal',
  source TEXT NOT NULL DEFAULT 'agent',
  raw_payload JSONB,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ai_decisions (
  id SERIAL PRIMARY KEY,
  request_id TEXT NOT NULL,
  label TEXT NOT NULL,
  confidence REAL,
  rationale JSONB,
  actions JSONB,
  requires_approval BOOLEAN DEFAULT TRUE,
  agent_positions JSONB,
  status TEXT NOT NULL DEFAULT 'pending',
  source TEXT NOT NULL DEFAULT 'agent',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ai_code_changes (
  id SERIAL PRIMARY KEY,
  request_id TEXT NOT NULL,
  branch TEXT,
  files_changed JSONB,
  tests_passed BOOLEAN,
  risk_level TEXT DEFAULT 'medium',
  summary TEXT,
  status TEXT NOT NULL DEFAULT 'pending',
  source TEXT NOT NULL DEFAULT 'agent',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ai_approvals (
  id SERIAL PRIMARY KEY,
  request_id TEXT NOT NULL,
  decision_id INTEGER,
  approved BOOLEAN NOT NULL,
  approved_by TEXT NOT NULL DEFAULT 'founder',
  reason TEXT,
  source TEXT NOT NULL DEFAULT 'founder',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ai_system_state (
  id SERIAL PRIMARY KEY,
  mode TEXT NOT NULL DEFAULT 'active',
  ai_paused BOOLEAN NOT NULL DEFAULT FALSE,
  code_changes_frozen BOOLEAN NOT NULL DEFAULT FALSE,
  manual_only BOOLEAN NOT NULL DEFAULT FALSE,
  last_changed_by TEXT DEFAULT 'system',
  source TEXT NOT NULL DEFAULT 'system',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Insert default system state
INSERT INTO ai_system_state (mode, ai_paused, code_changes_frozen, manual_only, last_changed_by, source)
SELECT 'active', FALSE, FALSE, FALSE, 'system', 'system'
WHERE NOT EXISTS (SELECT 1 FROM ai_system_state);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_ai_requests_request_id ON ai_requests(request_id);
CREATE INDEX IF NOT EXISTS idx_ai_requests_status ON ai_requests(status);
CREATE INDEX IF NOT EXISTS idx_ai_agent_events_request_id ON ai_agent_events(request_id);
CREATE INDEX IF NOT EXISTS idx_ai_agent_events_agent ON ai_agent_events(agent);
CREATE INDEX IF NOT EXISTS idx_ai_decisions_request_id ON ai_decisions(request_id);
CREATE INDEX IF NOT EXISTS idx_ai_decisions_status ON ai_decisions(status);
CREATE INDEX IF NOT EXISTS idx_ai_code_changes_request_id ON ai_code_changes(request_id);
CREATE INDEX IF NOT EXISTS idx_ai_approvals_request_id ON ai_approvals(request_id);
