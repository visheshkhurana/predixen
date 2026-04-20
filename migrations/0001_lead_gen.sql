-- Lead-gen migration for FounderConsole (predixen)
-- Apply via: psql $DATABASE_URL -f migrations/0001_lead_gen.sql
-- Or let drizzle-kit generate the equivalent from the schema additions.
--
-- Idempotent: uses IF NOT EXISTS / IF NOT EXISTS ... ADD COLUMN.

BEGIN;

-- ============================================================
-- Extend `leads` with the full outreach schema
-- ============================================================
ALTER TABLE leads ADD COLUMN IF NOT EXISTS first_name VARCHAR(120);
ALTER TABLE leads ADD COLUMN IF NOT EXISTS last_name VARCHAR(120);
ALTER TABLE leads ADD COLUMN IF NOT EXISTS linkedin_url TEXT;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS website VARCHAR(255);
ALTER TABLE leads ADD COLUMN IF NOT EXISTS source VARCHAR(50) NOT NULL DEFAULT 'manual';
ALTER TABLE leads ADD COLUMN IF NOT EXISTS sector VARCHAR(80);
ALTER TABLE leads ADD COLUMN IF NOT EXISTS stage VARCHAR(40);
ALTER TABLE leads ADD COLUMN IF NOT EXISTS last_funding_event TEXT;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS status VARCHAR(40) NOT NULL DEFAULT 'new';
ALTER TABLE leads ADD COLUMN IF NOT EXISTS hunter_status VARCHAR(30);
ALTER TABLE leads ADD COLUMN IF NOT EXISTS summary TEXT;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS hook TEXT;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS enriched_at TIMESTAMP;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS last_email_at TIMESTAMP;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS reply_category VARCHAR(40);
ALTER TABLE leads ADD COLUMN IF NOT EXISTS trial_signed_up_at TIMESTAMP;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS has_simulated BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS p50_survival INTEGER;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS tags JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS notes TEXT;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW();

CREATE INDEX IF NOT EXISTS leads_status_idx ON leads (status);
CREATE INDEX IF NOT EXISTS leads_source_idx ON leads (source);
CREATE INDEX IF NOT EXISTS leads_last_email_idx ON leads (last_email_at);

-- ============================================================
-- NEW: lead_campaigns
-- ============================================================
CREATE TABLE IF NOT EXISTS lead_campaigns (
  id SERIAL PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  description TEXT,
  target_segment JSONB NOT NULL DEFAULT '{}'::jsonb,
  n8n_workflow_id VARCHAR(80),
  n8n_webhook_path VARCHAR(200),
  cadence_days JSONB NOT NULL DEFAULT '[0, 2, 5, 9]'::jsonb,
  goal_metric VARCHAR(40) NOT NULL DEFAULT 'trial_signup',
  status VARCHAR(20) NOT NULL DEFAULT 'draft',
  created_by INTEGER,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ============================================================
-- NEW: lead_events (audit of every touchpoint)
-- ============================================================
CREATE TABLE IF NOT EXISTS lead_events (
  id SERIAL PRIMARY KEY,
  lead_id INTEGER NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
  campaign_id INTEGER REFERENCES lead_campaigns(id) ON DELETE SET NULL,
  kind VARCHAR(40) NOT NULL,
  email_subject TEXT,
  email_body_preview TEXT,
  gmail_thread_id VARCHAR(64),
  gmail_message_id VARCHAR(64),
  reply_category VARCHAR(40),
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  source_system VARCHAR(40) NOT NULL DEFAULT 'n8n',
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS lead_events_lead_idx ON lead_events (lead_id);
CREATE INDEX IF NOT EXISTS lead_events_kind_idx ON lead_events (kind);
CREATE INDEX IF NOT EXISTS lead_events_created_idx ON lead_events (created_at);

-- ============================================================
-- NEW: lead_templates
-- ============================================================
CREATE TABLE IF NOT EXISTS lead_templates (
  id SERIAL PRIMARY KEY,
  key VARCHAR(80) NOT NULL UNIQUE,
  label VARCHAR(120) NOT NULL,
  category VARCHAR(40) NOT NULL,
  system_prompt TEXT NOT NULL,
  sample_subject VARCHAR(200),
  sample_body TEXT,
  model VARCHAR(60) DEFAULT 'gpt-4o-mini',
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  updated_by INTEGER,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Seed default templates (idempotent — UPSERT on key)
INSERT INTO lead_templates (key, label, category, system_prompt, sample_subject) VALUES
('cold_email_1', 'Cold email #1', 'outbound',
 'You are Vishesh, founder of FounderConsole. Write email #1 to {{first_name}} at {{company_name}}. Reference {{hook}} in the first line. Under 110 words. CTA: try the free Survival Simulator at founderconsole.ai.',
 '{{company_name}} — survival scenarios?'),
('follow_up_2', 'Follow-up #2', 'outbound',
 'Follow-up 2 days after #1. Share ONE concrete insight: P50 vs P90 gap, post-round dilution preview, or hiring impact. Under 60 words. Reply to thread.',
 'Re: {{company_name}}'),
('follow_up_3', 'Follow-up #3', 'outbound',
 'Follow-up 3 days after #2. Offer a 10-min walkthrough on a similar sample company. Under 55 words. Reply to thread.',
 ''),
('breakup_4', 'Breakup #4', 'outbound',
 'Polite close-out, 4 days after #3. Under 40 words. Must include "I''ll stop writing after this."',
 ''),
('inbound_pricing', 'Inbound — pricing', 'inbound',
 'Reply to a pricing question. Tiers: Free, Pro $29/mo, Team $99/mo. Under 90 words. Sign off as Vishesh.',
 ''),
('inbound_question', 'Inbound — question', 'inbound',
 'Answer a product question using the knowledge-base docs. Under 120 words. CTA: try free at founderconsole.ai.',
 ''),
('inbound_use_case', 'Inbound — use case', 'inbound',
 'Honest fit assessment based on their described situation. Under 130 words. Point to free Survival Simulator as step 1.',
 ''),
('inbound_onboarding', 'Inbound — onboarding help', 'inbound',
 'Existing user stuck. Acknowledge, give a quick fix from KB, offer personal look within 24h if bug. Under 100 words.',
 ''),
('inbound_meeting', 'Inbound — meeting request', 'inbound',
 'Propose 2-3 calendar slots in next 5 biz days. 15 min default. Include booking link fallback. Under 80 words.',
 ''),
('inbound_misc', 'Inbound — misc', 'inbound',
 'Warm reply, address soft objection if present, keep door open. Under 80 words. Light CTA to free tool.',
 ''),
('activation_welcome', 'Activation welcome', 'activation',
 'New signup welcome. Walk through first simulation. 3 common mistakes. CTA: run first sim. Ask for P50.',
 'welcome to FounderConsole — want me to walk you through it?'),
('activation_nudge_48h', 'Activation nudge (48h)', 'activation',
 'Nudge if no sim run after 48h. 3 inputs needed: cash, burn, MRR. 90-second run.',
 'quick nudge on the simulator')
ON CONFLICT (key) DO NOTHING;

-- ============================================================
-- NEW: lead_gen_settings (singleton)
-- ============================================================
CREATE TABLE IF NOT EXISTS lead_gen_settings (
  id SERIAL PRIMARY KEY,
  n8n_base_url VARCHAR(255),
  n8n_api_key_encrypted TEXT,
  outbound_webhook_url VARCHAR(255),
  activation_webhook_url VARCHAR(255),
  sending_domain VARCHAR(120),
  daily_send_limit INTEGER NOT NULL DEFAULT 30,
  is_enabled BOOLEAN NOT NULL DEFAULT FALSE,
  updated_by INTEGER,
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Guarantee singleton row
INSERT INTO lead_gen_settings (id) VALUES (1) ON CONFLICT (id) DO NOTHING;

COMMIT;
