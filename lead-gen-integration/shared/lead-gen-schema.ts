/**
 * Lead-gen tables — append to shared/schema.ts
 *
 * Imports you need at the top of shared/schema.ts (if not already present):
 *   import { pgTable, text, varchar, integer, boolean, timestamp, jsonb, serial, index, uniqueIndex } from "drizzle-orm/pg-core";
 *   import { relations } from "drizzle-orm";
 *   import { createInsertSchema, createSelectSchema } from "drizzle-zod";
 *   import { z } from "zod";
 *
 * The existing `leads` table is minimal. We extend it below via ALTER
 * in the migration. Add the new columns here first so Drizzle generates
 * the correct migration on `drizzle-kit push`.
 */

// ============================================================
// EXTEND: leads table (new columns)
// ============================================================
// NOTE: merge these into your existing `leads` table definition.
// If your current definition looks like:
//
//   export const leads = pgTable("leads", {
//     id: serial("id").primaryKey(),
//     email: varchar("email", { length: 255 }).notNull().unique(),
//     company: varchar("company", { length: 255 }),
//     plan: varchar("plan", { length: 50 }),
//     createdAt: timestamp("created_at").defaultNow(),
//   });
//
// Replace with the full definition below:

export const leads = pgTable("leads", {
  id: serial("id").primaryKey(),
  email: varchar("email", { length: 255 }).notNull().unique(),

  // Identity
  firstName: varchar("first_name", { length: 120 }),
  lastName: varchar("last_name", { length: 120 }),
  company: varchar("company", { length: 255 }),
  linkedinUrl: text("linkedin_url"),
  website: varchar("website", { length: 255 }),

  // Segmentation
  source: varchar("source", { length: 50 }).notNull().default("manual"),
  // web | scraper | csv | manual | signup | demo_request
  sector: varchar("sector", { length: 80 }),
  stage: varchar("stage", { length: 40 }),
  // pre-seed | seed | series-a | series-b | later | bootstrapped | unknown
  lastFundingEvent: text("last_funding_event"),

  // Lifecycle
  status: varchar("status", { length: 40 }).notNull().default("new"),
  // new | enriching | enriched | queued | contacted | replied | converted | unsubscribed | bounced | do_not_contact
  plan: varchar("plan", { length: 50 }), // existing column — kept for trial tier tracking: free | pro | team

  // Verification (Hunter)
  hunterStatus: varchar("hunter_status", { length: 30 }),
  // valid | accept_all | invalid | disposable | webmail | unknown

  // Enrichment (Perplexity / Apify output)
  summary: text("summary"),
  hook: text("hook"),
  enrichedAt: timestamp("enriched_at"),

  // Campaign tracking
  lastEmailAt: timestamp("last_email_at"),
  replyCategory: varchar("reply_category", { length: 40 }),
  // pricing | question | use_case | onboarding | meeting | misc | noop
  trialSignedUpAt: timestamp("trial_signed_up_at"),
  hasSimulated: boolean("has_simulated").notNull().default(false),
  p50Survival: integer("p50_survival"), // percent, 0-100

  // Tags + notes
  tags: jsonb("tags").$type<string[]>().default([]).notNull(),
  notes: text("notes"),

  createdAt: timestamp("created_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().notNull(),
}, (t) => ({
  statusIdx: index("leads_status_idx").on(t.status),
  sourceIdx: index("leads_source_idx").on(t.source),
  lastEmailIdx: index("leads_last_email_idx").on(t.lastEmailAt),
}));

export const insertLeadSchema = createInsertSchema(leads).omit({
  id: true, createdAt: true, updatedAt: true,
});
export type InsertLead = z.infer<typeof insertLeadSchema>;
export type Lead = typeof leads.$inferSelect;

// ============================================================
// NEW: lead_campaigns — groups of leads running the same drip
// ============================================================
export const leadCampaigns = pgTable("lead_campaigns", {
  id: serial("id").primaryKey(),
  name: varchar("name", { length: 120 }).notNull(),
  description: text("description"),

  // Targeting
  targetSegment: jsonb("target_segment").$type<{
    stages?: string[];
    sectors?: string[];
    sources?: string[];
    tags?: string[];
  }>().default({}).notNull(),

  // n8n linkage
  n8nWorkflowId: varchar("n8n_workflow_id", { length: 80 }),
  n8nWebhookPath: varchar("n8n_webhook_path", { length: 200 }),

  // Cadence
  cadenceDays: jsonb("cadence_days").$type<number[]>().default([0, 2, 5, 9]).notNull(),

  // Goal
  goalMetric: varchar("goal_metric", { length: 40 }).default("trial_signup").notNull(),
  // trial_signup | demo_booked | reply | custom

  status: varchar("status", { length: 20 }).notNull().default("draft"),
  // draft | active | paused | archived

  createdBy: integer("created_by"), // users.id
  createdAt: timestamp("created_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().notNull(),
});

export const insertLeadCampaignSchema = createInsertSchema(leadCampaigns).omit({
  id: true, createdAt: true, updatedAt: true,
});
export type LeadCampaign = typeof leadCampaigns.$inferSelect;
export type InsertLeadCampaign = z.infer<typeof insertLeadCampaignSchema>;

// ============================================================
// NEW: lead_events — every interaction (email sent, opened, replied, ...)
// ============================================================
export const leadEvents = pgTable("lead_events", {
  id: serial("id").primaryKey(),
  leadId: integer("lead_id").notNull().references(() => leads.id, { onDelete: "cascade" }),
  campaignId: integer("campaign_id").references(() => leadCampaigns.id, { onDelete: "set null" }),

  kind: varchar("kind", { length: 40 }).notNull(),
  // email_sent | email_opened | email_clicked | reply_received | reply_classified
  // enrichment_started | enrichment_completed | hunter_verified
  // simulation_completed | trial_upgraded | unsubscribed | manual_note

  // Email-specific
  emailSubject: text("email_subject"),
  emailBodyPreview: text("email_body_preview"), // first 500 chars, for quick scan
  gmailThreadId: varchar("gmail_thread_id", { length: 64 }),
  gmailMessageId: varchar("gmail_message_id", { length: 64 }),

  // Reply-specific
  replyCategory: varchar("reply_category", { length: 40 }),

  // Generic
  metadata: jsonb("metadata").$type<Record<string, any>>().default({}).notNull(),

  // Source of truth for where this came from
  sourceSystem: varchar("source_system", { length: 40 }).notNull().default("n8n"),
  // n8n | predixen | gmail_sync | manual

  createdAt: timestamp("created_at").defaultNow().notNull(),
}, (t) => ({
  leadIdx: index("lead_events_lead_idx").on(t.leadId),
  kindIdx: index("lead_events_kind_idx").on(t.kind),
  createdIdx: index("lead_events_created_idx").on(t.createdAt),
}));

export type LeadEvent = typeof leadEvents.$inferSelect;
export type InsertLeadEvent = typeof leadEvents.$inferInsert;

// ============================================================
// NEW: lead_templates — email templates the AI agent references
// ============================================================
// Distinct from the existing `email_templates` (transactional). These are
// for the outbound drip + inbound auto-reply prompts.
export const leadTemplates = pgTable("lead_templates", {
  id: serial("id").primaryKey(),
  key: varchar("key", { length: 80 }).notNull().unique(),
  // cold_email_1 | follow_up_2 | follow_up_3 | breakup_4 |
  // inbound_pricing | inbound_question | inbound_use_case |
  // inbound_meeting | inbound_onboarding | inbound_misc |
  // activation_welcome | activation_nudge_48h

  label: varchar("label", { length: 120 }).notNull(),
  category: varchar("category", { length: 40 }).notNull(),
  // outbound | inbound | activation

  // The LLM system prompt + a sample subject. The n8n workflow reads these
  // on each send so you can iterate copy without touching n8n.
  systemPrompt: text("system_prompt").notNull(),
  sampleSubject: varchar("sample_subject", { length: 200 }),
  sampleBody: text("sample_body"),

  // Which model to route to (optional override)
  model: varchar("model", { length: 60 }).default("gpt-4o-mini"),

  isActive: boolean("is_active").notNull().default(true),
  updatedBy: integer("updated_by"),
  createdAt: timestamp("created_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().notNull(),
});

export const insertLeadTemplateSchema = createInsertSchema(leadTemplates).omit({
  id: true, createdAt: true, updatedAt: true,
});
export type LeadTemplate = typeof leadTemplates.$inferSelect;
export type InsertLeadTemplate = z.infer<typeof insertLeadTemplateSchema>;

// ============================================================
// NEW: lead_gen_settings — n8n connection + feature flags (singleton row)
// ============================================================
export const leadGenSettings = pgTable("lead_gen_settings", {
  id: serial("id").primaryKey(), // always 1
  n8nBaseUrl: varchar("n8n_base_url", { length: 255 }),
  // e.g. https://vysheshk.app.n8n.cloud
  n8nApiKeyEncrypted: text("n8n_api_key_encrypted"),
  // encrypted via existing CredentialEncryption service

  outboundWebhookUrl: varchar("outbound_webhook_url", { length: 255 }),
  activationWebhookUrl: varchar("activation_webhook_url", { length: 255 }),

  sendingDomain: varchar("sending_domain", { length: 120 }),
  // e.g. mail.founderconsole.ai
  dailySendLimit: integer("daily_send_limit").notNull().default(30),
  isEnabled: boolean("is_enabled").notNull().default(false),

  updatedBy: integer("updated_by"),
  updatedAt: timestamp("updated_at").defaultNow().notNull(),
});

// ============================================================
// RELATIONS
// ============================================================
export const leadsRelations = relations(leads, ({ many }) => ({
  events: many(leadEvents),
}));

export const leadCampaignsRelations = relations(leadCampaigns, ({ many }) => ({
  events: many(leadEvents),
}));

export const leadEventsRelations = relations(leadEvents, ({ one }) => ({
  lead: one(leads, { fields: [leadEvents.leadId], references: [leads.id] }),
  campaign: one(leadCampaigns, { fields: [leadEvents.campaignId], references: [leadCampaigns.id] }),
}));
