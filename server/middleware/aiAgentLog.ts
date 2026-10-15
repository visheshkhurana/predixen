import type { Request, Response, NextFunction } from "express";

/**
 * Server-side classification of AI-agent and search-crawler traffic.
 *
 * Why this exists. `client/src/lib/posthog.ts` attributes a pageview by reading
 * `document.referrer`, so the "From search or AI" channel can only ever see a
 * visitor whose browser ran, looked at its own referrer and reported it. A
 * crawler does none of those three things: it fetches the HTML and leaves. So
 * the channel reported a hard zero while GPTBot, PerplexityBot and Googlebot
 * were reading the site every day. A metric that cannot move is worse than a
 * missing one — a zero reads as "no traffic" when the truth is "not measured".
 * No client-side change can fix that by construction, because the client never
 * runs. The only place that sees a raw HTTP fetch is the gateway, and the
 * gateway is this process (see the Dockerfile: one container, Express at the
 * edge, spawning uvicorn behind it).
 *
 * What this is: measurement, and only measurement. It reads the User-Agent
 * request header and writes one structured line per recognised request to
 * stdout. It never touches the response — no status, no header, no body, no
 * redirect, no route. It does not decide anything, so it cannot break anything.
 *
 * Privacy. The line carries no IP, no cookie, no referrer, no session id, no
 * query string and no header other than the User-Agent. A crawler's
 * User-Agent is public by definition — it is that bot announcing itself. The
 * two things that are deliberately absent are the two that would make this a
 * privacy regression rather than a measurement: the client address, and the
 * query string (which is where `/auth?email=…` style values live). `req.path`
 * drops the query string, which is why it is used rather than `originalUrl`.
 *
 * Related, and deliberately separate: `server/middleware/geoRestrict.ts` owns a
 * second User-Agent list. That one decides whether to serve or 403, and it is
 * strict about staying generous because a false positive there has cost real ad
 * money. This one only counts, so a false positive costs a log line and a false
 * negative costs an invisible agent. The two lists are not merged on purpose —
 * driving the gate from a measurement table would mean a logging edit could
 * change who gets served.
 */

export type UaClass = "ai_agent" | "search_crawler" | "ads_crawler" | "other_bot";

export interface UaClassification {
  /** The vendor's own token, so the log reads like the bot's docs. */
  agent: string;
  class: UaClass;
  /** Only set for `other_bot`: the UA itself is the finding. */
  ua?: string;
}

/**
 * Ordered, first match wins.
 *
 * Order matters wherever one token is a substring of another, and there is
 * exactly one such pair here: `applebot-extended` contains `applebot`. The
 * longer token is listed first so a Google-AI-training fetch is not counted as
 * an Apple search crawl. `server/tests/ai-agent-log.test.ts` pins that.
 *
 * Tokens are matched case-insensitively against the whole UA string with
 * `includes`, the same way `geoRestrict.ts` matches, because real UAs append
 * version and `(+http://…/bot.html)` noise to the token.
 */
export const KNOWN_AGENTS: ReadonlyArray<{
  token: string;
  agent: string;
  class: UaClass;
}> = [
  // --- AI assistants and AI search, fetching on a user's behalf or indexing
  // for one. This is the family the "From search or AI" metric exists for.
  { token: "chatgpt-user", agent: "ChatGPT-User", class: "ai_agent" },
  { token: "oai-searchbot", agent: "OAI-SearchBot", class: "ai_agent" },
  { token: "gptbot", agent: "GPTBot", class: "ai_agent" },
  { token: "perplexity-user", agent: "Perplexity-User", class: "ai_agent" },
  { token: "perplexitybot", agent: "PerplexityBot", class: "ai_agent" },
  { token: "claude-user", agent: "Claude-User", class: "ai_agent" },
  { token: "claude-searchbot", agent: "Claude-SearchBot", class: "ai_agent" },
  { token: "claudebot", agent: "ClaudeBot", class: "ai_agent" },
  { token: "claude-web", agent: "Claude-Web", class: "ai_agent" },
  { token: "anthropic-ai", agent: "anthropic-ai", class: "ai_agent" },
  // Google's AI surfaces. `Google-Extended` is the token Google's AI training
  // honours; `Google-CloudVertexBot` is the Vertex/Gemini fetch agent.
  // `GoogleOther` is Google's generic research crawler — not Search, so it is
  // not folded into Googlebot.
  { token: "google-extended", agent: "Google-Extended", class: "ai_agent" },
  { token: "google-cloudvertexbot", agent: "Google-CloudVertexBot", class: "ai_agent" },
  { token: "googleother", agent: "GoogleOther", class: "ai_agent" },
  // The longer Apple token first — see the ordering note above.
  { token: "applebot-extended", agent: "Applebot-Extended", class: "ai_agent" },
  { token: "meta-externalagent", agent: "meta-externalagent", class: "ai_agent" },
  { token: "meta-externalfetcher", agent: "meta-externalfetcher", class: "ai_agent" },
  { token: "cohere-training-data-crawler", agent: "cohere-training-data-crawler", class: "ai_agent" },
  { token: "cohere-ai", agent: "cohere-ai", class: "ai_agent" },
  { token: "duckassistbot", agent: "DuckAssistBot", class: "ai_agent" },
  { token: "mistralai-user", agent: "MistralAI-User", class: "ai_agent" },
  { token: "amazonbot", agent: "Amazonbot", class: "ai_agent" },
  { token: "youbot", agent: "YouBot", class: "ai_agent" },
  { token: "diffbot", agent: "Diffbot", class: "ai_agent" },
  { token: "ccbot", agent: "CCBot", class: "ai_agent" },
  { token: "bytespider", agent: "Bytespider", class: "ai_agent" },
  { token: "imagesiftbot", agent: "ImagesiftBot", class: "ai_agent" },
  { token: "timpibot", agent: "Timpibot", class: "ai_agent" },
  { token: "omgilibot", agent: "Omgilibot", class: "ai_agent" },

  // --- Search engines. The classic index crawlers, which are the "search"
  // half of the channel and the reason a page's Search Console numbers and
  // PostHog's never agreed.
  { token: "googlebot", agent: "Googlebot", class: "search_crawler" },
  { token: "google-inspectiontool", agent: "Google-InspectionTool", class: "search_crawler" },
  { token: "storebot-google", agent: "Storebot-Google", class: "search_crawler" },
  { token: "google-read-aloud", agent: "Google-Read-Aloud", class: "search_crawler" },
  { token: "feedfetcher-google", agent: "FeedFetcher-Google", class: "search_crawler" },
  { token: "google-site-verification", agent: "Google-Site-Verification", class: "search_crawler" },
  { token: "bingbot", agent: "Bingbot", class: "search_crawler" },
  { token: "bingpreview", agent: "BingPreview", class: "search_crawler" },
  { token: "applebot", agent: "Applebot", class: "search_crawler" },
  { token: "duckduckbot", agent: "DuckDuckBot", class: "search_crawler" },
  { token: "baiduspider", agent: "Baiduspider", class: "search_crawler" },
  { token: "yandex", agent: "YandexBot", class: "search_crawler" },
  { token: "sogou", agent: "Sogou", class: "search_crawler" },
  { token: "exabot", agent: "Exabot", class: "search_crawler" },
  { token: "seznambot", agent: "SeznamBot", class: "search_crawler" },
  { token: "naver", agent: "Naver", class: "search_crawler" },
  { token: "petalbot", agent: "PetalBot", class: "search_crawler" },
  { token: "qwantify", agent: "Qwantify", class: "search_crawler" },
  { token: "mojeekbot", agent: "MojeekBot", class: "search_crawler" },
  { token: "slurp", agent: "Yahoo Slurp", class: "search_crawler" },

  // --- Paid-traffic verifiers. Not the metric, but they arrive from the same
  // place, and `geoRestrict.ts` records what mis-handling AdsBot already cost:
  // two days of disapproved ads. Counting them keeps them out of `other_bot`,
  // where they would look like an unidentified agent.
  { token: "adsbot-google", agent: "AdsBot-Google", class: "ads_crawler" },
  { token: "mediapartners-google", agent: "Mediapartners-Google", class: "ads_crawler" },
  { token: "adidxbot", agent: "AdIdxBot", class: "ads_crawler" },
];

/**
 * Backstop for a crawler that is not in the table, so a bot we have never heard
 * of shows up as *something* rather than as nothing.
 *
 * This is the one design decision here worth arguing about. A new agent — the
 * next ChatGPT-User — would otherwise be invisible, and "invisible" is
 * indistinguishable from "did not visit", which is the exact failure this whole
 * change exists to undo. So an unrecognised non-browser client is logged as
 * `other_bot` **with its User-Agent attached**, because the UA is the finding.
 *
 * It is narrower than `geoRestrict.ts`'s equivalent on purpose: that one may
 * err toward letting things through, this one only errs toward noise. It is
 * also noisier by nature, so the liveness probe is carved out below.
 */
const GENERIC_BOT_UA =
  /(bot\b|\bbot|crawler|spider|crawl|fetcher|scraper|headlesschrome|python-requests|curl\/|wget\/|axios\/|go-http-client|okhttp|libwww|undici|node-fetch)/i;

/**
 * The container's own liveness probe, and the reason the backstop needs an
 * exemption at all.
 *
 * `Dockerfile:64` runs `curl -fsS http://localhost:5000/health` every 30s. With
 * no exemption that is one `other_bot` line every 30 seconds — 2,880 a day of
 * our own health check, which would bury the traffic this log exists to show.
 * It is excluded on the path because that is exact and stable, rather than on
 * the client address, which `trust proxy` rewrites.
 *
 * Only the backstop is exempted. A recognised crawler requesting `/health` is
 * still logged: that is a real thing to know.
 */
const LIVENESS_PATHS = new Set(["/health", "/healthz"]);

/** Longest raw UA we will echo into a log line. */
const UA_ECHO_LIMIT = 120;

/**
 * Longest request id we will echo into a log line — and, because `server/index.ts`
 * imports this constant, the longest id the response is allowed to carry.
 *
 * The id is the other stranger-controlled field in the line, and it was
 * unbounded while the User-Agent beside it was capped. One unauthenticated
 * request carrying a 5,000-character `x-request-id` therefore inflated a single
 * log line to kilobytes, repeatably, on every connection.
 *
 * EXPORTED, so the bound has ONE owner. Capping here alone was not enough and
 * shipped a defect: `server/index.ts` writes the id it read onto the response as
 * `X-Request-ID`, so a capped log line and an uncapped response header disagreed
 * for every id over the limit — an operator holding the response id would grep
 * the log and find nothing. With the id capped once, where it is generated or
 * first read, the value in the request header, the value on the response and the
 * value in the log line are the same string by construction rather than by two
 * files holding the same number and hoping.
 *
 * The read below still slices. That is not a duplicate of the gateway's cap: this
 * file's invariant is that nothing unbounded reaches the log line, and it should
 * hold whether or not whoever set the header remembered to bound it.
 */
export const ID_ECHO_LIMIT = 64;

/**
 * Classify a User-Agent string. Pure — no request, no I/O — so it is testable
 * on its own and cannot be affected by what the request did.
 *
 * Returns null for a browser and for an empty header. Null means "not
 * classified", which is not the same as "not a bot": the caller logs nothing,
 * and that silence is the point.
 */
export function classifyUserAgent(ua: string | undefined | null): UaClassification | null {
  const s = String(ua || "").toLowerCase();
  if (s.length === 0) return null;

  for (const entry of KNOWN_AGENTS) {
    if (s.includes(entry.token)) return { agent: entry.agent, class: entry.class };
  }

  if (GENERIC_BOT_UA.test(s)) {
    return { agent: "unrecognised", class: "other_bot", ua: s.slice(0, UA_ECHO_LIMIT) };
  }

  return null;
}

export interface AiAgentLogOptions {
  /**
   * Where a line goes. Defaults to stdout, which is what Railway captures.
   * Tests inject a collector so they assert on real output without polluting
   * the test runner's own stream.
   */
  write?: (line: string) => void;
  /** Clock, injectable so a test can assert the field without racing it. */
  now?: () => number;
}

/**
 * Express middleware. Classifies the request, then reports the *finished*
 * response.
 *
 * It hangs the write off `res.on("finish")` rather than logging on the way in,
 * because the status code is the half that tells you whether the crawler
 * actually got a page. A 200 from GPTBot and a 404 from GPTBot are completely
 * different findings, and a log written on entry cannot tell them apart.
 */
export function aiAgentLog(opts: AiAgentLogOptions = {}) {
  const write =
    opts.write ?? ((line: string) => { process.stdout.write(line + "\n"); });
  const now = opts.now ?? (() => Date.now());

  return (req: Request, res: Response, next: NextFunction): void => {
    const rawUa = req.headers["user-agent"];
    const match = classifyUserAgent(typeof rawUa === "string" ? rawUa : undefined);

    // A browser, an empty header, or a liveness probe: not our business.
    if (!match) return next();
    if (match.class === "other_bot" && LIVENESS_PATHS.has(req.path)) return next();

    // Read the path NOW, not inside the `finish` handler below.
    //
    // This is not a style choice — it is the difference between a working metric
    // and a useless one, and it was found by running the real server rather than
    // the tests. Express rewrites `req.url` while dispatching a wildcard layer:
    // after `app.use("*", …)` matches, `req.path` is `"/"` and only
    // `req.originalUrl` keeps the real path. In production almost every page is
    // answered by exactly that wildcard, the SPA catch-all in `static.ts`, so
    // reading `req.path` in the callback logged `path:"/"` for every crawler hit
    // — the agent right, the page wrong, and wrong in a way that looks fine.
    // `server/tests/ai-agent-log.test.ts` pins it.
    //
    // `path` (not `originalUrl`) is still what is recorded: the path property
    // carries no query string, which is deliberate — no metric here needs one and
    // they are where `?email=…` style values live.
    const path = req.path;
    const method = req.method;
    const requestId =
      typeof req.headers["x-request-id"] === "string"
        ? req.headers["x-request-id"].slice(0, ID_ECHO_LIMIT)
        : null;

    const started = now();

    res.on("finish", () => {
      const line: Record<string, string | number | null> = {
        event: "ai_agent_hit",
        ts: new Date().toISOString(),
        agent: match.agent,
        ua_class: match.class,
        method,
        path,
        status: res.statusCode,
        ms: now() - started,
        request_id: requestId,
      };
      // Only on `other_bot`, where the UA is the entire point of the line.
      if (match.ua) line.ua = match.ua;

      // One line, always. A multi-line JSON payload is unparseable by every
      // log tool that splits on newline, which is all of them.
      write(JSON.stringify(line));
    });

    next();
  };
}
