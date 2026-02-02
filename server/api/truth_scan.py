"""Truth Scan API endpoints.

This module provides the API layer for the Truth Scan validation system.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from datetime import datetime

from server.core.db import get_db
from server.core.security import get_current_user
from server.models.user import User
from server.models.company import Company
from server.models.truth_scan import (
    TruthScan,
    TruthScanUpload,
    TruthDataset,
    ValidationReport,
    ValidationIssue,
    TruthDecisionLog,
    SourceKind,
    IssueSeverity,
    IssueStatus,
)
from server.services.truth_scan import (
    run_truth_scan_pipeline,
    get_latest_truth_dataset,
    finalize_truth_dataset,
    resolve_issue,
    rule_validate,
    safe_repair,
    create_validation_report,
)
from server.truth.truth_scan import compute_truth_scan

router = APIRouter(tags=["truth"])


class TruthScanFromImportSessionRequest(BaseModel):
    company_id: int
    import_session_id: int


class TruthScanFromDatasetRequest(BaseModel):
    company_id: int
    dataset_id: int


class TruthScanFromManualBaselineRequest(BaseModel):
    company_id: int
    baseline_payload: Dict[str, Any]


class IssueResolution(BaseModel):
    issue_id: str
    value: Optional[Any] = None
    choice: Optional[str] = None
    notes: Optional[str] = None


class ResolveIssuesRequest(BaseModel):
    answers: List[IssueResolution]


@router.post("/truth-scan/from-import-session", response_model=Dict[str, Any])
def create_truth_scan_from_import_session(
    request: TruthScanFromImportSessionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a truth scan from an import session."""
    company = db.query(Company).filter(
        Company.id == request.company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    try:
        result = run_truth_scan_pipeline(
            db=db,
            company_id=request.company_id,
            source_kind=SourceKind.IMPORT_SESSION.value,
            import_session_id=request.import_session_id,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"code": "VALIDATION_ERROR", "message": str(e)})
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Truth scan from import session failed: {e}")
        raise HTTPException(status_code=500, detail={"code": "INTERNAL_ERROR", "message": "Failed to process data. Please try again."})


@router.post("/truth-scan/from-dataset", response_model=Dict[str, Any])
def create_truth_scan_from_dataset(
    request: TruthScanFromDatasetRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a truth scan from a dataset."""
    company = db.query(Company).filter(
        Company.id == request.company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    try:
        result = run_truth_scan_pipeline(
            db=db,
            company_id=request.company_id,
            source_kind=SourceKind.DATASET.value,
            dataset_id=request.dataset_id,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"code": "VALIDATION_ERROR", "message": str(e)})
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Truth scan from dataset failed: {e}")
        raise HTTPException(status_code=500, detail={"code": "INTERNAL_ERROR", "message": "Failed to process data. Please try again."})


@router.post("/truth-scan/from-manual-baseline", response_model=Dict[str, Any])
def create_truth_scan_from_manual_baseline(
    request: TruthScanFromManualBaselineRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a truth scan from a manual baseline entry."""
    company = db.query(Company).filter(
        Company.id == request.company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    try:
        result = run_truth_scan_pipeline(
            db=db,
            company_id=request.company_id,
            source_kind=SourceKind.MANUAL_BASELINE.value,
            manual_baseline_payload=request.baseline_payload,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"code": "VALIDATION_ERROR", "message": str(e)})
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Truth scan from manual baseline failed: {e}")
        raise HTTPException(status_code=500, detail={"code": "INTERNAL_ERROR", "message": "Failed to process data. Please try again."})


@router.get("/truth-scan/uploads/{upload_id}", response_model=Dict[str, Any])
def get_truth_scan_upload(
    upload_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed truth scan upload with issues and questions."""
    upload = db.query(TruthScanUpload).filter(
        TruthScanUpload.id == upload_id
    ).first()
    
    if not upload:
        raise HTTPException(status_code=404, detail="Truth scan upload not found")
    
    company = db.query(Company).filter(
        Company.id == upload.company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=403, detail="Access denied")
    
    truth_dataset = db.query(TruthDataset).filter(
        TruthDataset.source_upload_id == upload_id
    ).order_by(TruthDataset.version.desc()).first()
    
    report = db.query(ValidationReport).filter(
        ValidationReport.source_upload_id == upload_id
    ).order_by(ValidationReport.created_at.desc()).first()
    
    issues_grouped = {
        "auto_fixed": [],
        "needs_confirmation": [],
        "blocked": [],
    }
    
    questions = []
    
    if report:
        issues = db.query(ValidationIssue).filter(
            ValidationIssue.report_id == report.id
        ).all()
        
        for issue in issues:
            issue_data = {
                "id": issue.id,
                "severity": issue.severity,
                "category": issue.category,
                "metric_key": issue.metric_key,
                "message": issue.message,
                "evidence": issue.evidence,
                "suggestion": issue.suggestion,
                "status": issue.status,
            }
            
            if issue.status == IssueStatus.AUTO_FIXED.value:
                issues_grouped["auto_fixed"].append(issue_data)
            elif issue.severity == IssueSeverity.BLOCKED.value and issue.status == IssueStatus.OPEN.value:
                issues_grouped["blocked"].append(issue_data)
                if issue.suggestion:
                    questions.append({
                        "issue_id": issue.id,
                        "question": issue.message,
                        "options": issue.suggestion.get("options", []),
                        "metric_key": issue.metric_key,
                    })
            elif issue.status in [IssueStatus.OPEN.value, IssueStatus.USER_NEEDED.value]:
                issues_grouped["needs_confirmation"].append(issue_data)
                if issue.suggestion:
                    questions.append({
                        "issue_id": issue.id,
                        "question": issue.message,
                        "options": issue.suggestion.get("options", []),
                        "metric_key": issue.metric_key,
                    })
    
    latest_month_metrics = {}
    if truth_dataset and truth_dataset.facts:
        facts = truth_dataset.facts
        for metric in ["revenue", "cogs", "cash_balance"]:
            if metric in facts and facts[metric]:
                sorted_periods = sorted(facts[metric].keys(), reverse=True)
                if sorted_periods:
                    latest_month_metrics[metric] = facts[metric][sorted_periods[0]]
        
        if truth_dataset.derived:
            derived = truth_dataset.derived
            if "runway_months" in derived:
                latest_month_metrics["runway"] = derived["runway_months"]
            if "net_burn_monthly" in derived:
                burn_data = derived["net_burn_monthly"]
                if burn_data:
                    sorted_periods = sorted(burn_data.keys(), reverse=True)
                    if sorted_periods:
                        latest_month_metrics["net_burn"] = burn_data[sorted_periods[0]]
    
    return {
        "upload_id": upload.id,
        "company_id": upload.company_id,
        "source_kind": upload.source_kind,
        "status": upload.status,
        "created_at": upload.created_at.isoformat() if upload.created_at else None,
        "truth_dataset": {
            "id": truth_dataset.id if truth_dataset else None,
            "version": truth_dataset.version if truth_dataset else None,
            "finalized": truth_dataset.finalized if truth_dataset else False,
            "assumptions": truth_dataset.assumptions if truth_dataset else {},
            "coverage": truth_dataset.coverage if truth_dataset else {},
            "confidence": truth_dataset.confidence_summary if truth_dataset else {},
        },
        "latest_month_metrics": latest_month_metrics,
        "issues": issues_grouped,
        "questions": questions[:7],
        "can_finalize": len(issues_grouped["blocked"]) == 0,
    }


@router.post("/truth-scan/uploads/{upload_id}/resolve", response_model=Dict[str, Any])
def resolve_truth_scan_issues(
    upload_id: str,
    request: ResolveIssuesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Resolve validation issues with user answers."""
    upload = db.query(TruthScanUpload).filter(
        TruthScanUpload.id == upload_id
    ).first()
    
    if not upload:
        raise HTTPException(status_code=404, detail="Truth scan upload not found")
    
    company = db.query(Company).filter(
        Company.id == upload.company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=403, detail="Access denied")
    
    resolved_count = 0
    for answer in request.answers:
        resolution = {
            "value": answer.value,
            "choice": answer.choice,
            "notes": answer.notes,
        }
        if resolve_issue(db, upload_id, answer.issue_id, resolution):
            resolved_count += 1
    
    truth_dataset = db.query(TruthDataset).filter(
        TruthDataset.source_upload_id == upload_id
    ).order_by(TruthDataset.version.desc()).first()
    
    if truth_dataset:
        new_issues = rule_validate(truth_dataset)
        _, decisions = safe_repair(db, truth_dataset, new_issues)
    
    return {
        "resolved_count": resolved_count,
        "message": f"Resolved {resolved_count} issue(s)",
    }


@router.post("/truth-scan/uploads/{upload_id}/finalize", response_model=Dict[str, Any])
def finalize_truth_scan(
    upload_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Finalize the truth dataset if all blocked issues are resolved."""
    upload = db.query(TruthScanUpload).filter(
        TruthScanUpload.id == upload_id
    ).first()
    
    if not upload:
        raise HTTPException(status_code=404, detail="Truth scan upload not found")
    
    company = db.query(Company).filter(
        Company.id == upload.company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=403, detail="Access denied")
    
    truth_dataset = db.query(TruthDataset).filter(
        TruthDataset.source_upload_id == upload_id
    ).order_by(TruthDataset.version.desc()).first()
    
    if not truth_dataset:
        raise HTTPException(status_code=404, detail="No truth dataset found for this upload")
    
    success = finalize_truth_dataset(db, upload, truth_dataset)
    
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Cannot finalize: blocked issues still exist"
        )
    
    try:
        from server.utils.websocket_broadcast import broadcast_truth_scan_update_sync
        kpi_metrics = {}
        if truth_dataset.derived:
            derived = truth_dataset.derived
            kpi_metrics["runway_months"] = derived.get("runway_months", 0)
            net_burn = derived.get("net_burn_monthly", {})
            if isinstance(net_burn, dict) and net_burn:
                sorted_periods = sorted(net_burn.keys(), reverse=True)
                kpi_metrics["net_burn"] = net_burn.get(sorted_periods[0], 0)
            growth_mom = derived.get("growth_mom", {})
            if isinstance(growth_mom, dict) and growth_mom:
                sorted_periods = sorted(growth_mom.keys(), reverse=True)
                kpi_metrics["revenue_growth_mom"] = growth_mom.get(sorted_periods[0], 0)
            gross_margin = derived.get("gross_margin", {})
            if isinstance(gross_margin, dict) and gross_margin:
                sorted_periods = sorted(gross_margin.keys(), reverse=True)
                kpi_metrics["gross_margin"] = gross_margin.get(sorted_periods[0], 0)
        if truth_dataset.facts:
            facts = truth_dataset.facts
            for metric, target_key in [("revenue", "monthly_revenue"), ("cash_balance", "cash_balance")]:
                if metric in facts and facts[metric]:
                    sorted_periods = sorted(facts[metric].keys(), reverse=True)
                    if sorted_periods:
                        kpi_metrics[target_key] = facts[metric][sorted_periods[0]]
        broadcast_truth_scan_update_sync(
            company_id=upload.company_id,
            metrics=kpi_metrics,
            status="finalized"
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Failed to broadcast finalize update: {e}")
    
    return {
        "success": True,
        "truth_dataset_id": truth_dataset.id,
        "version": truth_dataset.version,
        "message": "Truth dataset finalized successfully",
    }


@router.get("/companies/{company_id}/truth/latest", response_model=Dict[str, Any])
def get_company_latest_truth(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the latest finalized truth dataset for a company."""
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    truth_dataset = get_latest_truth_dataset(db, company_id)
    
    if truth_dataset:
        return {
            "id": truth_dataset.id,
            "version": truth_dataset.version,
            "finalized": truth_dataset.finalized,
            "is_latest": truth_dataset.is_latest,
            "assumptions": truth_dataset.assumptions,
            "facts": truth_dataset.facts,
            "derived": truth_dataset.derived,
            "coverage": truth_dataset.coverage,
            "confidence_summary": truth_dataset.confidence_summary,
            "created_at": truth_dataset.created_at.isoformat() if truth_dataset.created_at else None,
        }
    
    scan = db.query(TruthScan).filter(
        TruthScan.company_id == company_id
    ).order_by(TruthScan.created_at.desc()).first()
    
    if scan:
        return {
            "id": scan.id,
            "legacy": True,
            **scan.outputs_json,
            "created_at": scan.created_at.isoformat() if scan.created_at else None,
        }
    
    return {
        "id": None,
        "message": "No truth scan data available",
        "assumptions": {},
        "facts": {},
        "derived": {},
    }


@router.post("/companies/{company_id}/truth/run", response_model=Dict[str, Any])
def run_truth_scan(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Run legacy truth scan (backward compatibility)."""
    from server.utils.websocket_broadcast import broadcast_truth_scan_update_sync
    
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    outputs = compute_truth_scan(company, db)
    
    scan = TruthScan(
        company_id=company_id,
        outputs_json=outputs
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)
    
    broadcast_truth_scan_update_sync(
        company_id=company_id,
        metrics=outputs.get("metrics", {}),
        status="completed"
    )
    
    return {
        "id": scan.id,
        **outputs
    }


@router.get("/truth-scan/uploads/{upload_id}/decision-log", response_model=Dict[str, Any])
def get_decision_log(
    upload_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the audit trail of decisions for a truth scan upload."""
    upload = db.query(TruthScanUpload).filter(
        TruthScanUpload.id == upload_id
    ).first()
    
    if not upload:
        raise HTTPException(status_code=404, detail="Truth scan upload not found")
    
    company = db.query(Company).filter(
        Company.id == upload.company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=403, detail="Access denied")
    
    logs = db.query(TruthDecisionLog).filter(
        TruthDecisionLog.source_upload_id == upload_id
    ).order_by(TruthDecisionLog.created_at.desc()).all()
    
    return {
        "upload_id": upload_id,
        "decisions": [
            {
                "id": log.id,
                "action": log.action,
                "patch": log.patch,
                "rationale": log.rationale,
                "actor": log.actor,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ],
    }
