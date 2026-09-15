"""Queued check that a git push actually landed on the serving process.

HANDOVER deploy-proof rule: diff the served asset hash AND the response body
of the change class; never treat push (or HTTP 200) as live.

Why this exists
---------------
A git push has been treated as live while Railway had not picked it up (once
40+ minutes). Agents then reported commits live that were not. The frontend
bundle hash (`index-*.js`) is a useful signal for client ships, but it is not
a deploy proof: backend / SSR / auth can land with the SAME hash (15 Sep: auth
lock #6/#7 and SSR #5 both served `index-eWXmctMP.js`).

So this monitor proves landing with (1) the served entry-asset hash AND (2)
real response bodies of the change class — never hash alone, never HTTP status
alone.

What this actually probes
-------------------------
Named probes against APP_BASE_URL (default https://founderconsole.ai), plus a
control that MUST fail. A monitor that cannot fail is more dangerous than no
monitor: it converts an untested system into a reassuring one.

1. CONTROL — request a deliberately fake entry asset
   `/assets/index-DEPLOYMONITOR-CONTROL-MISS.js`. It MUST be 404. If that path
   returns 200 (SPA fallback, catch-all static, CDN serving index.html for any
   `/assets/index-*.js`), the hash check is meaningless: report
   `control-failed`, never green.

   Body control: the same HTML used for the hash extract MUST NOT contain the
   sentinel `DEPLOYMONITOR-BODY-CONTROL-MISS`. If it does, a contains-check
   cannot be trusted (always-200 shell echoing our marker, or a matcher that
   cannot fail) — also `control-failed`.

2. HASH — homepage HTML, extract `src="/assets/index-<hash>.js"`. Always
   recorded. If EXPECTED_INDEX_HASH / DEPLOY_EXPECTED_INDEX_HASH is set,
   require a match. If unset, record-only: do not fail on hash, because
   backend ships often keep it.

3. BODY — fail closed on missing content, not just 200:
   - GET /health JSON: status healthy, database connected, redis connected,
     routers_loaded true
   - GET /pricing body contains `id="ssr-content"`
   - GET /api/leads unauth: HTTP 401 (not 404). GET is auth; POST stays public
     so this monitor does not require POST 401.
   - GET /api/events unauth: 401

The probe list is small and named. Extra `path::substring` body probes can be
appended via DEPLOY_LANDED_EXTRA_BODY_PROBES without rewriting this module.

Env:
  APP_BASE_URL                 site to probe (default https://founderconsole.ai)
  EXPECTED_INDEX_HASH          optional; also DEPLOY_EXPECTED_INDEX_HASH
  DEPLOY_LANDED_ENABLED=false  disable the loop entirely
  DEPLOY_LANDED_INTERVAL_SECONDS   default 600 (10 min)
  CRAWLER_ALERT_EMAIL          where failures are emailed (same helper as
                               crawler_health)
  DEPLOY_LANDED_EXTRA_BODY_PROBES  `|`-separated `path::substring` pairs
  DEPLOY_LANDED_CONTROL_ASSET      fake asset path (default as above)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Callable

import httpx

logger = logging.getLogger(__name__)

# HANDOVER deploy-proof: served hash + change-class body, never push = live.
MONITOR_UA = "FounderConsole-deploy-landed/1.0"
DEFAULT_SITE = "https://founderconsole.ai"
DEFAULT_INTERVAL_SECONDS = 600
CONTROL_ASSET_DEFAULT = "/assets/index-DEPLOYMONITOR-CONTROL-MISS.js"
BODY_CONTROL_SENTINEL = "DEPLOYMONITOR-BODY-CONTROL-MISS"
INDEX_SRC_RE = re.compile(r"""src=["']/assets/index-([^/"']+)\.js["']""")

GetFn = Callable[..., tuple[int, str]]


def _site() -> str:
    return os.environ.get("APP_BASE_URL", DEFAULT_SITE).rstrip("/")


def _control_asset_path() -> str:
    return os.environ.get("DEPLOY_LANDED_CONTROL_ASSET", CONTROL_ASSET_DEFAULT)


def _expected_index_hash() -> str | None:
    raw = (
        os.environ.get("DEPLOY_EXPECTED_INDEX_HASH")
        or os.environ.get("EXPECTED_INDEX_HASH")
        or ""
    ).strip()
    return _normalize_index_hash(raw) if raw else None


def _normalize_index_hash(value: str) -> str:
    name = value.strip().strip("/").split("/")[-1]
    if name.startswith("index-"):
        name = name[len("index-") :]
    if name.endswith(".js"):
        name = name[: -len(".js")]
    return name


def _interval_seconds() -> int:
    raw = os.environ.get("DEPLOY_LANDED_INTERVAL_SECONDS", str(DEFAULT_INTERVAL_SECONDS))
    try:
        return max(60, int(raw))
    except ValueError:
        return DEFAULT_INTERVAL_SECONDS


def _snippet(body: str, limit: int = 160) -> str:
    collapsed = " ".join((body or "").split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 1] + "…"


@dataclass
class ProbeSpec:
    """One named check. Extra body probes are the same shape."""

    name: str
    path: str
    expected_status: int = 200
    contains: str | None = None
    json_equals: dict[str, object] | None = None
    follow_redirects: bool = True


@dataclass
class ProbeResult:
    name: str
    path: str
    status: int
    ok: bool
    detail: str = ""
    snippet: str = ""
    kind: str = "probe"  # probe | control | hash

    def describe(self) -> str:
        outcome = "ok" if self.ok else "FAIL"
        extra = f"  {self.detail}" if self.detail else ""
        return f"{outcome:4s}  {self.name:16s}  {self.path}  -> {self.status}{extra}"


@dataclass
class DeployReport:
    status: str  # "ok" | "failed" | "control-failed"
    index_hash: str | None = None
    expected_index_hash: str | None = None
    results: list[ProbeResult] = field(default_factory=list)
    note: str = ""

    @property
    def failures(self) -> list[ProbeResult]:
        return [r for r in self.results if not r.ok]

    @property
    def probes(self) -> list[ProbeResult]:
        return [r for r in self.results if r.kind != "control"]

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "index_hash": self.index_hash,
            "expected_index_hash": self.expected_index_hash,
            "checked": len(self.probes),
            "failed": len([r for r in self.probes if not r.ok]),
            "note": self.note,
            "failures": [
                {
                    "name": r.name,
                    "path": r.path,
                    "status": r.status,
                    "kind": r.kind,
                    "detail": r.detail,
                    "snippet": r.snippet,
                }
                for r in self.failures
            ],
        }


def default_probes() -> list[ProbeSpec]:
    """Keep this list small. Extra body strings belong in env, not a rewrite."""
    return [
        ProbeSpec(
            name="health",
            path="/health",
            expected_status=200,
            json_equals={
                "status": "healthy",
                "database": "connected",
                "redis": "connected",
                "routers_loaded": True,
            },
        ),
        ProbeSpec(
            name="pricing-ssr",
            path="/pricing",
            expected_status=200,
            contains='id="ssr-content"',
        ),
        ProbeSpec(
            name="leads-auth",
            path="/api/leads",
            expected_status=401,
            follow_redirects=False,
        ),
        ProbeSpec(
            name="events-auth",
            path="/api/events",
            expected_status=401,
            follow_redirects=False,
        ),
    ]


def extra_body_probes() -> list[ProbeSpec]:
    """DEPLOY_LANDED_EXTRA_BODY_PROBES=' /features::id="ssr-content"|/about::id="ssr-content" '."""
    raw = os.environ.get("DEPLOY_LANDED_EXTRA_BODY_PROBES", "").strip()
    if not raw:
        return []
    specs: list[ProbeSpec] = []
    for part in raw.split("|"):
        part = part.strip()
        if not part or "::" not in part:
            logger.warning("[deploy-landed] ignoring extra body probe %r (want path::substring)", part)
            continue
        path, contains = part.split("::", 1)
        path = path.strip()
        contains = contains.strip()
        if not path.startswith("/"):
            path = "/" + path
        if not contains:
            logger.warning("[deploy-landed] ignoring extra body probe %r (empty substring)", part)
            continue
        specs.append(
            ProbeSpec(
                name=f"body:{path}",
                path=path,
                expected_status=200,
                contains=contains,
            )
        )
    return specs


def _get(path: str, *, follow_redirects: bool = True, timeout: float = 15.0) -> tuple[int, str]:
    headers = {"User-Agent": MONITOR_UA}
    try:
        resp = httpx.get(
            f"{_site()}{path}",
            headers=headers,
            timeout=timeout,
            follow_redirects=follow_redirects,
        )
        return resp.status_code, resp.text
    except Exception as exc:  # noqa: BLE001 — a failed probe is a finding, not a crash
        return 0, str(exc)


def extract_index_hash(html: str) -> str | None:
    match = INDEX_SRC_RE.search(html or "")
    return match.group(1) if match else None


def _evaluate_spec(spec: ProbeSpec, status: int, body: str) -> ProbeResult:
    problems: list[str] = []
    if status != spec.expected_status:
        problems.append(f"status {status}, expected {spec.expected_status}")

    if spec.contains:
        if spec.contains not in (body or ""):
            problems.append(f"missing {spec.contains!r}")

    if spec.json_equals:
        try:
            data = json.loads(body)
        except (TypeError, json.JSONDecodeError):
            problems.append("body is not JSON")
            data = None
        if isinstance(data, dict):
            for key, expected in spec.json_equals.items():
                actual = data.get(key)
                if actual != expected:
                    problems.append(f"{key}={actual!r} want {expected!r}")
        elif data is not None:
            problems.append("JSON body is not an object")

    ok = not problems
    detail = "; ".join(problems) if problems else _pass_detail(spec, body)
    return ProbeResult(
        name=spec.name,
        path=spec.path,
        status=status,
        ok=ok,
        detail=detail,
        snippet=_snippet(body),
        kind="probe",
    )


def _pass_detail(spec: ProbeSpec, body: str) -> str:
    if spec.json_equals:
        try:
            data = json.loads(body)
            bits = [f"{k}={data.get(k)!r}" for k in spec.json_equals]
            return " ".join(bits)
        except (TypeError, json.JSONDecodeError):
            return "json ok"
    if spec.contains:
        return f"contains {spec.contains!r}"
    return f"status {spec.expected_status}"


def format_report(report: DeployReport) -> str:
    """Pasteable evidence: hash, each probe status + snippet."""
    lines = [
        f"deploy-landed  status={report.status}",
        f"site: {_site()}",
    ]
    expected = report.expected_index_hash
    if expected:
        match = "match" if report.index_hash == expected else "MISMATCH"
        lines.append(f"index_hash: {report.index_hash or '(none)'}  expected: {expected}  [{match}]")
    else:
        lines.append(f"index_hash: {report.index_hash or '(none)'}  expected: unset (recorded only)")
    if report.note:
        lines.append(report.note)
    for r in report.results:
        prefix = "CONTROL" if r.kind == "control" else ("HASH" if r.kind == "hash" else "PROBE")
        lines.append(f"  [{prefix}] {r.describe()}")
        if not r.ok and r.snippet:
            lines.append(f"           snippet: {r.snippet}")
    n_ok = len(report.probes) - len([r for r in report.probes if not r.ok])
    lines.append(f"{n_ok}/{len(report.probes)} probes ok — status: {report.status}")
    return "\n".join(lines)


def check_deploy_landed(*, get: GetFn | None = None) -> DeployReport:
    """Run controls + hash + body probes once. Blocking; call via asyncio.to_thread."""
    fetch = get or _get
    results: list[ProbeResult] = []
    note_parts: list[str] = []

    # Control first — it decides whether hash/body assertions mean anything.
    control_path = _control_asset_path()
    control_status, control_body = fetch(control_path, follow_redirects=True)
    control_ok = control_status == 404
    results.append(
        ProbeResult(
            name="fake-asset",
            path=control_path,
            status=control_status,
            ok=control_ok,
            detail="must 404" if control_ok else "must 404 — hash check is meaningless",
            snippet=_snippet(control_body),
            kind="control",
        )
    )
    if not control_ok:
        note_parts.append(
            f"CONTROL FAILED: fake asset {control_path} returned {control_status or control_body}, "
            f"expected 404. Served-hash assertions cannot be trusted."
        )

    homepage_status, homepage_body = fetch("/", follow_redirects=True)
    body_control_ok = BODY_CONTROL_SENTINEL not in (homepage_body or "")
    results.append(
        ProbeResult(
            name="body-absent",
            path="/",
            status=homepage_status,
            ok=body_control_ok,
            detail=(
                f"{BODY_CONTROL_SENTINEL!r} absent"
                if body_control_ok
                else f"{BODY_CONTROL_SENTINEL!r} present — contains-check is meaningless"
            ),
            snippet=_snippet(homepage_body),
            kind="control",
        )
    )
    if not body_control_ok:
        note_parts.append(
            f"CONTROL FAILED: homepage body contains {BODY_CONTROL_SENTINEL!r}, "
            f"so a substring assertion cannot be trusted."
        )

    index_hash = extract_index_hash(homepage_body) if homepage_status == 200 else None
    expected = _expected_index_hash()
    hash_problems: list[str] = []
    if homepage_status != 200:
        hash_problems.append(f"homepage status {homepage_status}, expected 200")
    elif not index_hash:
        hash_problems.append("no src=/assets/index-<hash>.js in homepage HTML")
    elif expected and index_hash != expected:
        hash_problems.append(f"hash {index_hash!r} != expected {expected!r}")

    # Unset expected hash: record only, do not fail on the hash itself.
    hash_ok = not hash_problems
    results.append(
        ProbeResult(
            name="homepage-hash",
            path="/",
            status=homepage_status,
            ok=hash_ok,
            detail=(
                "; ".join(hash_problems)
                if hash_problems
                else (
                    f"hash={index_hash} recorded"
                    + (" (no expected hash)" if not expected else f" matches {expected}")
                )
            ),
            snippet=_snippet(homepage_body),
            kind="hash",
        )
    )

    for spec in default_probes() + extra_body_probes():
        status, body = fetch(spec.path, follow_redirects=spec.follow_redirects)
        results.append(_evaluate_spec(spec, status, body))

    control_failed = any(r.kind == "control" and not r.ok for r in results)
    probe_failed = any(r.kind != "control" and not r.ok for r in results)
    if control_failed:
        status = "control-failed"
    elif probe_failed:
        status = "failed"
    else:
        status = "ok"

    report = DeployReport(
        status=status,
        index_hash=index_hash,
        expected_index_hash=expected,
        results=results,
        note=" ".join(note_parts),
    )

    if control_failed:
        logger.error("[deploy-landed] CONTROL FAILED — do not trust hash/body: %s", report.note)
    elif probe_failed:
        logger.error(
            "[deploy-landed] %d probe(s) FAILED (hash=%s): %s",
            len([r for r in report.probes if not r.ok]),
            index_hash,
            ", ".join(r.describe() for r in report.failures),
        )
    else:
        logger.info(
            "[deploy-landed] ok  hash=%s  %d probes",
            index_hash,
            len(report.probes),
        )

    return report


def _alert_html(report: DeployReport) -> str:
    rows = "".join(
        f"<tr><td style='padding:4px 12px 4px 0'>{r.kind}</td>"
        f"<td style='padding:4px 12px 4px 0'><b>{r.name}</b></td>"
        f"<td style='padding:4px 12px 4px 0'>{r.path}</td>"
        f"<td style='padding:4px 12px 4px 0'>{r.status}</td>"
        f"<td style='padding:4px 0'>{r.detail}</td></tr>"
        for r in report.failures
    )
    headline = (
        "Deploy-landed: control failed — hash/body assertions are meaningless"
        if report.status == "control-failed"
        else f"Deploy-landed: {len(report.failures)} check(s) failed"
    )
    return (
        f"<h2>{headline}</h2>"
        f"<p>site={_site()} hash={report.index_hash or '(none)'} "
        f"expected={report.expected_index_hash or 'unset'}</p>"
        f"<p>{report.note}</p>"
        f"<table style='font:14px/1.5 system-ui,sans-serif;border-collapse:collapse'>{rows}</table>"
        f"<pre style='font:12px/1.4 ui-monospace,monospace;white-space:pre-wrap'>"
        f"{format_report(report)}</pre>"
    )


async def _send_alert(report: DeployReport) -> None:
    to = os.environ.get("CRAWLER_ALERT_EMAIL")
    if not to:
        logger.warning("[deploy-landed] CRAWLER_ALERT_EMAIL unset — no alert sent")
        return
    try:
        from server.email.service import send_email

        subject = (
            "[FounderConsole] Deploy-landed CONTROL FAILED — do not trust hash"
            if report.status == "control-failed"
            else f"[FounderConsole] Deploy-landed {len(report.failures)} check(s) FAILED"
        )
        await send_email(to=to, subject=subject, html_content=_alert_html(report))
        logger.info("[deploy-landed] alert emailed to %s", to)
    except Exception:  # noqa: BLE001 — a broken alert must not kill the loop
        logger.exception("[deploy-landed] could not send alert email")


async def run_deploy_landed_loop(interval_seconds: int | None = None) -> None:
    """Background loop. Runs once shortly after startup, then every ~10 min.

    Async, and the probes run in a worker thread: httpx.get is blocking and this
    is started with asyncio.create_task alongside the other schedulers in
    main.py. A blocking sleep here would stall the entire event loop.
    """
    if os.environ.get("DEPLOY_LANDED_ENABLED") == "false":
        logger.info("[deploy-landed] disabled via DEPLOY_LANDED_ENABLED=false")
        return

    if interval_seconds is None:
        interval_seconds = _interval_seconds()

    await asyncio.sleep(60)  # let the app finish booting before hitting its own front door
    while True:
        try:
            report = await asyncio.to_thread(check_deploy_landed)
            if report.status != "ok":
                await _send_alert(report)
        except Exception:  # noqa: BLE001
            logger.exception("[deploy-landed] check itself failed")
        await asyncio.sleep(interval_seconds)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    rep = check_deploy_landed()
    print(format_report(rep))
    raise SystemExit(0 if rep.status == "ok" else 1)
