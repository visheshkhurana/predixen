from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from server.core.db import get_db
from server.core.security import get_current_user
from server.models.user import User
from server.models.company import Company
from server.models.workspace import NotificationPreference
from server.models.financial import FinancialRecord

router = APIRouter(tags=["digest"])


class DigestPreferenceUpdate(BaseModel):
    monthly_digest: bool


@router.get("/companies/{company_id}/digest/preferences")
def get_digest_preferences(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    pref = db.query(NotificationPreference).filter(
        NotificationPreference.user_id == current_user.id,
    ).first()

    return {
        "monthly_digest": pref.monthly_digest if pref and pref.monthly_digest is not None else True,
    }


@router.put("/companies/{company_id}/digest/preferences")
def update_digest_preferences(
    company_id: int,
    data: DigestPreferenceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    pref = db.query(NotificationPreference).filter(
        NotificationPreference.user_id == current_user.id,
    ).first()

    if pref:
        pref.monthly_digest = data.monthly_digest
        pref.updated_at = datetime.utcnow()
    else:
        pref = NotificationPreference(
            user_id=current_user.id,
            monthly_digest=data.monthly_digest,
        )
        db.add(pref)

    db.commit()
    return {"monthly_digest": data.monthly_digest}


@router.post("/companies/{company_id}/digest/send")
def send_monthly_digest(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    user = db.query(User).filter(User.id == current_user.id).first()
    email = user.username if user else None
    if not email:
        raise HTTPException(status_code=400, detail="No email found for user")

    latest = db.query(FinancialRecord).filter(
        FinancialRecord.company_id == company_id
    ).order_by(FinancialRecord.period_end.desc()).first()

    mrr = latest.mrr if latest and latest.mrr else 0
    cash = latest.cash_balance if latest and latest.cash_balance else 0
    burn = latest.net_burn if latest and latest.net_burn else 0
    runway = latest.runway_months if latest and latest.runway_months else 0
    revenue = latest.revenue if latest else 0

    risks = []
    if runway and runway < 6:
        risks.append(f"Runway critically low at {runway:.1f} months")
    if burn and burn > revenue * 1.5:
        risks.append("Burn rate exceeds 1.5x revenue")
    if mrr and latest and latest.mom_growth and latest.mom_growth < 0:
        risks.append(f"MRR declining: {latest.mom_growth:.1f}% MoM")
    if not risks:
        risks.append("No critical risks detected")

    html = _build_digest_html(
        company_name=company.name,
        mrr=mrr,
        cash=cash,
        burn=burn,
        runway=runway,
        risks=risks,
    )

    try:
        from server.email.service import _send_email_sync
        result = _send_email_sync(
            sender="FounderConsole Digest <digest@founderconsole.ai>",
            to=email,
            subject=f"Monthly Digest — {company.name} | {datetime.utcnow().strftime('%b %Y')}",
            html=html,
        )
        return {
            "sent": True,
            "to": email,
            "metrics": {
                "mrr": mrr,
                "cash": cash,
                "burn": burn,
                "runway": runway,
                "risks": risks,
            }
        }
    except Exception as e:
        return {
            "sent": False,
            "error": str(e),
            "metrics": {
                "mrr": mrr,
                "cash": cash,
                "burn": burn,
                "runway": runway,
                "risks": risks,
            }
        }


def _fmt(val):
    if val >= 1_000_000:
        return f"${val/1_000_000:.1f}M"
    if val >= 1_000:
        return f"${val/1_000:.0f}K"
    return f"${val:.0f}"


def _build_digest_html(company_name, mrr, cash, burn, runway, risks):
    risk_items = "".join(
        f'<tr><td style="padding:6px 12px;color:#f59e0b;font-size:14px;">&#9888; {r}</td></tr>'
        for r in risks
    )
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#0f172a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;padding:40px 20px;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background:#1e293b;border-radius:12px;overflow:hidden;">
  <tr><td style="background:linear-gradient(135deg,#0ea5e9,#6366f1);padding:32px 40px;">
    <h1 style="margin:0;color:#fff;font-size:24px;">FounderConsole Monthly Digest</h1>
    <p style="margin:8px 0 0;color:rgba(255,255,255,0.8);font-size:14px;">{company_name} &mdash; {datetime.utcnow().strftime('%B %Y')}</p>
  </td></tr>
  <tr><td style="padding:32px 40px;">
    <h2 style="margin:0 0 20px;color:#f8fafc;font-size:18px;">Key Metrics</h2>
    <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;border-radius:8px;">
      <tr>
        <td style="padding:16px;text-align:center;width:25%;border-right:1px solid #334155;">
          <p style="margin:0;color:#94a3b8;font-size:11px;text-transform:uppercase;">MRR</p>
          <p style="margin:4px 0 0;color:#22c55e;font-size:20px;font-weight:700;">{_fmt(mrr)}</p>
        </td>
        <td style="padding:16px;text-align:center;width:25%;border-right:1px solid #334155;">
          <p style="margin:0;color:#94a3b8;font-size:11px;text-transform:uppercase;">Cash</p>
          <p style="margin:4px 0 0;color:#0ea5e9;font-size:20px;font-weight:700;">{_fmt(cash)}</p>
        </td>
        <td style="padding:16px;text-align:center;width:25%;border-right:1px solid #334155;">
          <p style="margin:0;color:#94a3b8;font-size:11px;text-transform:uppercase;">Burn</p>
          <p style="margin:4px 0 0;color:#f59e0b;font-size:20px;font-weight:700;">{_fmt(abs(burn))}</p>
        </td>
        <td style="padding:16px;text-align:center;width:25%;">
          <p style="margin:0;color:#94a3b8;font-size:11px;text-transform:uppercase;">Runway</p>
          <p style="margin:4px 0 0;color:{'#ef4444' if runway < 6 else '#22c55e'};font-size:20px;font-weight:700;">{runway:.1f}mo</p>
        </td>
      </tr>
    </table>
    <h2 style="margin:24px 0 12px;color:#f8fafc;font-size:18px;">Top Risks</h2>
    <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;border-radius:8px;">
      {risk_items}
    </table>
    <div style="margin-top:32px;text-align:center;">
      <a href="https://founderconsole.ai" style="display:inline-block;padding:12px 32px;background:#0ea5e9;color:#fff;text-decoration:none;border-radius:6px;font-weight:600;font-size:14px;">View Full Dashboard</a>
    </div>
  </td></tr>
  <tr><td style="padding:20px 40px;border-top:1px solid #334155;">
    <p style="margin:0;color:#64748b;font-size:12px;text-align:center;">FounderConsole &mdash; AI-powered financial simulation for startups</p>
  </td></tr>
</table>
</td></tr>
</table>
</body>
</html>"""
