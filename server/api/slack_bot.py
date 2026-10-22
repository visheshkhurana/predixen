"""
Slack Copilot Integration — slash commands and event handlers
for FounderConsole within Slack workspaces.

Commands:
  /fc-runway      — Show current runway and cash position
  /fc-metrics     — Show key financial metrics snapshot
  /fc-alerts      — Show active smart alerts
  /fc-ask <query> — Ask the AI copilot any question
  /fc-simulate    — Get simulation summary
  /fc-link <code> — Link this workspace/channel to a FounderConsole company
                    (code from POST /companies/{id}/integrations/slack/link-code)
"""
import os
import hmac
import hashlib
import secrets
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from server.core.db import get_db
from server.core.security import get_current_user
from server.core.company_access import get_user_company, get_user_company_role
from server.core.company_metadata import save_metadata_value, delete_metadata_value
from server.models.company import Company
from server.models.user import User
from server.utils.survival import survival_pct
from server.models.truth_scan import TruthScan
from server.models.financial import FinancialRecord

logger = logging.getLogger(__name__)

# Prefix deliberately excludes /api. Express proxies /api/* to this app
# with pathRewrite {"^/api": ""} (server/index.ts), so a prefix of
# "/api/slack" would be looked up here as "/api/slack" while the request
# actually arrives as "/slack" — a guaranteed 404 for every caller.
router = APIRouter(prefix="/slack", tags=["slack"])


def _verify_slack_signature(
    body: bytes, timestamp: str, signature: str
) -> bool:
    """Verify that the request is genuinely from Slack."""
    signing_secret = os.getenv("SLACK_SIGNING_SECRET", "")
    if not signing_secret:
        logger.warning("SLACK_SIGNING_SECRET not set — rejecting request")
        return False

    if not timestamp or not signature:
        return False

    try:
        if abs(time.time() - float(timestamp)) > 60 * 5:
            return False
    except (ValueError, TypeError):
        return False

    sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
    computed = "v0=" + hmac.new(
        signing_secret.encode(), sig_basestring.encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(computed, signature)


SLACK_META_KEY = "slack_integration"
LINK_CODE_META_KEY = "slack_link_code"
LINK_CODE_TTL_SECONDS = 15 * 60
_LINK_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _hash_link_code(code: str) -> str:
    return hashlib.sha256(code.strip().upper().encode()).hexdigest()


def _company_by_meta(db: Session, key: str, field: str, value: str) -> Optional[Company]:
    """Find a company by a string inside metadata_json, in the database.

    A JSON-path filter, not a Python scan, so it covers every company
    (the old lookup only looked at the first 100 rows).
    """
    return (
        db.query(Company)
        .filter(Company.metadata_json[key][field].as_string() == value)
        .order_by(Company.id.asc())
        .first()
    )


def _get_company_from_slack(
    db: Session, team_id: str, channel_id: str
) -> Optional[Company]:
    """Look up the company associated with this Slack workspace or channel."""
    if channel_id:
        company = _company_by_meta(db, SLACK_META_KEY, "channel_id", channel_id)
        if company is not None:
            return company
    if team_id:
        company = _company_by_meta(db, SLACK_META_KEY, "team_id", team_id)
        if company is not None:
            return company
    return None


def _link_with_code(
    db: Session, code: str, team_id: str, channel_id: str, slack_user_id: str
) -> Optional[Company]:
    """Consume a one-time link code and store the Slack team/channel on its company."""
    if not code or not team_id:
        return None
    company = _company_by_meta(db, LINK_CODE_META_KEY, "code_hash", _hash_link_code(code))
    if company is None:
        return None
    pending = (company.metadata_json or {}).get(LINK_CODE_META_KEY) or {}
    try:
        expired = float(pending.get("expires_at", 0)) < time.time()
    except (TypeError, ValueError):
        expired = True
    # Single use either way.
    delete_metadata_value(db, company, LINK_CODE_META_KEY)
    if expired:
        return None

    # A workspace answers for one company: drop any older link to this team.
    for _ in range(50):
        previous = _company_by_meta(db, SLACK_META_KEY, "team_id", team_id)
        if previous is None or previous.id == company.id:
            break
        delete_metadata_value(db, previous, SLACK_META_KEY)

    save_metadata_value(db, company, SLACK_META_KEY, {
        "team_id": team_id,
        "channel_id": channel_id or None,
        "linked_by_slack_user": slack_user_id or None,
        "linked_by_user_id": pending.get("created_by"),
        "linked_at": datetime.utcnow().isoformat(),
    })
    return company


def _get_metrics_snapshot(db: Session, company: Company) -> Dict[str, Any]:
    """Get the latest financial metrics for a company."""
    truth_scan = (
        db.query(TruthScan)
        .filter(TruthScan.company_id == company.id)
        .order_by(TruthScan.created_at.desc())
        .first()
    )

    latest_fin = (
        db.query(FinancialRecord)
        .filter(FinancialRecord.company_id == company.id)
        .order_by(FinancialRecord.period_start.desc())
        .first()
    )

    metrics = {}
    if truth_scan and truth_scan.outputs_json:
        ts_metrics = truth_scan.outputs_json.get("metrics", {})
        for key in [
            "mrr", "arr", "cash_balance", "runway_months",
            "net_burn", "gross_margin", "headcount",
            "churn_rate", "cac", "ltv",
        ]:
            val = ts_metrics.get(key)
            if isinstance(val, dict):
                metrics[key] = val.get("value", 0)
            elif isinstance(val, (int, float)):
                metrics[key] = val

    if latest_fin:
        if not metrics.get("mrr"):
            metrics["mrr"] = float(latest_fin.revenue or 0)
        if not metrics.get("cash_balance"):
            metrics["cash_balance"] = float(latest_fin.cash_balance or 0)

    return metrics


def _format_currency(value: float) -> str:
    if value >= 1_000_000:
        return f"${value/1_000_000:.1f}M"
    elif value >= 1_000:
        return f"${value/1_000:.1f}K"
    return f"${value:,.0f}"


def _build_runway_response(metrics: Dict[str, Any], company_name: str) -> Dict[str, Any]:
    runway = metrics.get("runway_months", 0)
    cash = metrics.get("cash_balance", 0)
    burn = metrics.get("net_burn", 0)

    status_emoji = ":white_check_mark:" if runway >= 18 else ":warning:" if runway >= 12 else ":rotating_light:"

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{company_name} — Runway"},
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Runway:* {status_emoji} {runway:.1f} months"},
                {"type": "mrkdwn", "text": f"*Cash:* {_format_currency(cash)}"},
                {"type": "mrkdwn", "text": f"*Net Burn:* {_format_currency(burn)}/mo"},
            ],
        },
    ]

    if runway < 12:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": ":rotating_light: *Action needed:* Runway is below 12 months. "
                        "Consider cost optimization or begin fundraising preparation.",
            },
        })

    return {"response_type": "ephemeral", "blocks": blocks}


def _build_metrics_response(metrics: Dict[str, Any], company_name: str) -> Dict[str, Any]:
    mrr = metrics.get("mrr", 0)
    arr = metrics.get("arr", mrr * 12)
    cash = metrics.get("cash_balance", 0)
    runway = metrics.get("runway_months", 0)
    burn = metrics.get("net_burn", 0)
    margin = metrics.get("gross_margin", 0)
    headcount = metrics.get("headcount", 0)
    churn = metrics.get("churn_rate", 0)

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{company_name} — Key Metrics"},
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*MRR:* {_format_currency(mrr)}"},
                {"type": "mrkdwn", "text": f"*ARR:* {_format_currency(arr)}"},
                {"type": "mrkdwn", "text": f"*Cash:* {_format_currency(cash)}"},
                {"type": "mrkdwn", "text": f"*Runway:* {runway:.1f} months"},
                {"type": "mrkdwn", "text": f"*Net Burn:* {_format_currency(burn)}/mo"},
                {"type": "mrkdwn", "text": f"*Gross Margin:* {margin:.1f}%"},
                {"type": "mrkdwn", "text": f"*Headcount:* {headcount}"},
                {"type": "mrkdwn", "text": f"*Churn:* {churn:.2f}%"},
            ],
        },
        {"type": "divider"},
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": "Data from FounderConsole. Open the dashboard for full details."},
            ],
        },
    ]

    return {"response_type": "ephemeral", "blocks": blocks}


def _build_alerts_response(
    db: Session, company: Company, company_name: str
) -> Dict[str, Any]:
    metadata = company.metadata_json or {}
    alerts = metadata.get("smart_alerts", [])

    active_alerts = [a for a in alerts if not a.get("acknowledged")]

    if not active_alerts:
        return {
            "response_type": "ephemeral",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f":white_check_mark: *{company_name}* — No active alerts. All systems healthy.",
                    },
                },
            ],
        }

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{company_name} — Active Alerts"},
        },
    ]

    severity_emoji = {
        "critical": ":rotating_light:",
        "warning": ":warning:",
        "info": ":information_source:",
    }

    for alert in active_alerts[:5]:
        emoji = severity_emoji.get(alert.get("severity"), ":bell:")
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{emoji} *{alert.get('title', 'Alert')}*\n{alert.get('message', '')}",
            },
        })
        if alert.get("suggestedAction"):
            blocks.append({
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"_Suggested:_ {alert['suggestedAction']}"},
                ],
            })

    if len(active_alerts) > 5:
        blocks.append({
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"... and {len(active_alerts) - 5} more alerts. View all in FounderConsole."},
            ],
        })

    return {"response_type": "ephemeral", "blocks": blocks}


async def _handle_ask_command(
    query: str, db: Session, company: Company
) -> Dict[str, Any]:
    """Process an /fc-ask query through the copilot router agent."""
    try:
        from server.copilot.agents import RouterAgent
        from server.copilot.agents.base import CompanyKnowledgeBase
        from server.lib.llm.llm_router import get_llm_router

        llm_router = get_llm_router()
        router = RouterAgent(llm_router=llm_router)

        ckb = CompanyKnowledgeBase(
            company_id=company.id,
            company_name=company.name or "Company",
        )

        metrics = _get_metrics_snapshot(db, company)
        ckb.financials = metrics

        context = {"source": "slack"}
        response = await router.process(query, ckb, context)

        response_text = response.raw_response or ""
        if not response_text and response.findings:
            response_text = "\n".join(f"• {f}" for f in response.findings[:5])
        if not response_text:
            response_text = "I analyzed your question but couldn't generate a detailed response. Please try the FounderConsole dashboard for full analysis."

        if len(response_text) > 2900:
            response_text = response_text[:2900] + "\n\n_...truncated. View full response in FounderConsole._"

        return {
            "response_type": "ephemeral",
            "blocks": [
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": response_text},
                },
                {"type": "divider"},
                {
                    "type": "context",
                    "elements": [
                        {"type": "mrkdwn", "text": ":brain: Powered by FounderConsole AI Copilot"},
                    ],
                },
            ],
        }
    except Exception as e:
        logger.error(f"Copilot query failed: {e}")
        return {
            "response_type": "ephemeral",
            "text": f"Sorry, I couldn't process that question right now. Error: {str(e)[:100]}",
        }


def _runway_p50(results: Dict[str, Any]) -> Optional[float]:
    """The engine writes runway as {"p10","p50","p90"}; older rows flattened it."""
    runway = results.get("runway")
    candidates = [
        runway.get("p50") if isinstance(runway, dict) else None,
        results.get("runway_p50"),
        results.get("median_runway"),
    ]
    for value in candidates:
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


@router.post("/commands")
async def handle_slash_command(request: Request, db: Session = Depends(get_db)):
    """Handle Slack slash commands."""
    body = await request.body()
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")

    if not _verify_slack_signature(body, timestamp, signature):
        raise HTTPException(status_code=401, detail="Invalid Slack signature")

    form = await request.form()
    command = form.get("command", "")
    text = form.get("text", "").strip()
    team_id = form.get("team_id", "")
    channel_id = form.get("channel_id", "")
    user_name = form.get("user_name", "")

    logger.info(f"Slack command: {command} from {user_name} in {team_id}")

    cmd = command.lower().replace("/", "")

    if cmd in ("fc-link", "fc_link", "fclink"):
        linked = _link_with_code(db, text, team_id, channel_id, form.get("user_id", ""))
        if linked is None:
            return JSONResponse({
                "response_type": "ephemeral",
                "text": "That link code is invalid or expired. Generate a new one in FounderConsole and run `/fc-link <code>`.",
            })
        return JSONResponse({
            "response_type": "ephemeral",
            "text": f"Linked this Slack workspace to *{linked.name or 'your company'}*. Try `/fc-runway`.",
        })

    company = _get_company_from_slack(db, team_id, channel_id)
    if not company:
        return JSONResponse({
            "response_type": "ephemeral",
            "text": "No company linked to this Slack workspace. Generate a link code in FounderConsole, then run `/fc-link <code>`.",
        })

    company_name = company.name or "Your Company"
    metrics = _get_metrics_snapshot(db, company)

    if cmd in ("fc-runway", "fc_runway", "fcrunway"):
        return JSONResponse(_build_runway_response(metrics, company_name))

    elif cmd in ("fc-metrics", "fc_metrics", "fcmetrics"):
        return JSONResponse(_build_metrics_response(metrics, company_name))

    elif cmd in ("fc-alerts", "fc_alerts", "fcalerts"):
        return JSONResponse(_build_alerts_response(db, company, company_name))

    elif cmd in ("fc-ask", "fc_ask", "fcask"):
        if not text:
            return JSONResponse({
                "response_type": "ephemeral",
                "text": "Usage: `/fc-ask <your question>`\nExample: `/fc-ask Should we hire 3 engineers?`",
            })
        result = await _handle_ask_command(text, db, company)
        return JSONResponse(result)

    elif cmd in ("fc-simulate", "fc_simulate", "fcsimulate"):
        from server.models.simulation_run import SimulationRun
        from server.models.scenario import Scenario
        latest_run = (
            db.query(SimulationRun)
            .join(Scenario, SimulationRun.scenario_id == Scenario.id)
            .filter(Scenario.company_id == company.id)
            .order_by(SimulationRun.created_at.desc())
            .first()
        )

        if latest_run and latest_run.outputs_json:
            results = latest_run.outputs_json
            p50 = _runway_p50(results)
            survival = survival_pct(results.get("survival"), 18)
            p50_text = f"{p50:.1f} months" if p50 is not None else "not available"
            survival_text = f"{survival:.1f}%" if survival is not None else "not available"
            return JSONResponse({
                "response_type": "ephemeral",
                "blocks": [
                    {
                        "type": "header",
                        "text": {"type": "plain_text", "text": f"{company_name} — Latest Simulation"},
                    },
                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": f"*Runway P50:* {p50_text}"},
                            {"type": "mrkdwn", "text": f"*Survival (18m):* {survival_text}"},
                        ],
                    },
                ],
            })
        else:
            return JSONResponse({
                "response_type": "ephemeral",
                "text": "No completed simulations found. Run a simulation in FounderConsole first.",
            })

    return JSONResponse({
        "response_type": "ephemeral",
        "text": f"Unknown command: {command}. Available: /fc-runway, /fc-metrics, /fc-alerts, /fc-ask, /fc-simulate, /fc-link",
    })


@router.post("/events")
async def handle_slack_events(request: Request):
    """Handle Slack Events API (URL verification + events)."""
    body_bytes = await request.body()
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")

    body = await request.json()

    if body.get("type") == "url_verification":
        return JSONResponse({"challenge": body.get("challenge")})

    if not _verify_slack_signature(body_bytes, timestamp, signature):
        raise HTTPException(status_code=401, detail="Invalid Slack signature")

    event = body.get("event", {})
    event_type = event.get("type")

    logger.info(f"Slack event: {event_type}")

    return JSONResponse({"ok": True})


@router.get("/install")
async def slack_install_info():
    """Return Slack app installation info."""
    client_id = os.getenv("SLACK_CLIENT_ID", "")
    scopes = "commands,chat:write,users:read"

    return {
        "install_url": f"https://slack.com/oauth/v2/authorize?client_id={client_id}&scope={scopes}",
        "supported_commands": [
            {"command": "/fc-runway", "description": "Show current runway and cash position"},
            {"command": "/fc-metrics", "description": "Show key financial metrics snapshot"},
            {"command": "/fc-alerts", "description": "Show active smart alerts"},
            {"command": "/fc-ask", "description": "Ask the AI copilot any question"},
            {"command": "/fc-simulate", "description": "Show latest simulation results"},
            {"command": "/fc-link", "description": "Link this workspace to a FounderConsole company"},
        ],
        "setup_instructions": [
            "1. Create a Slack App at api.slack.com/apps",
            "2. Add slash commands (/fc-runway, /fc-metrics, /fc-alerts, /fc-ask, /fc-simulate)",
            "3. Set the Request URL to your FounderConsole domain + /api/slack/commands",
            "4. Set SLACK_SIGNING_SECRET and SLACK_CLIENT_ID environment variables",
            "5. Install the app to your workspace",
            "6. In FounderConsole, generate a Slack link code and run /fc-link <code> in Slack",
        ],
    }


# ---------------------------------------------------------------------------
# Linking, from the FounderConsole side (authenticated).
# ---------------------------------------------------------------------------
link_router = APIRouter(tags=["slack"])


def _require_slack_manager(db: Session, company_id: int, user: User) -> Company:
    """Slack linking decides who can read this company from an external workspace.

    A link outlives the request that made it, so it needs more than ordinary
    read access: only an owner or admin may issue, inspect or revoke it. A
    viewer keeps the access they already had and gains no way to create one.
    """
    company = get_user_company(db, company_id, user)
    if get_user_company_role(db, company_id, user) not in ("owner", "admin"):
        raise HTTPException(
            status_code=403,
            detail="Requires owner or admin role to manage the Slack link",
        )
    return company


@link_router.post("/companies/{company_id}/integrations/slack/link-code")
def create_slack_link_code(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Issue a one-time code; running `/fc-link <code>` in Slack links the workspace."""
    company = _require_slack_manager(db, company_id, current_user)
    code = "".join(secrets.choice(_LINK_CODE_ALPHABET) for _ in range(10))
    expires_at = time.time() + LINK_CODE_TTL_SECONDS
    save_metadata_value(db, company, LINK_CODE_META_KEY, {
        "code_hash": _hash_link_code(code),
        "expires_at": expires_at,
        "created_by": current_user.id,
    })
    return {
        "code": code,
        "expires_in_seconds": LINK_CODE_TTL_SECONDS,
        "instructions": f"In the Slack channel to link, run: /fc-link {code}",
    }


@link_router.get("/companies/{company_id}/integrations/slack")
def get_slack_link_status(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company = _require_slack_manager(db, company_id, current_user)
    link = (company.metadata_json or {}).get(SLACK_META_KEY) or {}
    return {
        "linked": bool(link.get("team_id")),
        "team_id": link.get("team_id"),
        "channel_id": link.get("channel_id"),
        "linked_at": link.get("linked_at"),
    }


@link_router.delete("/companies/{company_id}/integrations/slack")
def unlink_slack(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company = _require_slack_manager(db, company_id, current_user)
    delete_metadata_value(db, company, SLACK_META_KEY)
    delete_metadata_value(db, company, LINK_CODE_META_KEY)
    return {"linked": False}
