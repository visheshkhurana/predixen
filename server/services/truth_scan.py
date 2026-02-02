"""Truth Scan validation service.

This module implements the validation pipeline that sits between data uploads
and simulation runs, ensuring data quality and consistency.
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_

from server.models import (
    Company,
    ImportSession,
    Dataset,
    FinancialRecord,
    FinancialMetricPoint,
    TruthScanUpload,
    TruthDataset,
    ValidationReport,
    ValidationIssue,
    TruthDecisionLog,
    SourceKind,
    TruthScanStatus,
    IssueSeverity,
    IssueCategory,
    IssueStatus,
    DecisionAction,
    DecisionActor,
)

logger = logging.getLogger(__name__)

CONFIDENCE_MAP = {
    "high": 0.9,
    "medium": 0.6,
    "low": 0.3,
}

CANONICAL_METRIC_MAP = {
    "revenue": "revenue",
    "cogs": "cogs",
    "cash_balance": "cash_balance",
    "cash": "cash_balance",
    "payroll": "opex_by_category.payroll",
    "salaries": "opex_by_category.payroll",
    "people_cost": "opex_by_category.payroll",
    "marketing_expense": "opex_by_category.marketing",
    "marketing": "opex_by_category.marketing",
    "other_costs": "opex_by_category.other_costs",
    "rent": "opex_by_category.rent",
    "opex": "opex_total",
    "opex_total": "opex_total",
    "operating_expenses": "opex_total",
}


def compute_net_burn(revenue: Optional[float], total_expenses: Optional[float]) -> Optional[float]:
    """Calculate net burn rate.
    
    Net burn = revenue - total_expenses
    Positive value = net positive cash flow
    Negative value = burning cash
    """
    if revenue is None or total_expenses is None:
        return None
    return revenue - total_expenses


def compute_runway_months(cash_balance: Optional[float], monthly_burn: Optional[float]) -> Optional[float]:
    """Calculate runway in months.
    
    Runway = cash_balance / |monthly_burn|
    Returns 999 if positive cash flow or zero burn.
    """
    if cash_balance is None or monthly_burn is None:
        return None
    
    if monthly_burn >= 0:
        return 999
    
    if cash_balance == 0:
        return 0.0
    
    return cash_balance / abs(monthly_burn)


def create_truth_scan_upload(
    db: Session,
    company_id: int,
    source_kind: str,
    import_session_id: Optional[int] = None,
    dataset_id: Optional[int] = None,
    manual_baseline_payload: Optional[Dict] = None,
) -> TruthScanUpload:
    """Create a new truth scan upload entry.
    
    This is the entry point for the Truth Scan validation pipeline.
    """
    upload = TruthScanUpload(
        company_id=company_id,
        source_kind=source_kind,
        import_session_id=import_session_id,
        dataset_id=dataset_id,
        manual_baseline_payload=manual_baseline_payload,
        status=TruthScanStatus.RECEIVED.value,
    )
    db.add(upload)
    db.commit()
    db.refresh(upload)
    
    logger.info(f"Created truth scan upload {upload.id} for company {company_id}")
    return upload


def infer_assumptions(
    db: Session,
    upload: TruthScanUpload,
) -> Tuple[Dict[str, Any], List[Dict]]:
    """Infer data assumptions from the source.
    
    Returns:
        Tuple of (assumptions dict, list of issues for ambiguous assumptions)
    """
    assumptions = {
        "currency": None,
        "scale": "unit",
        "time_granularity": "monthly",
        "fiscal_year_start_month": 1,
    }
    issues = []
    
    company = db.query(Company).filter(Company.id == upload.company_id).first()
    
    if upload.source_kind == SourceKind.IMPORT_SESSION.value:
        import_session = db.query(ImportSession).filter(
            ImportSession.id == upload.import_session_id
        ).first()
        
        if import_session:
            assumptions["time_granularity"] = import_session.detected_time_granularity or "monthly"
            
            metric_points = db.query(FinancialMetricPoint).filter(
                FinancialMetricPoint.import_session_id == import_session.id
            ).all()
            
            currencies = set(mp.unit for mp in metric_points if mp.unit)
            if len(currencies) == 1:
                assumptions["currency"] = list(currencies)[0]
            elif len(currencies) > 1:
                issues.append({
                    "severity": IssueSeverity.BLOCKED.value,
                    "category": IssueCategory.STRUCTURAL.value,
                    "metric_key": "assumptions.currency",
                    "message": f"Multiple currencies detected: {', '.join(currencies)}. Please confirm the primary currency.",
                    "evidence": {"currencies_found": list(currencies)},
                    "suggestion": {"options": list(currencies)},
                })
            
            raw_data = import_session.raw_data or {}
            if "summary" in raw_data:
                summary = raw_data["summary"]
                if "scale" in summary:
                    assumptions["scale"] = summary["scale"]
    
    elif upload.source_kind == SourceKind.DATASET.value:
        dataset = db.query(Dataset).filter(Dataset.id == upload.dataset_id).first()
        if dataset:
            records = db.query(FinancialRecord).filter(
                FinancialRecord.company_id == upload.company_id
            ).all()
            
            if records:
                assumptions["currency"] = company.currency if company else "USD"
    
    elif upload.source_kind == SourceKind.MANUAL_BASELINE.value:
        payload = upload.manual_baseline_payload or {}
        assumptions["currency"] = payload.get("currency", company.currency if company else "USD")
        assumptions["scale"] = payload.get("scale", "unit")
    
    if not assumptions["currency"]:
        if company and company.currency:
            assumptions["currency"] = company.currency
        else:
            issues.append({
                "severity": IssueSeverity.BLOCKED.value,
                "category": IssueCategory.STRUCTURAL.value,
                "metric_key": "assumptions.currency",
                "message": "Currency could not be determined. Please specify the currency.",
                "evidence": {},
                "suggestion": {"options": ["USD", "INR", "EUR", "GBP"]},
            })
    
    return assumptions, issues


def build_facts_from_metric_points(
    db: Session,
    import_session_id: int,
) -> Tuple[Dict[str, Dict], Dict[str, float]]:
    """Build canonical facts JSON from FinancialMetricPoint rows.
    
    Returns:
        Tuple of (facts dict, coverage dict)
    """
    facts = {
        "revenue": {},
        "cogs": {},
        "cash_balance": {},
        "opex_by_category": {},
        "opex_total": {},
    }
    
    metric_points = db.query(FinancialMetricPoint).filter(
        FinancialMetricPoint.import_session_id == import_session_id
    ).order_by(FinancialMetricPoint.period).all()
    
    periods_with_data = set()
    
    for mp in metric_points:
        if not mp.period:
            continue
            
        period_key = mp.period.strftime("%Y-%m")
        periods_with_data.add(period_key)
        
        canonical_key = CANONICAL_METRIC_MAP.get(
            mp.metric_key.lower() if mp.metric_key else "",
            mp.metric_key
        )
        
        confidence = CONFIDENCE_MAP.get(mp.confidence, 0.6)
        
        value_entry = {
            "value": mp.value,
            "confidence": confidence,
            "sources": [{
                "import_session_id": import_session_id,
                "metric_point_id": mp.id,
                "row_index": mp.row_index,
                "source_label": mp.source_label,
                "source_type": mp.source_type,
                "unit": mp.unit,
                "extraction_confidence": mp.confidence,
                "period": period_key,
            }],
        }
        
        if mp.value_raw is not None and mp.value_raw != mp.value:
            value_entry["derivation"] = f"Normalized from raw value {mp.value_raw}"
        
        if canonical_key.startswith("opex_by_category."):
            category = canonical_key.split(".")[1]
            if period_key not in facts["opex_by_category"]:
                facts["opex_by_category"][period_key] = {}
            facts["opex_by_category"][period_key][category] = value_entry
        elif canonical_key in facts:
            facts[canonical_key][period_key] = value_entry
    
    total_periods = len(periods_with_data)
    coverage = {}
    
    for metric_key in ["revenue", "cogs", "cash_balance"]:
        metric_periods = len(facts.get(metric_key, {}))
        coverage[metric_key] = (metric_periods / total_periods * 100) if total_periods > 0 else 0
    
    opex_categories = set()
    for period_data in facts.get("opex_by_category", {}).values():
        opex_categories.update(period_data.keys())
    coverage["opex_categories"] = list(opex_categories)
    
    return facts, coverage


def build_facts_from_financial_records(
    db: Session,
    company_id: int,
) -> Tuple[Dict[str, Dict], Dict[str, float]]:
    """Build canonical facts from FinancialRecord rows.
    
    Returns:
        Tuple of (facts dict, coverage dict)
    """
    facts = {
        "revenue": {},
        "cogs": {},
        "cash_balance": {},
        "opex_by_category": {},
        "opex_total": {},
    }
    
    records = db.query(FinancialRecord).filter(
        FinancialRecord.company_id == company_id
    ).order_by(FinancialRecord.period_start).all()
    
    periods_with_data = set()
    
    for rec in records:
        if not rec.period_start:
            continue
            
        period_key = rec.period_start.strftime("%Y-%m")
        periods_with_data.add(period_key)
        
        base_source = {
            "financial_record_id": rec.id,
            "source_type": rec.source_type or "csv",
            "period": period_key,
        }
        
        if rec.revenue is not None:
            facts["revenue"][period_key] = {
                "value": rec.revenue,
                "confidence": 0.9,
                "sources": [base_source],
            }
        
        if rec.cogs is not None:
            facts["cogs"][period_key] = {
                "value": rec.cogs,
                "confidence": 0.9,
                "sources": [base_source],
            }
        
        if rec.cash_balance is not None:
            facts["cash_balance"][period_key] = {
                "value": rec.cash_balance,
                "confidence": 0.9,
                "sources": [base_source],
            }
        
        if period_key not in facts["opex_by_category"]:
            facts["opex_by_category"][period_key] = {}
        
        if rec.payroll is not None:
            facts["opex_by_category"][period_key]["payroll"] = {
                "value": rec.payroll,
                "confidence": 0.9,
                "sources": [base_source],
            }
        
        if rec.marketing_expense is not None:
            facts["opex_by_category"][period_key]["marketing"] = {
                "value": rec.marketing_expense,
                "confidence": 0.9,
                "sources": [base_source],
            }
        
        if rec.other_costs is not None:
            facts["opex_by_category"][period_key]["other_costs"] = {
                "value": rec.other_costs,
                "confidence": 0.9,
                "sources": [base_source],
            }
        
        if rec.opex is not None:
            facts["opex_total"][period_key] = {
                "value": rec.opex,
                "confidence": 0.9,
                "sources": [base_source],
            }
    
    total_periods = len(periods_with_data)
    coverage = {}
    
    for metric_key in ["revenue", "cogs", "cash_balance", "opex_total"]:
        metric_periods = len(facts.get(metric_key, {}))
        coverage[metric_key] = (metric_periods / total_periods * 100) if total_periods > 0 else 0
    
    return facts, coverage


def build_truth_dataset(
    db: Session,
    upload: TruthScanUpload,
    assumptions: Dict[str, Any],
) -> TruthDataset:
    """Build the canonical truth dataset from source data.
    
    This creates the monthly facts JSON with full provenance tracking.
    """
    facts = {}
    coverage = {}
    
    if upload.source_kind == SourceKind.IMPORT_SESSION.value and upload.import_session_id:
        facts, coverage = build_facts_from_metric_points(db, upload.import_session_id)
    elif upload.source_kind == SourceKind.DATASET.value:
        facts, coverage = build_facts_from_financial_records(db, upload.company_id)
    elif upload.source_kind == SourceKind.MANUAL_BASELINE.value:
        payload = upload.manual_baseline_payload or {}
        period_key = datetime.now().strftime("%Y-%m")
        
        facts = {
            "revenue": {period_key: {"value": payload.get("revenue", 0), "confidence": 0.3, "sources": [{"source_type": "manual"}]}},
            "cogs": {period_key: {"value": payload.get("cogs", 0), "confidence": 0.3, "sources": [{"source_type": "manual"}]}},
            "cash_balance": {period_key: {"value": payload.get("cash_balance", 0), "confidence": 0.3, "sources": [{"source_type": "manual"}]}},
            "opex_by_category": {period_key: {}},
            "opex_total": {period_key: {"value": payload.get("opex", 0), "confidence": 0.3, "sources": [{"source_type": "manual"}]}},
        }
        
        if payload.get("payroll"):
            facts["opex_by_category"][period_key]["payroll"] = {
                "value": payload["payroll"],
                "confidence": 0.3,
                "sources": [{"source_type": "manual"}],
            }
        
        coverage = {"revenue": 100, "cogs": 100, "cash_balance": 100, "opex_total": 100}
    
    existing_count = db.query(TruthDataset).filter(
        TruthDataset.company_id == upload.company_id
    ).count()
    
    truth_dataset = TruthDataset(
        company_id=upload.company_id,
        source_upload_id=upload.id,
        version=existing_count + 1,
        finalized=False,
        is_latest=False,
        assumptions=assumptions,
        facts=facts,
        derived={},
        coverage=coverage,
        confidence_summary={},
    )
    
    db.add(truth_dataset)
    db.commit()
    db.refresh(truth_dataset)
    
    upload.status = TruthScanStatus.NORMALIZED.value
    db.commit()
    
    logger.info(f"Built truth dataset {truth_dataset.id} version {truth_dataset.version}")
    return truth_dataset


def rule_validate(
    truth_dataset: TruthDataset,
) -> List[Dict]:
    """Run validation rules against the truth dataset.
    
    Returns list of issue dictionaries.
    """
    issues = []
    facts = truth_dataset.facts or {}
    assumptions = truth_dataset.assumptions or {}
    
    if not assumptions.get("currency"):
        issues.append({
            "severity": IssueSeverity.BLOCKED.value,
            "category": IssueCategory.STRUCTURAL.value,
            "metric_key": "assumptions.currency",
            "message": "Currency is not specified.",
            "evidence": {},
        })
    
    if not assumptions.get("time_granularity"):
        issues.append({
            "severity": IssueSeverity.BLOCKED.value,
            "category": IssueCategory.STRUCTURAL.value,
            "metric_key": "assumptions.time_granularity",
            "message": "Time granularity is not specified.",
            "evidence": {},
        })
    
    revenue_periods = len(facts.get("revenue", {}))
    cash_periods = len(facts.get("cash_balance", {}))
    opex_periods = len(facts.get("opex_total", {}))
    opex_cat_periods = len(facts.get("opex_by_category", {}))
    
    has_opex = opex_periods > 0 or opex_cat_periods > 0
    
    if revenue_periods == 0:
        issues.append({
            "severity": IssueSeverity.BLOCKED.value,
            "category": IssueCategory.STRUCTURAL.value,
            "metric_key": "revenue",
            "message": "No revenue time series data found. Simulation cannot run without revenue data.",
            "evidence": {"periods_found": 0},
        })
    
    if cash_periods == 0:
        issues.append({
            "severity": IssueSeverity.BLOCKED.value,
            "category": IssueCategory.STRUCTURAL.value,
            "metric_key": "cash_balance",
            "message": "No cash balance time series data found. Runway calculations require cash data.",
            "evidence": {"periods_found": 0},
        })
    
    if not has_opex:
        issues.append({
            "severity": IssueSeverity.BLOCKED.value,
            "category": IssueCategory.STRUCTURAL.value,
            "metric_key": "opex",
            "message": "No operating expense data found. Burn rate calculations require expense data.",
            "evidence": {"opex_total_periods": opex_periods, "opex_category_periods": opex_cat_periods},
        })
    
    revenue_data = facts.get("revenue", {})
    all_zero_revenue = all(
        entry.get("value", 0) == 0 
        for entry in revenue_data.values()
    ) if revenue_data else True
    
    opex_total_data = facts.get("opex_total", {})
    opex_cat_data = facts.get("opex_by_category", {})
    
    has_expenses = False
    for entry in opex_total_data.values():
        if entry.get("value", 0) > 0:
            has_expenses = True
            break
    
    if not has_expenses:
        for period_cats in opex_cat_data.values():
            for cat_entry in period_cats.values():
                if cat_entry.get("value", 0) > 0:
                    has_expenses = True
                    break
    
    if all_zero_revenue and has_expenses:
        issues.append({
            "severity": IssueSeverity.HIGH.value,
            "category": IssueCategory.ARITHMETIC.value,
            "metric_key": "revenue",
            "message": "Revenue is 0 for all periods but expenses are greater than 0. Is this pre-revenue or missing data?",
            "evidence": {"revenue_periods": revenue_periods, "has_expenses": True},
            "suggestion": {"options": ["Pre-revenue startup", "Revenue data missing"]},
        })
    
    opex_total = facts.get("opex_total", {})
    opex_categories = facts.get("opex_by_category", {})
    
    for period, total_entry in opex_total.items():
        if period in opex_categories:
            cat_sum = sum(
                cat.get("value", 0) 
                for cat in opex_categories[period].values()
            )
            total_val = total_entry.get("value", 0)
            
            if cat_sum > 0 and total_val > 0:
                diff_pct = abs(cat_sum - total_val) / max(cat_sum, total_val) * 100
                if diff_pct > 10:
                    issues.append({
                        "severity": IssueSeverity.MEDIUM.value,
                        "category": IssueCategory.ACCOUNTING.value,
                        "metric_key": "opex",
                        "message": f"OPEX total ({total_val:,.0f}) differs from sum of categories ({cat_sum:,.0f}) by {diff_pct:.1f}% for {period}.",
                        "evidence": {"period": period, "opex_total": total_val, "category_sum": cat_sum},
                    })
    
    return issues


def safe_repair(
    db: Session,
    truth_dataset: TruthDataset,
    issues: List[Dict],
) -> Tuple[Dict, List[Dict]]:
    """Apply safe auto-fixes and compute derived metrics.
    
    Returns:
        Tuple of (derived metrics dict, list of decision logs)
    """
    facts = truth_dataset.facts or {}
    assumptions = truth_dataset.assumptions or {}
    derived = {}
    decisions = []
    
    net_burn_monthly = {}
    revenue_data = facts.get("revenue", {})
    cogs_data = facts.get("cogs", {})
    opex_total_data = facts.get("opex_total", {})
    opex_cat_data = facts.get("opex_by_category", {})
    
    all_periods = set()
    all_periods.update(revenue_data.keys())
    all_periods.update(opex_total_data.keys())
    all_periods.update(opex_cat_data.keys())
    
    for period in sorted(all_periods):
        revenue = revenue_data.get(period, {}).get("value", 0) or 0
        cogs = cogs_data.get(period, {}).get("value", 0) or 0
        
        opex = opex_total_data.get(period, {}).get("value", 0) or 0
        if opex == 0 and period in opex_cat_data:
            opex = sum(
                cat.get("value", 0) or 0 
                for cat in opex_cat_data[period].values()
            )
        
        burn = (opex + cogs) - revenue
        
        if burn < 0:
            net_burn_monthly[period] = {
                "value": burn,
                "label": "net_profit",
                "derivation": f"burn = ({opex:,.0f} + {cogs:,.0f}) - {revenue:,.0f} = {burn:,.0f} (profitable)",
            }
        else:
            net_burn_monthly[period] = {
                "value": burn,
                "label": "net_burn",
                "derivation": f"burn = ({opex:,.0f} + {cogs:,.0f}) - {revenue:,.0f} = {burn:,.0f}",
            }
    
    derived["net_burn_monthly"] = net_burn_monthly
    
    if net_burn_monthly:
        sorted_periods = sorted(net_burn_monthly.keys(), reverse=True)
        latest_period = sorted_periods[0]
        latest_burn = net_burn_monthly[latest_period]["value"]
        
        cash_data = facts.get("cash_balance", {})
        latest_cash = cash_data.get(latest_period, {}).get("value", 0)
        
        if not latest_cash and cash_data:
            cash_periods = sorted(cash_data.keys(), reverse=True)
            if cash_periods:
                latest_cash = cash_data[cash_periods[0]].get("value", 0)
        
        if latest_burn <= 0:
            derived["runway_months"] = {
                "value": "cash_generating",
                "label": "Cash-generating",
                "derivation": "Burn is zero or negative (profitable)",
            }
        elif latest_cash and latest_cash > 0:
            runway = latest_cash / latest_burn
            derived["runway_months"] = {
                "value": round(runway, 1),
                "label": f"{round(runway, 1)} months",
                "derivation": f"runway = {latest_cash:,.0f} / {latest_burn:,.0f} = {runway:.1f} months",
            }
        else:
            derived["runway_months"] = {
                "value": None,
                "label": "Unknown",
                "derivation": "Insufficient cash data",
            }
    
    growth_mom = {}
    sorted_rev_periods = sorted(revenue_data.keys())
    
    for i, period in enumerate(sorted_rev_periods):
        if i == 0:
            growth_mom[period] = {
                "value": None,
                "label": "N/A",
                "derivation": "No prior period",
            }
        else:
            prev_period = sorted_rev_periods[i - 1]
            curr_rev = revenue_data[period].get("value", 0) or 0
            prev_rev = revenue_data[prev_period].get("value", 0) or 0
            
            if prev_rev == 0:
                growth_mom[period] = {
                    "value": None,
                    "label": "Insufficient data",
                    "derivation": f"Previous revenue ({prev_period}) is 0",
                }
            else:
                growth = ((curr_rev - prev_rev) / prev_rev) * 100
                growth_mom[period] = {
                    "value": round(growth, 1),
                    "label": f"{growth:+.1f}%",
                    "derivation": f"({curr_rev:,.0f} - {prev_rev:,.0f}) / {prev_rev:,.0f} = {growth:.1f}%",
                }
    
    derived["growth_mom"] = growth_mom
    
    if revenue_data:
        revenue_vals = [e.get("value", 0) or 0 for e in revenue_data.values()]
        if cogs_data:
            cogs_vals = [cogs_data.get(p, {}).get("value", 0) or 0 for p in revenue_data.keys()]
            gross_margins = []
            for rev, cog in zip(revenue_vals, cogs_vals):
                if rev > 0:
                    gm = ((rev - cog) / rev) * 100
                    gross_margins.append(gm)
            if gross_margins:
                avg_gm = sum(gross_margins) / len(gross_margins)
                derived["gross_margin"] = {
                    "value": round(avg_gm, 1),
                    "label": f"{avg_gm:.1f}%",
                    "derivation": "Average gross margin across periods",
                }
    
    decisions.append({
        "action": DecisionAction.AUTO_FIX_APPLIED.value,
        "patch": {"derived": derived},
        "rationale": "Computed derived metrics: net_burn_monthly, runway_months, growth_mom, gross_margin",
    })
    
    truth_dataset.derived = derived
    db.commit()
    
    return derived, decisions


def create_validation_report(
    db: Session,
    truth_dataset: TruthDataset,
    upload: TruthScanUpload,
    issues: List[Dict],
    decisions: List[Dict],
) -> ValidationReport:
    """Create a validation report with all issues."""
    blocked_count = sum(1 for i in issues if i.get("severity") == IssueSeverity.BLOCKED.value)
    high_count = sum(1 for i in issues if i.get("severity") == IssueSeverity.HIGH.value)
    medium_count = sum(1 for i in issues if i.get("severity") == IssueSeverity.MEDIUM.value)
    low_count = sum(1 for i in issues if i.get("severity") == IssueSeverity.LOW.value)
    
    autofix_count = len(decisions)
    
    summary = {
        "coverage": truth_dataset.coverage,
        "assumptions": truth_dataset.assumptions,
        "confidence": truth_dataset.confidence_summary,
        "issues_by_severity": {
            "blocked": blocked_count,
            "high": high_count,
            "medium": medium_count,
            "low": low_count,
        },
        "auto_fixed_count": autofix_count,
        "can_finalize": blocked_count == 0,
    }
    
    report = ValidationReport(
        company_id=upload.company_id,
        source_upload_id=upload.id,
        truth_dataset_id=truth_dataset.id,
        summary=summary,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    
    for issue_data in issues:
        issue = ValidationIssue(
            report_id=report.id,
            severity=issue_data.get("severity"),
            category=issue_data.get("category"),
            metric_key=issue_data.get("metric_key"),
            message=issue_data.get("message"),
            evidence=issue_data.get("evidence", {}),
            suggestion=issue_data.get("suggestion"),
            can_autofix=issue_data.get("can_autofix", False),
            autofix_patch=issue_data.get("autofix_patch"),
            status=IssueStatus.OPEN.value,
        )
        db.add(issue)
    
    for decision_data in decisions:
        log = TruthDecisionLog(
            source_upload_id=upload.id,
            action=decision_data.get("action"),
            patch=decision_data.get("patch", {}),
            rationale=decision_data.get("rationale"),
            actor=DecisionActor.SYSTEM.value,
        )
        db.add(log)
    
    db.commit()
    
    if blocked_count > 0:
        upload.status = TruthScanStatus.NEEDS_USER.value
    else:
        upload.status = TruthScanStatus.VALIDATED.value
    db.commit()
    
    logger.info(f"Created validation report {report.id} with {len(issues)} issues")
    return report


def finalize_truth_dataset(
    db: Session,
    upload: TruthScanUpload,
    truth_dataset: TruthDataset,
) -> bool:
    """Finalize the truth dataset if all blocked issues are resolved.
    
    Returns True if finalized successfully, False if blocked issues exist.
    """
    report = db.query(ValidationReport).filter(
        ValidationReport.truth_dataset_id == truth_dataset.id
    ).order_by(ValidationReport.created_at.desc()).first()
    
    if report:
        blocked_issues = db.query(ValidationIssue).filter(
            and_(
                ValidationIssue.report_id == report.id,
                ValidationIssue.severity == IssueSeverity.BLOCKED.value,
                ValidationIssue.status == IssueStatus.OPEN.value,
            )
        ).count()
        
        if blocked_issues > 0:
            logger.warning(f"Cannot finalize: {blocked_issues} blocked issues remain")
            return False
    
    db.query(TruthDataset).filter(
        and_(
            TruthDataset.company_id == truth_dataset.company_id,
            TruthDataset.is_latest == True,
        )
    ).update({"is_latest": False})
    
    truth_dataset.finalized = True
    truth_dataset.is_latest = True
    
    company = db.query(Company).filter(Company.id == truth_dataset.company_id).first()
    if company:
        company.latest_truth_dataset_id = truth_dataset.id
    
    upload.status = TruthScanStatus.FINALIZED.value
    
    if upload.import_session_id:
        import_session = db.query(ImportSession).filter(
            ImportSession.id == upload.import_session_id
        ).first()
        if import_session:
            import_session.status = "saved"
            import_session.truth_scan_upload_id = upload.id
            import_session.truth_dataset_id = truth_dataset.id
    
    log = TruthDecisionLog(
        source_upload_id=upload.id,
        action=DecisionAction.DATASET_FINALIZED.value,
        patch={"truth_dataset_id": truth_dataset.id, "version": truth_dataset.version},
        rationale="Truth dataset finalized and set as latest",
        actor=DecisionActor.SYSTEM.value,
    )
    db.add(log)
    
    db.commit()
    
    logger.info(f"Finalized truth dataset {truth_dataset.id} for company {truth_dataset.company_id}")
    return True


def run_truth_scan_pipeline(
    db: Session,
    company_id: int,
    source_kind: str,
    import_session_id: Optional[int] = None,
    dataset_id: Optional[int] = None,
    manual_baseline_payload: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Run the complete truth scan validation pipeline.
    
    This is the main entry point that orchestrates all validation steps.
    """
    upload = create_truth_scan_upload(
        db=db,
        company_id=company_id,
        source_kind=source_kind,
        import_session_id=import_session_id,
        dataset_id=dataset_id,
        manual_baseline_payload=manual_baseline_payload,
    )
    
    assumptions, assumption_issues = infer_assumptions(db, upload)
    
    truth_dataset = build_truth_dataset(db, upload, assumptions)
    
    validation_issues = rule_validate(truth_dataset)
    all_issues = assumption_issues + validation_issues
    
    derived, decisions = safe_repair(db, truth_dataset, all_issues)
    
    report = create_validation_report(db, truth_dataset, upload, all_issues, decisions)
    
    blocked_count = sum(1 for i in all_issues if i.get("severity") == IssueSeverity.BLOCKED.value)
    
    try:
        from server.utils.websocket_broadcast import broadcast_truth_scan_update_sync
        kpi_metrics = {}
        if derived:
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
            company_id=company_id,
            metrics=kpi_metrics,
            status="pipeline_complete"
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Failed to broadcast truth scan update: {e}")
    
    return {
        "upload_id": upload.id,
        "truth_dataset_id": truth_dataset.id,
        "report_id": report.id,
        "status": upload.status,
        "issues_summary": {
            "blocked": blocked_count,
            "total": len(all_issues),
        },
        "can_finalize": blocked_count == 0,
    }


def get_latest_truth_dataset(db: Session, company_id: int) -> Optional[TruthDataset]:
    """Get the latest finalized truth dataset for a company."""
    return db.query(TruthDataset).filter(
        and_(
            TruthDataset.company_id == company_id,
            TruthDataset.is_latest == True,
            TruthDataset.finalized == True,
        )
    ).first()


def resolve_issue(
    db: Session,
    upload_id: str,
    issue_id: str,
    resolution: Dict[str, Any],
) -> bool:
    """Resolve a specific validation issue with user input.
    
    Args:
        db: Database session
        upload_id: Truth scan upload ID
        issue_id: Validation issue ID
        resolution: Dict with 'value' or 'choice' and optional 'notes'
    
    Returns:
        True if resolved successfully
    """
    issue = db.query(ValidationIssue).filter(ValidationIssue.id == issue_id).first()
    if not issue:
        return False
    
    upload = db.query(TruthScanUpload).filter(TruthScanUpload.id == upload_id).first()
    if not upload:
        return False
    
    truth_dataset = db.query(TruthDataset).filter(
        TruthDataset.source_upload_id == upload_id
    ).order_by(TruthDataset.version.desc()).first()
    
    if not truth_dataset:
        return False
    
    if issue.metric_key and issue.metric_key.startswith("assumptions."):
        key = issue.metric_key.replace("assumptions.", "")
        assumptions = truth_dataset.assumptions.copy()
        assumptions[key] = resolution.get("value") or resolution.get("choice")
        truth_dataset.assumptions = assumptions
    
    issue.status = IssueStatus.RESOLVED.value
    issue.resolved_at = datetime.utcnow()
    
    log = TruthDecisionLog(
        source_upload_id=upload_id,
        issue_id=issue_id,
        action=DecisionAction.USER_OVERRIDE_APPLIED.value,
        patch=resolution,
        rationale=resolution.get("notes", "User resolved issue"),
        actor=DecisionActor.USER.value,
    )
    db.add(log)
    
    db.commit()
    
    return True
