// The generic non-browser User-Agent heuristic, in ONE place.
//
// It used to be two literals — `geoRestrict.ts` and `aiAgentLog.ts` each had
// their own copy — and they had ALREADY DIVERGED. `geoRestrict.ts` carried six
// tokens the newer copy lacked: `monitor`, `preview`, `validator`,
// `feedparser`, `java/` and `^node$`. The consequence was concrete and one-way:
// a `Java/1.8` client, or anything matching monitor/preview/validator/
// feedparser, was treated as a bot by the geo gate — and therefore waved
// through it — while being INVISIBLE to the AI-agent metric. The log
// undercounted exactly the traffic the older middleware lets past.
//
// WHAT IS SHARED IS THE HEURISTIC, NOT THE DECISION. The two callers want
// opposite things from it:
//
//   `geoRestrict.ts`   uses a match to BYPASS the gate — a false positive
//                      serves a request the gate would have blocked, which
//                      costs nothing. Narrowing the list here would make the
//                      gate STRICTER and could start blocking real people,
//                      which is the direction that breaks things quietly.
//   `aiAgentLog.ts`    uses a match to CLASSIFY as `other_bot` — a false
//                      positive costs one log line. Widening the list makes
//                      the metric more complete.
//
// So the list may be WIDENED and must never be narrowed: widening is safe for
// both callers, narrowing is only safe for one of them. The merged list is
// therefore `geoRestrict.ts`'s, which was the wider of the two — merging the
// other way would have silently made the geo gate stricter, and that is a
// behaviour change to who gets served, not a logging change.
//
// `server/tests/test_bot_ua_shared.py` pins both halves of that: that neither
// middleware declares its own copy again, and that the tokens `geoRestrict.ts`
// relied on are all still present, so a future edit cannot narrow it by
// accident.
export const GENERIC_BOT_UA =
  /(bot\b|\bbot|crawler|spider|crawl|fetcher|scraper|monitor|preview|validator|feedparser|headlesschrome|python-requests|curl\/|wget\/|axios\/|go-http-client|okhttp|java\/|libwww|undici|node-fetch|^node$)/i;
