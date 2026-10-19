import express, { type Express, type Request, type Response } from "express";
import OpenAI from "openai";
import { requireAuth } from "../../middleware/requireAuth";
import { aiUserRateLimit, type AiRateLimitOptions } from "../../middleware/aiRateLimit";

export interface ChatRouteOptions {
  /** Override the OpenAI client. Tests inject a fake so the success path never hits the network. */
  getOpenAIClient?: () => OpenAI | null;
  rateLimit?: AiRateLimitOptions;
}

const configuredOpenAIKey =
  process.env.AI_INTEGRATIONS_OPENAI_API_KEY || process.env.OPENAI_API_KEY;
let cachedOpenAIClient: OpenAI | null | undefined;

function getOpenAIClient(): OpenAI | null {
  if (cachedOpenAIClient !== undefined) {
    return cachedOpenAIClient;
  }

  if (!configuredOpenAIKey) {
    cachedOpenAIClient = null;
    return cachedOpenAIClient;
  }

  cachedOpenAIClient = new OpenAI({
    apiKey: configuredOpenAIKey,
    baseURL: process.env.AI_INTEGRATIONS_OPENAI_BASE_URL,
  });
  return cachedOpenAIClient;
}

interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
}

// The system prompt is ours: callers may only send their own user/assistant
// turns, bounded in count and length, so a client cannot rewrite the advisor's
// instructions or pad a request to burn tokens.
const MAX_MESSAGES = 30;
const MAX_CONTENT_CHARS = 4000;

export function sanitizeChatMessages(raw: unknown): ChatMessage[] | null {
  if (!Array.isArray(raw)) return null;
  return raw
    .filter(
      (m): m is ChatMessage =>
        !!m &&
        typeof m === "object" &&
        (m.role === "user" || m.role === "assistant") &&
        typeof m.content === "string",
    )
    .slice(-MAX_MESSAGES)
    .map((m) => ({ role: m.role, content: m.content.slice(0, MAX_CONTENT_CHARS) }));
}

export function registerChatRoutes(app: Express, options: ChatRouteOptions = {}): void {
  const resolveClient = options.getOpenAIClient ?? getOpenAIClient;
  const limitAi = aiUserRateLimit(options.rateLimit);
  // Every /api/ai/* path is Express-owned (LOCAL_API_PREFIXES skips the FastAPI proxy).
  // Auth is mounted on the prefix so a new route cannot ship unauthenticated.
  const router = express.Router();
  router.use(requireAuth);

  router.post("/chat", limitAi, async (req: Request, res: Response) => {
    try {
      const { messages: rawMessages, context } = req.body as {
        messages: unknown;
        context?: {
          companyName?: string;
          industry?: string;
          stage?: string;
          cashOnHand?: number;
          monthlyRevenue?: number;
          monthlyExpenses?: number;
          growthRate?: number;
          employees?: number;
          targetRunway?: number;
        };
      };

      const messages = sanitizeChatMessages(rawMessages);
      if (!messages || messages.length === 0) {
        return res.status(400).json({ error: "Messages array is required" });
      }

      const openai = resolveClient();
      if (!openai) {
        return res.status(503).json({
          error:
            "AI chat is not configured. Set AI_INTEGRATIONS_OPENAI_API_KEY or OPENAI_API_KEY.",
        });
      }

      const systemPrompt = `You are a helpful financial advisor AI assistant for startups. You help founders understand their financial metrics, runway, and make data-driven decisions.

${context ? `Current Company Context:
- Company: ${context.companyName || "Not specified"}
- Industry: ${context.industry || "Not specified"}
- Stage: ${context.stage || "Not specified"}
- Cash on Hand: $${context.cashOnHand?.toLocaleString() || "Not specified"}
- Monthly Revenue: $${context.monthlyRevenue?.toLocaleString() || "Not specified"}
- Monthly Expenses: $${context.monthlyExpenses?.toLocaleString() || "Not specified"}
- Net Burn Rate: $${((context.monthlyExpenses || 0) - (context.monthlyRevenue || 0)).toLocaleString()}${(context.monthlyExpenses || 0) < (context.monthlyRevenue || 0) ? " (Net Positive/Surplus)" : ""}
- Growth Rate: ${context.growthRate || 0}%
- Employees: ${context.employees || "Not specified"}
- Target Runway: ${context.targetRunway || 18} months

Based on this data:
- Current Runway: ${context.cashOnHand && context.monthlyExpenses && context.monthlyRevenue 
  ? (context.monthlyExpenses - context.monthlyRevenue) > 0 
    ? (context.cashOnHand / (context.monthlyExpenses - context.monthlyRevenue)).toFixed(1) + " months"
    : "Sustainable (net positive cash flow)"
  : "Cannot calculate"}
` : ""}

Be concise but insightful. Use specific numbers from the context when answering questions. If asked about external data or news, acknowledge that you don't have real-time web access but provide helpful guidance based on general knowledge.`;

      const fullMessages: ChatMessage[] = [
        { role: "system", content: systemPrompt },
        ...messages,
      ];

      res.setHeader("Content-Type", "text/event-stream");
      res.setHeader("Cache-Control", "no-cache");
      res.setHeader("Connection", "keep-alive");

      const stream = await openai.chat.completions.create({
        model: "gpt-5",
        messages: fullMessages,
        stream: true,
        max_tokens: 1024,
      });

      for await (const chunk of stream) {
        const content = chunk.choices[0]?.delta?.content || "";
        if (content) {
          res.write(`data: ${JSON.stringify({ content })}\n\n`);
        }
      }

      res.write(`data: ${JSON.stringify({ done: true })}\n\n`);
      res.end();
    } catch (error) {
      console.error("Error in AI chat:", error);
      if (res.headersSent) {
        res.write(`data: ${JSON.stringify({ error: "Failed to get AI response" })}\n\n`);
        res.end();
      } else {
        res.status(500).json({ error: "Failed to get AI response" });
      }
    }
  });

  router.post("/quick-answer", limitAi, async (req: Request, res: Response) => {
    try {
      const { question, context } = req.body;

      if (!question) {
        return res.status(400).json({ error: "Question is required" });
      }

      const openai = resolveClient();
      if (!openai) {
        return res.status(503).json({
          error:
            "AI quick answers are not configured. Set AI_INTEGRATIONS_OPENAI_API_KEY or OPENAI_API_KEY.",
        });
      }

      const systemPrompt = `You are a concise financial advisor. Answer in 2-3 sentences max.
${context ? `Context: Cash $${context.cashOnHand?.toLocaleString()}, Revenue $${context.monthlyRevenue?.toLocaleString()}/mo, Expenses $${context.monthlyExpenses?.toLocaleString()}/mo, Growth ${context.growthRate}%` : ""}`;

      const response = await openai.chat.completions.create({
        model: "gpt-5",
        messages: [
          { role: "system", content: systemPrompt },
          { role: "user", content: question },
        ],
        max_tokens: 256,
      });

      res.json({
        answer: response.choices[0]?.message?.content || "Unable to generate response",
      });
    } catch (error) {
      console.error("Error in quick answer:", error);
      res.status(500).json({ error: "Failed to get AI response" });
    }
  });

  app.use("/api/ai", router);
}
