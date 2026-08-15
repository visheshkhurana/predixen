"""Daily check that crawlers can still reach the site.

Why this exists
---------------
On 12 August 2026 a country-restriction middleware shipped whose crawler
exemption matched "googlebot" but not "adsbot-google". Google's ad
landing-page crawler got a 403 from a non-allowed country and disapproved
every ad in the account with "Destination not working". Ad delivery stopped
for two days.

Nothing caught it, because a geo-conditional break is invisible from a single
vantage point: every manual check came from an allowed country and returned
200. The site was healthy for us and broken for Google, and the only visible
symptom was traffic quietly going to zero.

What this actually probes
-------------------------
Two tiers, because they fail for different reasons and one of them can be
silently meaningless:

1. AVAILABILITY — crawler user agents against the live site from wherever this
   happens to run. Catches outages, bad deploys, a 500 on the ad landing page,
   a robots.txt that stopped rendering. Always meaningful.

2. GEO EXEMPTION — the same crawler user agents, but claiming an IP in a
   country the gate does not allow. This is the tier that would have caught the
   original bug, and tier 1 cannot: from an allowed country the request passes
   the gate on the country check whether or not the crawler exemption still
   works, so a regression stays green.

   Tier 2 is only meaningful when the gate is actually blocking. That is what
   the CONTROL probe is for — an ordinary browser UA from the same disallowed
   IP, which must come back 403. If the control gets a 200 then the gate is off
   (GEO_RESTRICTION_ENABLED=false), or the spoofed header is not reaching the
   middleware, and the crawler results prove nothing at all. That case reports
   "gate-inactive" rather than a green tick, because a monitor that cannot fail
   is more dangerous than no monitor: it converts an untested system into a
   reassuring one.

Spoofing the client IP works because the app runs behind a proxy with
`trust proxy` on, and its clientIp() takes the left-most public address in
X-Forwarded-For — the value we send. The edge appends its own hop to the right,
so ours stays left-most and wins.

Env:
  APP_BASE_URL          site to probe (default https://founderconsole.ai)
  GEO_PROBE_IP          disallowed-country IP for tier 2 (default 46.4.36.44, DE)
  CRAWLER_ALERT_EMAIL   where failures are emailed
  CRAWLER_HEALTH_ENABLED=false   disable the loop entirely
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from typing import Iterable

import httpx

logger = logging.getLogger(__name__)

SITE = os.environ.get("APP_BASE_URL", "https://founderconsole.ai").rstrip("/")

# Hetzner, Germany. Any stable address outside GEO_ALLOWED_COUNTRIES works; the
# control probe re-verifies the choice on every run rather than trusting it, so
# if this IP is ever reassigned or the allowlist grows to include Germany the
# check reports gate-inactive instead of quietly passing.
GEO_PROBE_IP = os.environ.get("GEO_PROBE_IP", "46.4.36.44")

ADSBOT_UA = "AdsBot-Google (+http://www.google.com/adsbot.html)"
GOOGLEBOT_UA = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
)

# (label, user-agent, path). Ad landing pages first — those are the ones whose
# breakage costs money directly — then the pages we need indexed.
PROBES: list[tuple[str, str, str]] = [
    ("adsbot", ADSBOT_UA, "/"),
    (
        "adsbot-mobile",
        "Mozilla/5.0 (Linux; Android 6.0.1;) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/136.0.0.0 Mobile Safari/537.36 (compatible; AdsBot-Google-Mobile; "
        "+http://www.google.com/mobile/adsbot.html)",
        "/",
    ),
    ("adsbot-calculator", ADSBOT_UA, "/tools/runway-calculator"),
    ("adsbot-ai-cfo", ADSBOT_UA, "/ai-cfo"),
    ("googlebot", GOOGLEBOT_UA, "/"),
    ("googlebot-blog", GOOGLEBOT_UA, "/blog"),
    ("bingbot", "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)", "/"),
    ("claudebot", "ClaudeBot/1.0", "/"),
    ("gptbot", "GPTBot/1.1", "/"),
    ("robots", GOOGLEBOT_UA, "/robots.txt"),
    ("sitemap", GOOGLEBOT_UA, "/sitemap.xml"),
]


@dataclass
class ProbeResult:
    label: str
    path: str
    status: int
    ok: bool
    tier: str = "availability"
    error: str | None = None

    def describe(self) -> str:
        return f"{self.label} {self.path} -> {self.status or self.error}"


@dataclass
class HealthReport:
    status: str  # "ok" | "failed" | "gate-inactive"
    results: list[ProbeResult] = field(default_factory=list)
    control_status: int = 0
    note: str = ""

    @property
    def failures(self) -> list[ProbeResult]:
        return [r for r in self.results if not r.ok]

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "checked": len(self.results),
            "failed": len(self.failures),
            "control_status": self.control_status,
            "note": self.note,
            "failures": [
                {"label": r.label, "path": r.path, "status": r.status,
                 "tier": r.tier, "error": r.error}
                for r in self.failures
            ],
        }


def _get(path: str, ua: str, xff: str | None = None, timeout: float = 15.0) -> tuple[int, str | None]:
    headers = {"User-Agent": ua}
    if xff:
        headers["X-Forwarded-For"] = xff
    try:
        resp = httpx.get(f"{SITE}{path}", headers=headers, timeout=timeout, follow_redirects=True)
        return resp.status_code, None
    except Exception as exc:  # noqa: BLE001 — a failed probe is a finding, not a crash
        return 0, str(exc)


def _run_tier(probes: Iterable[tuple[str, str, str]], tier: str, xff: str | None) -> list[ProbeResult]:
    results: list[ProbeResult] = []
    for label, ua, path in probes:
        status, error = _get(path, ua, xff)
        results.append(ProbeResult(label, path, status, status == 200, tier, error))
    return results


def check_crawler_health() -> HealthReport:
    """Run both tiers once. Blocking; call via asyncio.to_thread."""
    results = _run_tier(PROBES, "availability", None)

    # Control first — it decides whether tier 2 means anything.
    control_status, control_error = _get("/", BROWSER_UA, GEO_PROBE_IP)
    gate_active = control_status == 403

    note = ""
    if gate_active:
        results += _run_tier(PROBES, "geo-exemption", GEO_PROBE_IP)
    else:
        note = (
            f"Geo-exemption tier SKIPPED: control probe (browser UA from {GEO_PROBE_IP}) "
            f"returned {control_status or control_error}, expected 403. The country gate is "
            f"not blocking, so crawler-exemption regressions cannot be detected."
        )

    failures = [r for r in results if not r.ok]
    if failures:
        status = "failed"
    elif not gate_active:
        status = "gate-inactive"
    else:
        status = "ok"

    report = HealthReport(status=status, results=results, control_status=control_status, note=note)

    if failures:
        # Deliberately ERROR and deliberately verbose. The failure mode this
        # guards against looked like nothing at all for two days.
        logger.error(
            "[crawler-health] %d/%d probes FAILED — ads and indexing are at risk: %s",
            len(failures), len(results), ", ".join(r.describe() for r in failures),
        )
    elif not gate_active:
        logger.warning("[crawler-health] %s", note)
    else:
        logger.info("[crawler-health] all %d probes returned 200 (gate verified active)", len(results))

    return report


def _alert_html(report: HealthReport) -> str:
    rows = "".join(
        f"<tr><td style='padding:4px 12px 4px 0'>{r.tier}</td>"
        f"<td style='padding:4px 12px 4px 0'><b>{r.label}</b></td>"
        f"<td style='padding:4px 12px 4px 0'>{r.path}</td>"
        f"<td style='padding:4px 0'>{r.status or r.error}</td></tr>"
        for r in report.failures
    )
    if report.status == "gate-inactive":
        return (
            f"<h2>Crawler health: gate inactive</h2><p>{report.note}</p>"
            f"<p>All {len(report.results)} availability probes returned 200, so the site is up — "
            f"but the geo-exemption check could not run, and a repeat of the "
            f"August 2026 ad outage would not be caught.</p>"
        )
    return (
        f"<h2>Crawler health: {len(report.failures)} of {len(report.results)} probes failed</h2>"
        f"<p>These user agents could not reach {SITE}. Google disapproves ads when "
        f"AdsBot cannot fetch the landing page.</p>"
        f"<table style='font:14px/1.5 system-ui,sans-serif;border-collapse:collapse'>{rows}</table>"
        f"<p style='color:#666'>Probe IP for the geo-exemption tier: {GEO_PROBE_IP}. "
        f"Control probe returned {report.control_status}.</p>"
    )


async def _send_alert(report: HealthReport) -> None:
    to = os.environ.get("CRAWLER_ALERT_EMAIL")
    if not to:
        logger.warning("[crawler-health] CRAWLER_ALERT_EMAIL unset — no alert sent")
        return
    try:
        from server.email.service import send_email

        subject = (
            "[FounderConsole] Crawler health: gate inactive"
            if report.status == "gate-inactive"
            else f"[FounderConsole] {len(report.failures)} crawler probes FAILED — ads at risk"
        )
        await send_email(to=to, subject=subject, html_content=_alert_html(report))
        logger.info("[crawler-health] alert emailed to %s", to)
    except Exception:  # noqa: BLE001 — a broken alert must not kill the loop
        logger.exception("[crawler-health] could not send alert email")


async def run_crawler_health_loop(interval_seconds: int = 86400) -> None:
    """Background loop. Runs once shortly after startup, then daily.

    Async, and the probes run in a worker thread: httpx.get is blocking and this
    is started with asyncio.create_task alongside the other schedulers in
    main.py. A blocking sleep here would stall the entire event loop — every
    request on the box — for a day.
    """
    if os.environ.get("CRAWLER_HEALTH_ENABLED") == "false":
        logger.info("[crawler-health] disabled via CRAWLER_HEALTH_ENABLED=false")
        return

    await asyncio.sleep(60)  # let the app finish booting before hitting its own front door
    while True:
        try:
            report = await asyncio.to_thread(check_crawler_health)
            if report.status != "ok":
                await _send_alert(report)
        except Exception:  # noqa: BLE001
            logger.exception("[crawler-health] check itself failed")
        await asyncio.sleep(interval_seconds)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    rep = check_crawler_health()
    for r in rep.failures:
        print(f"FAIL [{r.tier:15s}] {r.label:20s} {r.path:26s} {r.status or r.error}")
    passed = len(rep.results) - len(rep.failures)
    print(f"\n{passed}/{len(rep.results)} probes returned 200 — status: {rep.status}")
    if rep.note:
        print(f"\n{rep.note}")
    raise SystemExit(0 if rep.status == "ok" else 1)
