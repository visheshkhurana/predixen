"""
Smart Alerts API - Enhanced alert evaluation, CRUD, rules management, and weekly briefing.
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from server.core.db import get_db
from server.core.security import get_current_user
from server.core.company_access import get_user_company
from server.models.user import User
from server.models.company import Company
from server.models.truth_scan import TruthScan
from server.models.financial import FinancialRecord
from server.api.simulations import extract_metric_value

logger = logging.getLogger(__name__)

router = APIRouter(tags=["smart-alerts"])


class AlertRuleCreate(BaseModel):
    name: str
    alert_type: str
    metric: str
    threshold: float
    severity: str = "warning"
    enabled: bool = True
    notification_channels: List[str] = ["in_app"]


class AlertRuleUpdate(BaseModel):
    name: Optional[str] = None
    threshold: Optional[float] = None
    severity: Optional[str] = None
    enabled: Optional[bool] = None
    notification_channels: Optional[List[str]] = None


def _get_metadata(company: Company) -> dict:
    return company.metadata_json or {}


def _save_metadata(db: Session, company: Company, metadata: dict):
    company.metadata_json = metadata
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(company, "metadata_json")
    db.commit()


def _evaluate_alerts(company: Company, db: Session) -> List[Dict[str, Any]]:
    truth_scan = db.query(TruthScan).filter(
        TruthScan.company_id == company.id
    ).order_by(TruthScan.created_at.desc()).first()

    records = (
        db.query(FinancialRecord)
        .filter(FinancialRecord.company_id == company.id)
        .order_by(FinancialRecord.period_start.desc())
        .limit(12)
        .all()
    )

    new_alerts = []
    now = datetime.now(timezone.utc).isoformat()

    metrics = {}
    if truth_scan and truth_scan.outputs_json:
        metrics = truth_scan.outputs_json.get("metrics", {})

    latest = records[0] if records else None
    previous = records[1] if len(records) > 1 else None

    if latest and previous:
        curr_burn = (
            float(latest.opex or 0) + float(latest.payroll or 0) +
            float(latest.cogs or 0) + float(latest.other_costs or 0)
        )
        prev_burn = (
            float(previous.opex or 0) + float(previous.payroll or 0) +
            float(previous.cogs or 0) + float(previous.other_costs or 0)
        )
        if prev_burn > 0:
            burn_change = (curr_burn - prev_burn) / prev_burn * 100
            if burn_change > 15:
                new_alerts.append({
                    "id": str(uuid.uuid4()),
                    "type": "burn_spike",
                    "severity": "critical",
                    "title": "Burn Rate Spike Detected",
                    "message": f"Monthly burn increased by {burn_change:.1f}% from ${prev_burn:,.0f} to ${curr_burn:,.0f}.",
                    "metric": "burn_rate",
                    "currentValue": curr_burn,
                    "previousValue": prev_burn,
                    "changePercent": round(burn_change, 1),
                    "timestamp": now,
                    "acknowledged": False,
                    "suggestedAction": "Review recent expense increases. Consider cost optimization in non-critical areas."
                })

        curr_revenue = float(latest.revenue or 0)
        prev_revenue = float(previous.revenue or 0)
        if prev_revenue > 0:
            mrr_change = (curr_revenue - prev_revenue) / prev_revenue * 100
            if mrr_change < -5:
                new_alerts.append({
                    "id": str(uuid.uuid4()),
                    "type": "mrr_drop",
                    "severity": "critical",
                    "title": "MRR Drop Detected",
                    "message": f"Monthly revenue dropped by {abs(mrr_change):.1f}% from ${prev_revenue:,.0f} to ${curr_revenue:,.0f}.",
                    "metric": "mrr",
                    "currentValue": curr_revenue,
                    "previousValue": prev_revenue,
                    "changePercent": round(mrr_change, 1),
                    "timestamp": now,
                    "acknowledged": False,
                    "suggestedAction": "Investigate churn causes and review customer retention strategies."
                })

        curr_growth = float(latest.mom_growth or 0) if latest.mom_growth else 0
        prev_growth = float(previous.mom_growth or 0) if previous.mom_growth else 0
        if prev_growth > 0 and curr_growth > 0:
            growth_change = (curr_growth - prev_growth) / prev_growth * 100
            if growth_change < -30:
                new_alerts.append({
                    "id": str(uuid.uuid4()),
                    "type": "growth_slowdown",
                    "severity": "warning",
                    "title": "Growth Slowdown",
                    "message": f"Growth rate declined by {abs(growth_change):.1f}% from {prev_growth:.1f}% to {curr_growth:.1f}%.",
                    "metric": "growth_rate",
                    "currentValue": curr_growth,
                    "previousValue": prev_growth,
                    "changePercent": round(growth_change, 1),
                    "timestamp": now,
                    "acknowledged": False,
                    "suggestedAction": "Review acquisition channels and consider new growth strategies."
                })

    if latest:
        cash = float(latest.cash_balance or 0)
        total_costs = (
            float(latest.opex or 0) + float(latest.payroll or 0) +
            float(latest.cogs or 0) + float(latest.other_costs or 0)
        )
        net_burn = total_costs - float(latest.revenue or 0)
        if net_burn > 0 and cash > 0:
            runway = cash / net_burn
            if runway < 12:
                new_alerts.append({
                    "id": str(uuid.uuid4()),
                    "type": "runway_warning",
                    "severity": "critical",
                    "title": "Critical Runway Warning",
                    "message": f"Runway is {runway:.1f} months — below 12-month safety threshold. Cash: ${cash:,.0f}, Net burn: ${net_burn:,.0f}/mo.",
                    "metric": "runway_months",
                    "currentValue": round(runway, 1),
                    "previousValue": None,
                    "changePercent": None,
                    "timestamp": now,
                    "acknowledged": False,
                    "suggestedAction": "Initiate fundraising preparation or implement immediate cost reduction measures."
                })
            elif runway < 18:
                new_alerts.append({
                    "id": str(uuid.uuid4()),
                    "type": "runway_caution",
                    "severity": "warning",
                    "title": "Runway Caution",
                    "message": f"Runway is {runway:.1f} months — approaching the 18-month planning threshold.",
                    "metric": "runway_months",
                    "currentValue": round(runway, 1),
                    "previousValue": None,
                    "changePercent": None,
                    "timestamp": now,
                    "acknowledged": False,
                    "suggestedAction": "Begin fundraising planning. Explore scenarios to extend runway."
                })

    ts_churn = extract_metric_value(metrics.get("churn_rate"), 0)
    ts_prev_churn = extract_metric_value(metrics.get("prev_churn_rate"), 0)
    if ts_prev_churn > 0 and ts_churn > 0:
        churn_change = (ts_churn - ts_prev_churn) / ts_prev_churn * 100
        if churn_change > 50:
            new_alerts.append({
                "id": str(uuid.uuid4()),
                "type": "churn_spike",
                "severity": "warning",
                "title": "Churn Spike Detected",
                "message": f"Churn rate increased by {churn_change:.1f}% from {ts_prev_churn:.2f}% to {ts_churn:.2f}%.",
                "metric": "churn_rate",
                "currentValue": ts_churn,
                "previousValue": ts_prev_churn,
                "changePercent": round(churn_change, 1),
                "timestamp": now,
                "acknowledged": False,
                "suggestedAction": "Investigate customer satisfaction. Deploy retention campaigns and review product quality."
            })

    return new_alerts


@router.post("/companies/{company_id}/smart-alerts/evaluate")
def evaluate_alerts(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company = get_user_company(db, company_id, current_user)
    new_alerts = _evaluate_alerts(company, db)

    metadata = _get_metadata(company)
    existing_alerts = metadata.get("smart_alerts", [])
    existing_alerts = new_alerts + existing_alerts
    metadata["smart_alerts"] = existing_alerts
    _save_metadata(db, company, metadata)

    return {
        "new_alerts": len(new_alerts),
        "total_alerts": len(existing_alerts),
        "alerts": new_alerts,
    }


@router.get("/companies/{company_id}/smart-alerts")
def list_alerts(
    company_id: int,
    severity: Optional[str] = Query(None, description="Filter by severity"),
    acknowledged: Optional[bool] = Query(None, description="Filter by acknowledged status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company = get_user_company(db, company_id, current_user)
    metadata = _get_metadata(company)
    alerts = metadata.get("smart_alerts", [])

    if severity:
        alerts = [a for a in alerts if a.get("severity") == severity]
    if acknowledged is not None:
        alerts = [a for a in alerts if a.get("acknowledged") == acknowledged]

    alerts.sort(key=lambda a: a.get("timestamp", ""), reverse=True)

    unacknowledged = sum(1 for a in metadata.get("smart_alerts", []) if not a.get("acknowledged"))

    return {
        "alerts": alerts,
        "total": len(alerts),
        "unacknowledged_count": unacknowledged,
    }


@router.put("/companies/{company_id}/smart-alerts/{alert_id}/acknowledge")
def acknowledge_alert(
    company_id: int,
    alert_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company = get_user_company(db, company_id, current_user)
    metadata = _get_metadata(company)
    alerts = metadata.get("smart_alerts", [])

    found = False
    for alert in alerts:
        if alert.get("id") == alert_id:
            alert["acknowledged"] = True
            alert["acknowledged_at"] = datetime.now(timezone.utc).isoformat()
            found = True
            break

    if not found:
        raise HTTPException(status_code=404, detail="Alert not found")

    metadata["smart_alerts"] = alerts
    _save_metadata(db, company, metadata)

    return {"status": "acknowledged", "alert_id": alert_id}


@router.delete("/companies/{company_id}/smart-alerts/{alert_id}")
def delete_alert(
    company_id: int,
    alert_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company = get_user_company(db, company_id, current_user)
    metadata = _get_metadata(company)
    alerts = metadata.get("smart_alerts", [])

    original_len = len(alerts)
    alerts = [a for a in alerts if a.get("id") != alert_id]

    if len(alerts) == original_len:
        raise HTTPException(status_code=404, detail="Alert not found")

    metadata["smart_alerts"] = alerts
    _save_metadata(db, company, metadata)

    return {"status": "deleted", "alert_id": alert_id}


@router.get("/companies/{company_id}/smart-alerts/rules")
def list_rules(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company = get_user_company(db, company_id, current_user)
    metadata = _get_metadata(company)
    rules = metadata.get("alert_rules", _default_rules())

    return {"rules": rules}


@router.post("/companies/{company_id}/smart-alerts/rules")
def create_rule(
    company_id: int,
    rule: AlertRuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company = get_user_company(db, company_id, current_user)
    metadata = _get_metadata(company)
    rules = metadata.get("alert_rules", _default_rules())

    new_rule = {
        "id": str(uuid.uuid4()),
        "name": rule.name,
        "alert_type": rule.alert_type,
        "metric": rule.metric,
        "threshold": rule.threshold,
        "severity": rule.severity,
        "enabled": rule.enabled,
        "notification_channels": rule.notification_channels,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    rules.append(new_rule)
    metadata["alert_rules"] = rules
    _save_metadata(db, company, metadata)

    return {"rule": new_rule}


@router.put("/companies/{company_id}/smart-alerts/rules/{rule_id}")
def update_rule(
    company_id: int,
    rule_id: str,
    update: AlertRuleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company = get_user_company(db, company_id, current_user)
    metadata = _get_metadata(company)
    rules = metadata.get("alert_rules", _default_rules())

    found = False
    for r in rules:
        if r.get("id") == rule_id:
            if update.name is not None:
                r["name"] = update.name
            if update.threshold is not None:
                r["threshold"] = update.threshold
            if update.severity is not None:
                r["severity"] = update.severity
            if update.enabled is not None:
                r["enabled"] = update.enabled
            if update.notification_channels is not None:
                r["notification_channels"] = update.notification_channels
            r["updated_at"] = datetime.now(timezone.utc).isoformat()
            found = True
            break

    if not found:
        raise HTTPException(status_code=404, detail="Rule not found")

    metadata["alert_rules"] = rules
    _save_metadata(db, company, metadata)

    return {"rule": next(r for r in rules if r.get("id") == rule_id)}


@router.delete("/companies/{company_id}/smart-alerts/rules/{rule_id}")
def delete_rule(
    company_id: int,
    rule_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company = get_user_company(db, company_id, current_user)
    metadata = _get_metadata(company)
    rules = metadata.get("alert_rules", [])

    original_len = len(rules)
    rules = [r for r in rules if r.get("id") != rule_id]

    if len(rules) == original_len:
        raise HTTPException(status_code=404, detail="Rule not found")

    metadata["alert_rules"] = rules
    _save_metadata(db, company, metadata)

    return {"status": "deleted", "rule_id": rule_id}


@router.post("/companies/{company_id}/smart-alerts/weekly-briefing")
async def send_weekly_briefing(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company = get_user_company(db, company_id, current_user)
    metadata = _get_metadata(company)
    alerts = metadata.get("smart_alerts", [])

    records = (
        db.query(FinancialRecord)
        .filter(FinancialRecord.company_id == company.id)
        .order_by(FinancialRecord.period_start.desc())
        .limit(2)
        .all()
    )

    latest = records[0] if records else None
    key_metrics = {}
    if latest:
        revenue = float(latest.revenue or 0)
        total_costs = (
            float(latest.opex or 0) + float(latest.payroll or 0) +
            float(latest.cogs or 0) + float(latest.other_costs or 0)
        )
        net_burn = total_costs - revenue
        cash = float(latest.cash_balance or 0)
        runway = cash / net_burn if net_burn > 0 else None

        key_metrics = {
            "mrr": revenue,
            "burn_rate": total_costs,
            "net_burn": net_burn,
            "cash_balance": cash,
            "runway_months": round(runway, 1) if runway else None,
        }

    unacknowledged = [a for a in alerts if not a.get("acknowledged")]
    critical_count = sum(1 for a in unacknowledged if a.get("severity") == "critical")
    warning_count = sum(1 for a in unacknowledged if a.get("severity") == "warning")

    narrative = ""
    try:
        from server.lib.llm.llm_router import get_llm_router, TaskType
        llm = get_llm_router(db_session=db, company_id=company.id, user_id=current_user.id)
        prompt = (
            f"Write a concise weekly financial briefing for {company.name}. "
            f"Key metrics: {key_metrics}. "
            f"Active alerts: {critical_count} critical, {warning_count} warnings. "
            f"Alert details: {[a.get('title', '') + ': ' + a.get('message', '') for a in unacknowledged[:5]]}. "
            f"Keep it under 200 words, professional tone, actionable insights."
        )
        result = llm.chat(
            messages=[{"role": "user", "content": prompt}],
            task_type=TaskType.FINANCIAL_ANALYSIS,
            temperature=0.5,
            max_tokens=500,
        )
        narrative = result.get("content", "")
    except Exception as e:
        logger.warning(f"LLM briefing generation failed: {e}")
        narrative = (
            f"Weekly Briefing for {company.name}\n\n"
            f"Key Metrics:\n"
        )
        for k, v in key_metrics.items():
            narrative += f"- {k}: {v}\n"
        narrative += f"\nActive Alerts: {critical_count} critical, {warning_count} warnings.\n"
        for a in unacknowledged[:5]:
            narrative += f"- {a.get('title', 'Alert')}: {a.get('message', '')}\n"

    email_sent = False
    try:
        from server.email.service import send_email
        user_email = current_user.email
        subject = f"Weekly Briefing — {company.name}"
        html_content = f"""
        <html>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #1a1a2e;">Weekly Financial Briefing</h2>
            <h3 style="color: #16213e;">{company.name}</h3>
            <div style="background: #f8f9fa; padding: 16px; border-radius: 8px; margin: 16px 0;">
                <h4 style="margin-top:0;">Key Metrics</h4>
                {''.join(f'<p style="margin:4px 0;"><strong>{k}:</strong> {v}</p>' for k, v in key_metrics.items() if v is not None)}
            </div>
            <div style="background: #fff3cd; padding: 16px; border-radius: 8px; margin: 16px 0;">
                <h4 style="margin-top:0;">Active Alerts</h4>
                <p>{critical_count} critical, {warning_count} warnings</p>
                {''.join(f'<p style="margin:4px 0;">&#8226; <strong>{a.get("title", "Alert")}:</strong> {a.get("message", "")}</p>' for a in unacknowledged[:5])}
            </div>
            <div style="padding: 16px 0;">
                <h4>AI Analysis</h4>
                <p>{narrative.replace(chr(10), '<br>')}</p>
            </div>
            <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 20px 0;">
            <p style="color: #666; font-size: 12px;">Sent by FounderConsole</p>
        </body>
        </html>
        """
        email_result = await send_email(user_email, subject, html_content)
        email_sent = bool(email_result)
    except Exception as e:
        logger.warning(f"Weekly briefing email failed: {e}")

    return {
        "status": "sent" if email_sent else "generated",
        "narrative": narrative,
        "metrics": key_metrics,
        "alert_summary": {
            "critical": critical_count,
            "warning": warning_count,
            "total_unacknowledged": len(unacknowledged),
        },
        "email_sent": email_sent,
    }


def _default_rules() -> List[Dict[str, Any]]:
    return [
        {
            "id": "default-burn-spike",
            "name": "Burn Spike",
            "alert_type": "burn_spike",
            "metric": "burn_rate",
            "threshold": 15,
            "severity": "critical",
            "enabled": True,
            "notification_channels": ["in_app"],
        },
        {
            "id": "default-mrr-drop",
            "name": "MRR Drop",
            "alert_type": "mrr_drop",
            "metric": "mrr",
            "threshold": 5,
            "severity": "critical",
            "enabled": True,
            "notification_channels": ["in_app"],
        },
        {
            "id": "default-churn-spike",
            "name": "Churn Spike",
            "alert_type": "churn_spike",
            "metric": "churn_rate",
            "threshold": 50,
            "severity": "warning",
            "enabled": True,
            "notification_channels": ["in_app"],
        },
        {
            "id": "default-runway-warning",
            "name": "Runway Warning",
            "alert_type": "runway_warning",
            "metric": "runway_months",
            "threshold": 12,
            "severity": "critical",
            "enabled": True,
            "notification_channels": ["in_app"],
        },
        {
            "id": "default-runway-caution",
            "name": "Runway Caution",
            "alert_type": "runway_caution",
            "metric": "runway_months",
            "threshold": 18,
            "severity": "warning",
            "enabled": True,
            "notification_channels": ["in_app"],
        },
        {
            "id": "default-growth-slowdown",
            "name": "Growth Slowdown",
            "alert_type": "growth_slowdown",
            "metric": "growth_rate",
            "threshold": 30,
            "severity": "warning",
            "enabled": True,
            "notification_channels": ["in_app"],
        },
    ]
