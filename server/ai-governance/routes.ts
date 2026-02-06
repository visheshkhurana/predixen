import type { Express, Request, Response } from "express";
import crypto from "crypto";
import { db } from "../db";
import { eq, desc, and } from "drizzle-orm";
import {
  aiRequests,
  aiAgentEvents,
  aiDecisions,
  aiCodeChanges,
  aiApprovals,
  aiSystemState,
} from "../../shared/models/aiGovernance";

const N8N_WEBHOOK_BASE = process.env.N8N_WEBHOOK_BASE || "https://n8n.predixen.app/webhook";
const SHARED_SECRET = process.env.AI_GOVERNANCE_SECRET || "predixen-ai-governance-secret-change-me";
const CALLBACK_TOLERANCE_MS = 5 * 60 * 1000; // 5 min replay protection

function signPayload(body: string): string {
  return crypto.createHmac("sha256", SHARED_SECRET).update(body).digest("hex");
}

function verifySignature(body: string, signature: string | undefined): boolean {
  if (!signature) return false;
  const expected = signPayload(body);
  return crypto.timingSafeEqual(Buffer.from(expected), Buffer.from(signature));
}

function generateRequestId(): string {
  return `req_${crypto.randomUUID()}`;
}

async function getOrCreateSystemState() {
  const existing = await db.select().from(aiSystemState).orderBy(desc(aiSystemState.id)).limit(1);
  if (existing.length > 0) return existing[0];
  const [created] = await db.insert(aiSystemState).values({
    mode: "active",
    aiPaused: false,
    codeChangesFrozen: false,
    manualOnly: false,
    lastChangedBy: "system",
    source: "system",
  }).returning();
  return created;
}

async function forwardToN8n(endpoint: string, payload: any): Promise<boolean> {
  try {
    const body = JSON.stringify(payload);
    const signature = signPayload(body);
    const response = await fetch(`${N8N_WEBHOOK_BASE}/${endpoint}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-PREDIXEN-SIGNATURE": signature,
      },
      body,
    });
    return response.ok;
  } catch (error) {
    console.error(`[AI-GOV] Failed to forward to n8n ${endpoint}:`, error);
    return false;
  }
}

export function registerAiGovernanceRoutes(app: Express) {
  // GET /admin/ai-governance/state - Full boardroom state
  app.get("/admin/ai-governance/state", async (_req: Request, res: Response) => {
    try {
      const systemState = await getOrCreateSystemState();
      const recentRequests = await db.select().from(aiRequests).orderBy(desc(aiRequests.createdAt)).limit(20);
      const recentEvents = await db.select().from(aiAgentEvents).orderBy(desc(aiAgentEvents.createdAt)).limit(50);
      const recentDecisions = await db.select().from(aiDecisions).orderBy(desc(aiDecisions.createdAt)).limit(20);
      const recentCodeChanges = await db.select().from(aiCodeChanges).orderBy(desc(aiCodeChanges.createdAt)).limit(20);
      const recentApprovals = await db.select().from(aiApprovals).orderBy(desc(aiApprovals.createdAt)).limit(20);

      // Build agent statuses from most recent events
      const agents = ["CEO", "CFO", "CRO", "CPO", "CTO", "RISK", "CHIEF_OF_STAFF"];
      const agentStatuses: Record<string, { status: string; summary: string | null; confidence: number | null; lastUpdate: string | null }> = {};
      for (const agent of agents) {
        const latestEvent = recentEvents.find((e) => e.agent === agent);
        agentStatuses[agent] = {
          status: latestEvent?.status || "idle",
          summary: latestEvent?.summary || null,
          confidence: latestEvent?.confidence || null,
          lastUpdate: latestEvent?.createdAt?.toISOString() || null,
        };
      }

      // Current active request (most recent pending/in_progress)
      const activeRequest = recentRequests.find((r) => r.status === "pending" || r.status === "in_progress") || null;

      res.json({
        systemState,
        agents: agentStatuses,
        activeRequest,
        requests: recentRequests,
        events: recentEvents,
        decisions: recentDecisions,
        codeChanges: recentCodeChanges,
        approvals: recentApprovals,
      });
    } catch (error) {
      console.error("[AI-GOV] Error fetching state:", error);
      res.status(500).json({ error: "Failed to fetch AI governance state" });
    }
  });

  // POST /admin/ai-governance/ask - Founder asks a question
  app.post("/admin/ai-governance/ask", async (req: Request, res: Response) => {
    try {
      const { question, constraints, type } = req.body;
      if (!question) {
        return res.status(400).json({ error: "Question is required" });
      }

      const systemState = await getOrCreateSystemState();
      if (systemState.aiPaused || systemState.manualOnly) {
        return res.status(403).json({ error: "AI is currently paused or in manual-only mode" });
      }

      const requestId = generateRequestId();
      const contextSnapshotId = `snap_${crypto.randomUUID()}`;

      const [request] = await db.insert(aiRequests).values({
        requestId,
        companyId: "predixen",
        initiator: "founder",
        type: type || "decision",
        question,
        constraints: constraints || {},
        contextSnapshotId,
        status: "pending",
        source: "founder",
      }).returning();

      // Forward to n8n
      const n8nPayload = {
        request_id: requestId,
        company_id: "predixen",
        initiator: "founder",
        type: type || "decision",
        question,
        constraints: constraints || {},
        context_snapshot_id: contextSnapshotId,
      };

      const forwarded = await forwardToN8n("ceo-decision", n8nPayload);

      res.json({
        success: true,
        request,
        n8nForwarded: forwarded,
      });
    } catch (error) {
      console.error("[AI-GOV] Error in ask:", error);
      res.status(500).json({ error: "Failed to process question" });
    }
  });

  // POST /admin/ai-governance/approve - Approve a decision
  app.post("/admin/ai-governance/approve", async (req: Request, res: Response) => {
    try {
      const { requestId, decisionId, reason } = req.body;
      if (!requestId) {
        return res.status(400).json({ error: "requestId is required" });
      }

      const [approval] = await db.insert(aiApprovals).values({
        requestId,
        decisionId: decisionId || null,
        approved: true,
        approvedBy: "founder",
        reason: reason || null,
        source: "founder",
      }).returning();

      // Update decision status
      if (decisionId) {
        await db.update(aiDecisions).set({ status: "approved" }).where(eq(aiDecisions.id, decisionId));
      }

      // Update request status
      await db.update(aiRequests).set({ status: "approved" }).where(eq(aiRequests.requestId, requestId));

      // Forward approval to n8n
      const n8nPayload = {
        request_id: requestId,
        approved: true,
        approved_by: "founder",
        timestamp: new Date().toISOString(),
      };
      await forwardToN8n("decision-approval", n8nPayload);

      res.json({ success: true, approval });
    } catch (error) {
      console.error("[AI-GOV] Error in approve:", error);
      res.status(500).json({ error: "Failed to approve" });
    }
  });

  // POST /admin/ai-governance/reject - Reject a decision
  app.post("/admin/ai-governance/reject", async (req: Request, res: Response) => {
    try {
      const { requestId, decisionId, reason } = req.body;
      if (!requestId) {
        return res.status(400).json({ error: "requestId is required" });
      }

      const [approval] = await db.insert(aiApprovals).values({
        requestId,
        decisionId: decisionId || null,
        approved: false,
        approvedBy: "founder",
        reason: reason || null,
        source: "founder",
      }).returning();

      if (decisionId) {
        await db.update(aiDecisions).set({ status: "rejected" }).where(eq(aiDecisions.id, decisionId));
      }
      await db.update(aiRequests).set({ status: "rejected" }).where(eq(aiRequests.requestId, requestId));

      // Forward rejection to n8n
      const n8nPayload = {
        request_id: requestId,
        approved: false,
        approved_by: "founder",
        reason: reason || "Rejected by founder",
        timestamp: new Date().toISOString(),
      };
      await forwardToN8n("decision-approval", n8nPayload);

      res.json({ success: true, approval });
    } catch (error) {
      console.error("[AI-GOV] Error in reject:", error);
      res.status(500).json({ error: "Failed to reject" });
    }
  });

  // POST /admin/ai-governance/emergency - Emergency controls
  app.post("/admin/ai-governance/emergency", async (req: Request, res: Response) => {
    try {
      const { action } = req.body;
      const validActions = ["pause_all", "freeze_code", "manual_only", "resume_all"];
      if (!action || !validActions.includes(action)) {
        return res.status(400).json({ error: `Invalid action. Must be one of: ${validActions.join(", ")}` });
      }

      let updates: any = { lastChangedBy: "founder", updatedAt: new Date() };
      switch (action) {
        case "pause_all":
          updates = { ...updates, aiPaused: true, mode: "paused" };
          break;
        case "freeze_code":
          updates = { ...updates, codeChangesFrozen: true };
          break;
        case "manual_only":
          updates = { ...updates, manualOnly: true, mode: "manual" };
          break;
        case "resume_all":
          updates = { ...updates, aiPaused: false, codeChangesFrozen: false, manualOnly: false, mode: "active" };
          break;
      }

      const existing = await getOrCreateSystemState();
      await db.update(aiSystemState).set(updates).where(eq(aiSystemState.id, existing.id));
      const [updated] = await db.select().from(aiSystemState).where(eq(aiSystemState.id, existing.id));

      // Notify n8n of emergency action
      await forwardToN8n("emergency-action", {
        action,
        timestamp: new Date().toISOString(),
        initiated_by: "founder",
      });

      res.json({ success: true, systemState: updated });
    } catch (error) {
      console.error("[AI-GOV] Error in emergency:", error);
      res.status(500).json({ error: "Failed to process emergency action" });
    }
  });

  // POST /admin/ai-governance/callback - FROM n8n only
  app.post("/admin/ai-governance/callback", async (req: Request, res: Response) => {
    try {
      // Verify n8n signature
      const rawBody = JSON.stringify(req.body);
      const signature = req.headers["x-predixen-signature"] as string;

      if (!verifySignature(rawBody, signature)) {
        console.warn("[AI-GOV] Invalid callback signature");
        return res.status(401).json({ error: "Invalid signature" });
      }

      // Timestamp replay protection
      const { timestamp } = req.body;
      if (timestamp) {
        const eventTime = new Date(timestamp).getTime();
        const now = Date.now();
        if (Math.abs(now - eventTime) > CALLBACK_TOLERANCE_MS) {
          return res.status(400).json({ error: "Timestamp outside tolerance window" });
        }
      }

      const { event_type, request_id } = req.body;
      if (!event_type || !request_id) {
        return res.status(400).json({ error: "event_type and request_id required" });
      }

      switch (event_type) {
        case "agent_update": {
          const { agent, status, summary, confidence, severity } = req.body;
          await db.insert(aiAgentEvents).values({
            requestId: request_id,
            eventType: event_type,
            agent: agent || "UNKNOWN",
            status: status || "responded",
            summary,
            confidence,
            severity: severity || "normal",
            source: "agent",
            rawPayload: req.body,
          });

          // Update request status to in_progress
          await db.update(aiRequests).set({ status: "in_progress" }).where(eq(aiRequests.requestId, request_id));
          break;
        }
        case "decision_ready": {
          const { decision, agent_positions } = req.body;
          if (decision) {
            await db.insert(aiDecisions).values({
              requestId: request_id,
              label: decision.label || "Untitled Decision",
              confidence: decision.confidence,
              rationale: decision.rationale,
              actions: decision.actions,
              requiresApproval: decision.requires_approval ?? true,
              agentPositions: agent_positions,
              status: "pending",
              source: "agent",
            });
          }

          await db.update(aiRequests).set({ status: "decision_ready" }).where(eq(aiRequests.requestId, request_id));
          break;
        }
        case "code_change": {
          const { branch, files_changed, tests_passed, risk_level, summary } = req.body;
          await db.insert(aiCodeChanges).values({
            requestId: request_id,
            branch,
            filesChanged: files_changed,
            testsPassed: tests_passed,
            riskLevel: risk_level || "medium",
            summary,
            status: "pending",
            source: "agent",
          });
          break;
        }
        default:
          console.warn(`[AI-GOV] Unknown event_type: ${event_type}`);
      }

      res.json({ success: true, received: event_type });
    } catch (error) {
      console.error("[AI-GOV] Error in callback:", error);
      res.status(500).json({ error: "Failed to process callback" });
    }
  });
}
