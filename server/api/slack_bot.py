"""
Slack Copilot Integration — slash commands and event handlers
for FounderConsole within Slack workspaces.

Commands:
  /fc-runway      — Show current runway and cash position
  /fc-metrics     — Show key financial metrics snapshot
  /fc-alerts      — Show active smart alerts
  /fc-ask <query> — Ask the AI copilot any question
  /fc-simulate    — Get simulation summary
"""
import os
import hmac
import hashlib
import time
import logging
from typing import Dict, Any, Optional

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from server.core.db import get_db
from server.models.company import Company
from server.models.truth_scan import TruthScan
from server.models.financial import FinancialRecord

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/slack", tags=["slack"])


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


def _get_company_from_slack(
    db: Session, team_id: str, channel_id: str
) -> Optional[Company]:
    """Look up the company associated with this Slack workspace."""
    if not team_id and not channel_id:
        return None

    companies = db.query(Company).limit(100).all()
    for company in companies:
        meta = company.metadata_json or {}
        slack_config = meta.get("slack_integration", {})
        if team_id and slack_config.get("team_id") == team_id:
            return company
        if channel_id and slack_config.get("channel_id") == channel_id:
            return company

    return None


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

    logger.info(f"Slack command: {command} '{text}' from {user_name} in {team_id}")

    company = _get_company_from_slack(db, team_id, channel_id)
    if not company:
        return JSONResponse({
            "response_type": "ephemeral",
            "text": "No company linked to this Slack workspace. Set up the integration in FounderConsole Settings.",
        })

    company_name = company.name or "Your Company"
    metrics = _get_metrics_snapshot(db, company)

    cmd = command.lower().replace("/", "")

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
            p50 = results.get("runway_p50", results.get("median_runway", 0))
            survival = results.get("survival_probability", results.get("survival_rate", 0))
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
                            {"type": "mrkdwn", "text": f"*Runway P50:* {p50:.1f} months"},
                            {"type": "mrkdwn", "text": f"*Survival (18m):* {survival:.1f}%"},
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
        "text": f"Unknown command: {command}. Available: /fc-runway, /fc-metrics, /fc-alerts, /fc-ask, /fc-simulate",
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
        ],
        "setup_instructions": [
            "1. Create a Slack App at api.slack.com/apps",
            "2. Add slash commands (/fc-runway, /fc-metrics, /fc-alerts, /fc-ask, /fc-simulate)",
            "3. Set the Request URL to your FounderConsole domain + /api/slack/commands",
            "4. Set SLACK_SIGNING_SECRET and SLACK_CLIENT_ID environment variables",
            "5. Install the app to your workspace",
        ],
    }
