import { pgTable, serial, text, timestamp, boolean, real, jsonb, integer } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";
import { sql } from "drizzle-orm";

// AI Requests - tracks all requests from founder to AI boardroom
export const aiRequests = pgTable("ai_requests", {
  id: serial("id").primaryKey(),
  requestId: text("request_id").notNull().unique(),
  companyId: text("company_id").notNull().default("founderconsole"),
  initiator: text("initiator").notNull().default("founder"),
  type: text("type").notNull().default("decision"),
  question: text("question").notNull(),
  constraints: jsonb("constraints"),
  contextSnapshotId: text("context_snapshot_id"),
  status: text("status").notNull().default("pending"),
  source: text("source").notNull().default("founder"),
  createdAt: timestamp("created_at").default(sql`CURRENT_TIMESTAMP`).notNull(),
  updatedAt: timestamp("updated_at").default(sql`CURRENT_TIMESTAMP`).notNull(),
});

// AI Agent Events - tracks individual agent responses/updates
export const aiAgentEvents = pgTable("ai_agent_events", {
  id: serial("id").primaryKey(),
  requestId: text("request_id").notNull(),
  eventType: text("event_type").notNull(),
  agent: text("agent").notNull(),
  status: text("status").notNull().default("idle"),
  summary: text("summary"),
  confidence: real("confidence"),
  severity: text("severity").default("normal"),
  source: text("source").notNull().default("agent"),
  rawPayload: jsonb("raw_payload"),
  createdAt: timestamp("created_at").default(sql`CURRENT_TIMESTAMP`).notNull(),
});

// AI Decisions - tracks boardroom decisions
export const aiDecisions = pgTable("ai_decisions", {
  id: serial("id").primaryKey(),
  requestId: text("request_id").notNull(),
  label: text("label").notNull(),
  confidence: real("confidence"),
  rationale: jsonb("rationale"),
  actions: jsonb("actions"),
  requiresApproval: boolean("requires_approval").default(true),
  agentPositions: jsonb("agent_positions"),
  status: text("status").notNull().default("pending"),
  source: text("source").notNull().default("agent"),
  createdAt: timestamp("created_at").default(sql`CURRENT_TIMESTAMP`).notNull(),
});

// AI Code Changes - tracks AI-proposed code changes
export const aiCodeChanges = pgTable("ai_code_changes", {
  id: serial("id").primaryKey(),
  requestId: text("request_id").notNull(),
  branch: text("branch"),
  filesChanged: jsonb("files_changed"),
  testsPassed: boolean("tests_passed"),
  riskLevel: text("risk_level").default("medium"),
  summary: text("summary"),
  status: text("status").notNull().default("pending"),
  source: text("source").notNull().default("agent"),
  createdAt: timestamp("created_at").default(sql`CURRENT_TIMESTAMP`).notNull(),
});

// AI Approvals - tracks founder approvals/rejections
export const aiApprovals = pgTable("ai_approvals", {
  id: serial("id").primaryKey(),
  requestId: text("request_id").notNull(),
  decisionId: integer("decision_id"),
  approved: boolean("approved").notNull(),
  approvedBy: text("approved_by").notNull().default("founder"),
  reason: text("reason"),
  source: text("source").notNull().default("founder"),
  createdAt: timestamp("created_at").default(sql`CURRENT_TIMESTAMP`).notNull(),
});

// AI System State - tracks emergency stops, mode changes
export const aiSystemState = pgTable("ai_system_state", {
  id: serial("id").primaryKey(),
  mode: text("mode").notNull().default("active"),
  aiPaused: boolean("ai_paused").notNull().default(false),
  codeChangesFrozen: boolean("code_changes_frozen").notNull().default(false),
  manualOnly: boolean("manual_only").notNull().default(false),
  lastChangedBy: text("last_changed_by").default("system"),
  source: text("source").notNull().default("system"),
  createdAt: timestamp("created_at").default(sql`CURRENT_TIMESTAMP`).notNull(),
  updatedAt: timestamp("updated_at").default(sql`CURRENT_TIMESTAMP`).notNull(),
});

// Insert schemas
export const insertAiRequestSchema = createInsertSchema(aiRequests).omit({ id: true, createdAt: true, updatedAt: true });
export const insertAiAgentEventSchema = createInsertSchema(aiAgentEvents).omit({ id: true, createdAt: true });
export const insertAiDecisionSchema = createInsertSchema(aiDecisions).omit({ id: true, createdAt: true });
export const insertAiCodeChangeSchema = createInsertSchema(aiCodeChanges).omit({ id: true, createdAt: true });
export const insertAiApprovalSchema = createInsertSchema(aiApprovals).omit({ id: true, createdAt: true });
export const insertAiSystemStateSchema = createInsertSchema(aiSystemState).omit({ id: true, createdAt: true, updatedAt: true });

// Types
export type AiRequest = typeof aiRequests.$inferSelect;
export type InsertAiRequest = z.infer<typeof insertAiRequestSchema>;
export type AiAgentEvent = typeof aiAgentEvents.$inferSelect;
export type InsertAiAgentEvent = z.infer<typeof insertAiAgentEventSchema>;
export type AiDecision = typeof aiDecisions.$inferSelect;
export type InsertAiDecision = z.infer<typeof insertAiDecisionSchema>;
export type AiCodeChange = typeof aiCodeChanges.$inferSelect;
export type InsertAiCodeChange = z.infer<typeof insertAiCodeChangeSchema>;
export type AiApproval = typeof aiApprovals.$inferSelect;
export type InsertAiApproval = z.infer<typeof insertAiApprovalSchema>;
export type AiSystemState = typeof aiSystemState.$inferSelect;
export type InsertAiSystemState = z.infer<typeof insertAiSystemStateSchema>;
