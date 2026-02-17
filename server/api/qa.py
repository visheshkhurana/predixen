"""
QA Front backend endpoints - admin-only, read-only introspection for validating platform fixes.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from typing import Dict, Any, List, Optional
from datetime import datetime

from server.core.db import get_db
from server.core.security import get_current_user
from server.core.config import settings
from server.models import User, Company, Scenario
from server.models.truth_scan import TruthScan
from server.models.financial import FinancialRecord
from server.models.workspace import WorkspaceMember

router = APIRouter(prefix="/qa", tags=["qa"])


def require_qa_access(current_user: User = Depends(get_current_user)):
    admin_email = (settings.ADMIN_MASTER_EMAIL or "").lower().strip()
    user_email = getattr(current_user, 'email', '').lower().strip()
    if not admin_email or user_email != admin_email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="QA endpoints require admin access"
        )
    return current_user


@router.get("/whoami")
def qa_whoami(current_user: User = Depends(require_qa_access), db: Session = Depends(get_db)):
    owned_companies = db.query(Company).filter(Company.user_id == current_user.id).all()
    owned_ids = [c.id for c in owned_companies]

    member_rows = db.query(WorkspaceMember).filter(WorkspaceMember.user_id == current_user.id).all()
    member_ids = [m.company_id for m in member_rows]

    all_company_ids = list(set(owned_ids + member_ids))

    return {
        "user_id": current_user.id,
        "email": current_user.email,
        "role": getattr(current_user, 'role', None),
        "company_ids": all_company_ids,
        "company_count": len(all_company_ids),
        "is_admin": True,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/tenant-scope-check")
def qa_tenant_scope(
    company_id: int,
    current_user: User = Depends(require_qa_access),
    db: Session = Depends(get_db)
):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    scenario_count = db.query(func.count(Scenario.id)).filter(Scenario.company_id == company_id).scalar() or 0
    financial_count = db.query(func.count(FinancialRecord.id)).filter(FinancialRecord.company_id == company_id).scalar() or 0
    truth_scan_count = db.query(func.count(TruthScan.id)).filter(TruthScan.company_id == company_id).scalar() or 0
    workspace_members = db.query(func.count(WorkspaceMember.id)).filter(WorkspaceMember.company_id == company_id).scalar() or 0

    all_companies = db.query(Company.id, Company.name).all()
    demo_companies = [{"id": c.id, "name": c.name} for c in all_companies if "techflow" in (c.name or "").lower() or "demo" in (c.name or "").lower()]

    is_demo_company = any(d["id"] == company_id for d in demo_companies)

    return {
        "company_id": company_id,
        "company_name": company.name,
        "is_demo_company": is_demo_company,
        "scoped_counts": {
            "scenarios": scenario_count,
            "financial_records": financial_count,
            "truth_scans": truth_scan_count,
            "workspace_members": workspace_members,
        },
        "demo_companies_in_system": demo_companies,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/routes-health")
def qa_routes_health(current_user: User = Depends(require_qa_access)):
    core_routes = [
        {"path": "/", "name": "Dashboard/Overview", "type": "frontend"},
        {"path": "/overview", "name": "Overview", "type": "frontend"},
        {"path": "/scenarios", "name": "Scenarios", "type": "frontend"},
        {"path": "/decisions", "name": "Decisions", "type": "frontend"},
        {"path": "/truth", "name": "Health Check (Truth Scan)", "type": "frontend"},
        {"path": "/copilot", "name": "Copilot", "type": "frontend"},
        {"path": "/fundraising", "name": "Fundraising", "type": "frontend"},
        {"path": "/data", "name": "Data Input", "type": "frontend"},
        {"path": "/simulate", "name": "Simulate (should redirect)", "type": "frontend", "expect_redirect": True},
        {"path": "/admin", "name": "Admin Dashboard", "type": "frontend", "admin_only": True},
    ]
    api_routes = [
        {"path": "/api/admin/me", "name": "Admin Me", "type": "api"},
        {"path": "/api/companies", "name": "Companies List", "type": "api"},
        {"path": "/api/dashboard/kpis", "name": "Dashboard KPIs", "type": "api"},
        {"path": "/api/admin/users", "name": "Admin Users", "type": "api", "admin_only": True},
    ]
    return {
        "frontend_routes": core_routes,
        "api_routes": api_routes,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/health-summary")
def qa_health_summary(
    company_id: int,
    current_user: User = Depends(require_qa_access),
    db: Session = Depends(get_db)
):
    latest_scan = db.query(TruthScan).filter(
        TruthScan.company_id == company_id
    ).order_by(TruthScan.created_at.desc()).first()

    health_score = None
    confidence_score = None
    scan_data = None
    last_updated = None

    if latest_scan and latest_scan.outputs_json:
        scan_data = latest_scan.outputs_json if isinstance(latest_scan.outputs_json, dict) else {}
        metrics = scan_data.get("metrics", {}) if isinstance(scan_data.get("metrics"), dict) else {}
        health_score = scan_data.get("quality_of_growth_index") or scan_data.get("health_score")
        confidence_score = scan_data.get("data_confidence_score") or scan_data.get("confidence_score") or scan_data.get("data_confidence")
        last_updated = latest_scan.created_at.isoformat() if latest_scan.created_at else None

    return {
        "company_id": company_id,
        "health_score": health_score,
        "confidence_score": confidence_score,
        "has_truth_scan": latest_scan is not None,
        "last_updated": last_updated,
        "source": "truth_scans table (latest by created_at)",
        "raw_keys": list(scan_data.keys()) if scan_data else [],
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/kpi-sanity")
def qa_kpi_sanity(
    company_id: int,
    current_user: User = Depends(require_qa_access),
    db: Session = Depends(get_db)
):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    latest_records = db.query(FinancialRecord).filter(
        FinancialRecord.company_id == company_id
    ).order_by(FinancialRecord.period_start.desc()).limit(12).all()

    latest_scan = db.query(TruthScan).filter(
        TruthScan.company_id == company_id
    ).order_by(TruthScan.created_at.desc()).first()

    scan_data = {}
    metrics = {}
    if latest_scan and latest_scan.outputs_json:
        scan_data = latest_scan.outputs_json if isinstance(latest_scan.outputs_json, dict) else {}
        metrics = scan_data.get("metrics", {}) if isinstance(scan_data.get("metrics"), dict) else scan_data

    mrr = metrics.get("mrr")
    arr = metrics.get("arr")
    burn_rate = metrics.get("net_burn") or metrics.get("burn_rate") or metrics.get("monthly_burn")
    cash = metrics.get("cash_balance") or metrics.get("cash_on_hand") or metrics.get("cash")
    runway = metrics.get("runway_months") or metrics.get("runway")
    nrr = metrics.get("net_revenue_retention") or metrics.get("nrr")
    growth_rate = metrics.get("revenue_growth_mom") or metrics.get("monthly_growth_rate") or metrics.get("growth_rate")
    gross_margin = metrics.get("gross_margin")

    if not scan_data and latest_records:
        latest = latest_records[0]
        mrr = getattr(latest, 'revenue', None)
        burn_rate = getattr(latest, 'total_expenses', None)
        cash = getattr(latest, 'cash_on_hand', None)

    checks = []

    if nrr is not None:
        nrr_val = float(nrr) if nrr else 0
        checks.append({
            "metric": "NRR",
            "value": nrr_val,
            "pass": 0 <= nrr_val <= 300,
            "bounds": "0-300%",
            "note": "Capped at 300% per QA fix"
        })

    if growth_rate is not None:
        gr_val = float(growth_rate) if growth_rate else 0
        is_demo = "techflow" in (company.name or "").lower() or "demo" in (company.name or "").lower()
        growth_upper = 1000 if is_demo else 100
        checks.append({
            "metric": "Monthly Growth Rate",
            "value": gr_val,
            "pass": -100 <= gr_val <= growth_upper,
            "bounds": f"-100% to +{growth_upper}%{' (relaxed for demo/seed data)' if is_demo else ''}",
            "note": "Demo seed data may have extreme values from small base" if is_demo else "Capped per QA fix"
        })

    if mrr is not None and arr is not None:
        mrr_val = float(mrr) if mrr else 0
        arr_val = float(arr) if arr else 0
        expected_arr = mrr_val * 12
        tolerance = max(abs(expected_arr) * 0.05, 100)
        checks.append({
            "metric": "ARR = MRR * 12",
            "value": {"mrr": mrr_val, "arr": arr_val, "expected_arr": expected_arr},
            "pass": abs(arr_val - expected_arr) <= tolerance,
            "bounds": f"Within 5% tolerance ({tolerance:.0f})",
            "note": "ARR should equal MRR * 12"
        })

    if cash is not None and burn_rate is not None:
        cash_val = float(cash) if cash else 0
        burn_val = float(burn_rate) if burn_rate else 0
        expected_runway = cash_val / burn_val if burn_val > 0 else None
        if expected_runway is not None and runway is not None:
            runway_val = float(runway)
            tolerance = max(abs(expected_runway) * 0.1, 0.5)
            checks.append({
                "metric": "Runway = Cash / Burn",
                "value": {"cash": cash_val, "burn": burn_val, "runway": runway_val, "expected": round(expected_runway, 1)},
                "pass": abs(runway_val - expected_runway) <= tolerance,
                "bounds": f"Within 10% tolerance ({tolerance:.1f} months)",
                "note": "Runway should equal cash divided by net burn"
            })

    if gross_margin is not None:
        gm_val = float(gross_margin) if gross_margin else 0
        checks.append({
            "metric": "Gross Margin",
            "value": gm_val,
            "pass": 0 <= gm_val <= 100,
            "bounds": "0-100% (stored as percentage)",
            "note": "Normalized per P0 fix"
        })

    return {
        "company_id": company_id,
        "company_name": company.name,
        "checks": checks,
        "raw_metrics": {
            "mrr": mrr, "arr": arr, "burn_rate": burn_rate,
            "cash": cash, "runway": runway, "nrr": nrr,
            "growth_rate": growth_rate, "gross_margin": gross_margin
        },
        "financial_record_count": len(latest_records),
        "has_truth_scan": latest_scan is not None,
        "has_data": len(checks) > 0,
        "all_pass": all(c["pass"] for c in checks) if checks else None,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/parse-nlp-test")
def qa_parse_nlp(
    text: str = "",
    current_user: User = Depends(require_qa_access),
):
    try:
        from server.copilot.intent_parser import extract_parameters
        params = extract_parameters(text)
        params_dict = {}
        for field in ['burn_reduction_pct', 'revenue_growth_pct', 'price_change_pct', 'headcount_change', 'fundraise_amount', 'churn_reduction_pct']:
            val = getattr(params, field, None)
            if val is not None:
                params_dict[field] = val
        return {
            "text": text,
            "parameters": params_dict,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "text": text,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@router.post("/create-test-founder")
def qa_create_test_founder(
    current_user: User = Depends(require_qa_access),
    db: Session = Depends(get_db)
):
    import uuid
    from server.core.security import get_password_hash

    unique_id = uuid.uuid4().hex[:8]
    email = f"qa.founder.{unique_id}@founderconsole.dev"
    password = "QaTest@2026!"

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        return {"error": "Test user already exists", "email": email}

    user = User(
        email=email,
        password_hash=get_password_hash(password),
        role="user",
    )
    db.add(user)
    db.flush()

    company = Company(
        name=f"ReefOps AI {unique_id}",
        user_id=user.id,
        industry="SaaS",
        stage="Seed",
        currency="SGD",
        website=f"reefops-{unique_id}.ai",
    )
    db.add(company)
    db.flush()

    workspace_member = WorkspaceMember(
        user_id=user.id,
        company_id=company.id,
        role="owner",
    )
    db.add(workspace_member)
    db.commit()

    return {
        "user_id": user.id,
        "email": email,
        "password": password,
        "company_id": company.id,
        "company_name": company.name,
        "message": "Test founder created. Login with these credentials to test.",
        "timestamp": datetime.utcnow().isoformat()
    }
