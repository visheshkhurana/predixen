import type { Express, Request, Response } from "express";
import OpenAI from "openai";

const openai = new OpenAI({
  apiKey: process.env.AI_INTEGRATIONS_OPENAI_API_KEY,
  baseURL: process.env.AI_INTEGRATIONS_OPENAI_BASE_URL,
});

interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
}

export function registerChatRoutes(app: Express): void {
  app.post("/api/ai/chat", async (req: Request, res: Response) => {
    try {
      const { messages, context } = req.body as {
        messages: ChatMessage[];
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

      if (!messages || !Array.isArray(messages)) {
        return res.status(400).json({ error: "Messages array is required" });
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
        model: "gpt-4o",
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

  app.post("/api/ai/quick-answer", async (req: Request, res: Response) => {
    try {
      const { question, context } = req.body;

      if (!question) {
        return res.status(400).json({ error: "Question is required" });
      }

      const systemPrompt = `You are a concise financial advisor. Answer in 2-3 sentences max.
${context ? `Context: Cash $${context.cashOnHand?.toLocaleString()}, Revenue $${context.monthlyRevenue?.toLocaleString()}/mo, Expenses $${context.monthlyExpenses?.toLocaleString()}/mo, Growth ${context.growthRate}%` : ""}`;

      const response = await openai.chat.completions.create({
        model: "gpt-4o",
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
}
