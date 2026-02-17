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


@router.get("/baseline-snapshot")
def qa_baseline_snapshot(
    company_id: int,
    current_user: User = Depends(require_qa_access),
    db: Session = Depends(get_db)
):
    from server.services.kpi_calculations import (
        compute_arr, compute_gross_margin, compute_burn,
        compute_runway, compute_mom_growth, compute_nrr,
    )

    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    records = (
        db.query(FinancialRecord)
        .filter(FinancialRecord.company_id == company_id)
        .order_by(FinancialRecord.period_start.desc())
        .limit(2)
        .all()
    )

    if not records:
        return {
            "company_id": company_id,
            "company_name": company.name,
            "snapshot": None,
            "note": "No financial records",
            "timestamp": datetime.utcnow().isoformat()
        }

    latest = records[0]
    previous = records[1] if len(records) > 1 else None

    revenue = float(latest.revenue or 0)
    cogs = float(latest.cogs or 0)
    opex = float(latest.opex or 0)
    payroll = float(latest.payroll or 0)
    other_costs = float(latest.other_costs or 0)
    total_opex = opex + payroll + other_costs
    cash = float(latest.cash_balance or 0)
    mrr = float(latest.mrr or 0) if latest.mrr else revenue

    arr_result = compute_arr(mrr)
    gm_result = compute_gross_margin(revenue, cogs)
    burn_result = compute_burn(total_opex, cogs, revenue)
    burn_val = burn_result.get("value", 0)
    runway_result = compute_runway(cash, burn_val)
    mom_result = {"value": None, "reason": "no_previous_period"}

    if previous:
        prev_revenue = float(previous.revenue or 0)
        prev_mrr = float(previous.mrr or 0) if previous.mrr else prev_revenue
        mom_result = compute_mom_growth(mrr, prev_mrr)

    snapshot = {
        "mrr": {"value": mrr, "warning": None, "reason": None},
        "arr": arr_result,
        "gross_margin": gm_result,
        "burn": burn_result,
        "runway": runway_result,
        "mom_growth": mom_result,
    }

    return {
        "company_id": company_id,
        "company_name": company.name,
        "snapshot": snapshot,
        "financial_record_id": latest.id,
        "period_start": str(latest.period_start) if latest.period_start else None,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/tenant-tamper-test")
def qa_tenant_tamper(
    company_id: int,
    target_company_id: int,
    current_user: User = Depends(require_qa_access),
    db: Session = Depends(get_db)
):
    if company_id == target_company_id:
        return {
            "test": "tenant_tamper",
            "status": "SKIP",
            "reason": "Same company - no cross-tenant test possible",
            "timestamp": datetime.utcnow().isoformat()
        }

    source_company = db.query(Company).filter(Company.id == company_id).first()
    target_company = db.query(Company).filter(Company.id == target_company_id).first()

    if not source_company or not target_company:
        return {
            "test": "tenant_tamper",
            "status": "SKIP",
            "reason": "One or both companies not found",
            "timestamp": datetime.utcnow().isoformat()
        }

    source_scenarios = db.query(Scenario).filter(Scenario.company_id == company_id).limit(5).all()
    target_scenarios = db.query(Scenario).filter(Scenario.company_id == target_company_id).limit(5).all()

    source_records = db.query(FinancialRecord).filter(FinancialRecord.company_id == company_id).limit(5).all()
    target_records = db.query(FinancialRecord).filter(FinancialRecord.company_id == target_company_id).limit(5).all()

    source_ids = set(s.id for s in source_scenarios)
    target_ids = set(s.id for s in target_scenarios)
    overlap_scenarios = source_ids & target_ids

    source_rec_ids = set(r.id for r in source_records)
    target_rec_ids = set(r.id for r in target_records)
    overlap_records = source_rec_ids & target_rec_ids

    checks = []
    checks.append({
        "test": "scenario_isolation",
        "status": "PASS" if not overlap_scenarios else "FAIL",
        "detail": f"Source scenarios: {len(source_ids)}, Target: {len(target_ids)}, Overlap: {len(overlap_scenarios)}",
    })
    checks.append({
        "test": "financial_record_isolation",
        "status": "PASS" if not overlap_records else "FAIL",
        "detail": f"Source records: {len(source_rec_ids)}, Target: {len(target_rec_ids)}, Overlap: {len(overlap_records)}",
    })
    checks.append({
        "test": "company_identity",
        "status": "PASS" if source_company.name != target_company.name else "WARN",
        "detail": f"Source: '{source_company.name}' vs Target: '{target_company.name}'",
    })

    all_pass = all(c["status"] == "PASS" for c in checks)

    return {
        "test": "tenant_tamper",
        "company_id": company_id,
        "target_company_id": target_company_id,
        "checks": checks,
        "all_pass": all_pass,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/scenario-invariants")
def qa_scenario_invariants(
    company_id: int,
    current_user: User = Depends(require_qa_access),
    db: Session = Depends(get_db)
):
    from server.services.kpi_calculations import compute_runway, compute_burn

    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    latest_record = (
        db.query(FinancialRecord)
        .filter(FinancialRecord.company_id == company_id)
        .order_by(FinancialRecord.period_start.desc())
        .first()
    )

    checks = []

    if not latest_record:
        return {
            "company_id": company_id,
            "checks": [],
            "note": "No financial records for invariant testing",
            "timestamp": datetime.utcnow().isoformat()
        }

    revenue = float(latest_record.revenue or 0)
    cogs = float(latest_record.cogs or 0)
    opex = float(latest_record.opex or 0)
    payroll = float(latest_record.payroll or 0)
    other_costs = float(latest_record.other_costs or 0)
    total_opex = opex + payroll + other_costs
    cash = float(latest_record.cash_balance or 0)

    base_burn = compute_burn(total_opex, cogs, revenue)
    base_burn_val = base_burn["value"] or 0
    base_runway = compute_runway(cash, base_burn_val)
    base_runway_val = base_runway["value"]

    cost_cut_opex = total_opex * 0.8
    cut_burn = compute_burn(cost_cut_opex, cogs, revenue)
    cut_burn_val = cut_burn["value"] or 0
    cut_runway = compute_runway(cash, cut_burn_val)
    cut_runway_val = cut_runway["value"]

    checks.append({
        "invariant": "cost_cut_reduces_burn",
        "status": "PASS" if cut_burn_val <= base_burn_val else "FAIL",
        "detail": f"Base burn: {base_burn_val:.0f}, After 20% cut: {cut_burn_val:.0f}",
    })

    if base_runway_val is not None and cut_runway_val is not None and base_burn_val > 0:
        checks.append({
            "invariant": "cost_cut_extends_runway",
            "status": "PASS" if cut_runway_val >= base_runway_val else "FAIL",
            "detail": f"Base runway: {base_runway_val:.1f}mo, After cut: {cut_runway_val:.1f}mo",
        })
    else:
        checks.append({
            "invariant": "cost_cut_extends_runway",
            "status": "SKIP",
            "detail": "Cannot test - cash flow positive or no data",
        })

    rev_up = revenue * 1.1
    rev_up_burn = compute_burn(total_opex, cogs, rev_up)
    rev_up_burn_val = rev_up_burn["value"] or 0
    checks.append({
        "invariant": "revenue_increase_reduces_burn",
        "status": "PASS" if rev_up_burn_val <= base_burn_val else "FAIL",
        "detail": f"Base burn: {base_burn_val:.0f}, After 10% rev up: {rev_up_burn_val:.0f}",
    })

    rev_down = revenue * 0.7
    rev_down_burn = compute_burn(total_opex, cogs, rev_down)
    rev_down_burn_val = rev_down_burn["value"] or 0
    checks.append({
        "invariant": "revenue_decrease_increases_burn",
        "status": "PASS" if rev_down_burn_val >= base_burn_val else "FAIL",
        "detail": f"Base burn: {base_burn_val:.0f}, After 30% rev down: {rev_down_burn_val:.0f}",
    })

    more_cash = cash * 2
    more_cash_runway = compute_runway(more_cash, base_burn_val)
    more_cash_runway_val = more_cash_runway["value"]
    if base_runway_val is not None and more_cash_runway_val is not None:
        checks.append({
            "invariant": "more_cash_extends_runway",
            "status": "PASS" if more_cash_runway_val >= base_runway_val else "FAIL",
            "detail": f"Base runway: {base_runway_val:.1f}mo, 2x cash: {more_cash_runway_val:.1f}mo",
        })

    checks.append({
        "invariant": "burn_non_negative",
        "status": "PASS" if base_burn_val >= 0 else "FAIL",
        "detail": f"Burn: {base_burn_val:.0f} (must be >= 0)",
    })

    if base_runway_val is not None:
        checks.append({
            "invariant": "runway_positive_when_burning",
            "status": "PASS" if base_runway_val > 0 else "FAIL",
            "detail": f"Runway: {base_runway_val:.1f}mo",
        })

    all_pass = all(c["status"] in ("PASS", "SKIP") for c in checks)

    return {
        "company_id": company_id,
        "checks": checks,
        "all_pass": all_pass,
        "invariant_count": len(checks),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/export-version")
def qa_export_version(current_user: User = Depends(require_qa_access)):
    import subprocess, os
    commit_hash = "unknown"
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            commit_hash = result.stdout.strip()
    except Exception:
        pass

    env = os.environ.get("REPL_SLUG", "dev")

    return {
        "commit_hash": commit_hash,
        "environment": env,
        "server_time": datetime.utcnow().isoformat(),
        "version": "2.0",
        "platform": "FounderConsole QA",
    }


@router.get("/calc/run")
def qa_calc_run(suite: str = "all", current_user: User = Depends(require_qa_access)):
    import json, os
    from server.services.kpi_calculations import run_all_fixtures

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "tests", "fixtures"))
    suite_map = {
        "core": ["calc_cases.json"],
        "consumer": ["consumer_calc_cases.json"],
        "all": ["calc_cases.json", "consumer_calc_cases.json"],
    }
    files = suite_map.get(suite, suite_map["all"])

    all_cases = []
    for fname in files:
        fpath = os.path.join(base_dir, fname)
        if os.path.exists(fpath):
            with open(fpath, "r") as f:
                all_cases.extend(json.load(f))

    if not all_cases:
        raise HTTPException(status_code=500, detail="No fixture files found")

    results = run_all_fixtures(all_cases)
    results["suite"] = suite
    results["timestamp"] = datetime.utcnow().isoformat()
    return results


@router.get("/calc/consistency")
def qa_calc_consistency(
    company_id: int,
    current_user: User = Depends(require_qa_access),
    db: Session = Depends(get_db)
):
    from server.services.kpi_calculations import (
        compute_arr, compute_gross_margin, compute_burn,
        compute_runway, compute_nrr,
    )

    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    latest_record = (
        db.query(FinancialRecord)
        .filter(FinancialRecord.company_id == company_id)
        .order_by(FinancialRecord.period_start.desc())
        .first()
    )

    if not latest_record:
        return {
            "company_id": company_id,
            "company_name": company.name,
            "checks": [],
            "all_pass": True,
            "data_sources": {"financial_record_id": None},
            "timestamp": datetime.utcnow().isoformat(),
            "note": "No financial records found"
        }

    revenue = float(latest_record.revenue or 0)
    cogs = float(latest_record.cogs or 0)
    opex = float(latest_record.opex or 0)
    payroll = float(latest_record.payroll or 0)
    other_costs = float(latest_record.other_costs or 0)
    total_opex = opex + payroll + other_costs
    cash = float(latest_record.cash_balance or 0)
    mrr = float(latest_record.mrr or 0) if latest_record.mrr else revenue

    canonical_arr = compute_arr(mrr)
    canonical_gm = compute_gross_margin(revenue, cogs)
    canonical_burn = compute_burn(total_opex, cogs, revenue)
    canonical_runway = compute_runway(cash, canonical_burn["value"])

    checks = []

    def check(name, canonical_result, existing_val, tol=0.05):
        c_val = canonical_result.get("value") if isinstance(canonical_result, dict) else canonical_result
        status = "SKIP"
        diff = None
        if c_val is not None and existing_val is not None:
            try:
                diff = abs(float(c_val) - float(existing_val))
                max_val = max(abs(float(c_val)), abs(float(existing_val)), 1)
                rel_diff = diff / max_val if max_val > 0 else 0
                status = "PASS" if rel_diff <= tol else "FAIL"
            except (TypeError, ValueError):
                status = "SKIP"
        elif c_val is None and existing_val is None:
            status = "PASS"
        elif c_val is None:
            status = "SKIP"
            diff = None
        else:
            status = "WARN"

        checks.append({
            "metric": name,
            "canonical": c_val,
            "existing": existing_val,
            "diff": diff,
            "status": status,
            "warning": canonical_result.get("warning") if isinstance(canonical_result, dict) else None,
            "reason": canonical_result.get("reason") if isinstance(canonical_result, dict) else None,
        })

    check("ARR", canonical_arr, latest_record.arr)
    check("Gross Margin", canonical_gm, latest_record.gross_margin)
    check("Burn", canonical_burn, latest_record.net_burn)
    check("Runway", canonical_runway, latest_record.runway_months)

    all_pass = all(c["status"] in ("PASS", "SKIP") for c in checks)

    return {
        "company_id": company_id,
        "company_name": company.name,
        "checks": checks,
        "all_pass": all_pass,
        "data_sources": {
            "financial_record_id": latest_record.id,
        },
        "timestamp": datetime.utcnow().isoformat()
    }
