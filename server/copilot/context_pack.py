from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from server.models.company import Company
from server.models.truth_scan import TruthScan
from server.models.scenario import Scenario
from server.models.simulation_run import SimulationRun
from server.models.decision import Decision
from server.models.financial import FinancialRecord, FinancialMetricPoint


def _serialize_financial_record(rec: FinancialRecord) -> Dict[str, Any]:
    return {
        "period": rec.period_end.isoformat() if rec.period_end else None,
        "revenue": float(rec.revenue or 0),
        "cogs": float(rec.cogs or 0),
        "opex": float(rec.opex or 0),
        "payroll": float(rec.payroll or 0),
        "other_costs": float(rec.other_costs or 0),
        "cash_balance": float(rec.cash_balance or 0),
        "mrr": float(rec.mrr) if rec.mrr is not None else None,
        "arr": float(rec.arr) if rec.arr is not None else None,
        "gross_margin": float(rec.gross_margin) if rec.gross_margin is not None else None,
        "net_burn": float(rec.net_burn) if rec.net_burn is not None else None,
        "runway_months": float(rec.runway_months) if rec.runway_months is not None else None,
        "headcount": int(rec.headcount) if rec.headcount else None,
        "customers": int(rec.customers) if rec.customers else None,
        "ltv": float(rec.ltv) if rec.ltv is not None else None,
        "cac": float(rec.cac) if rec.cac is not None else None,
        "ltv_cac_ratio": float(rec.ltv_cac_ratio) if rec.ltv_cac_ratio is not None else None,
        "arpu": float(rec.arpu) if rec.arpu is not None else None,
        "mom_growth": float(rec.mom_growth) if rec.mom_growth is not None else None,
        "marketing_expense": float(rec.marketing_expense) if rec.marketing_expense is not None else None,
    }


def build_context_pack(company: Company, db: Session) -> Dict[str, Any]:
    truth_scan = db.query(TruthScan).filter(
        TruthScan.company_id == company.id
    ).order_by(TruthScan.created_at.desc()).first()
    
    scenarios = db.query(Scenario).filter(
        Scenario.company_id == company.id
    ).order_by(Scenario.created_at.desc()).limit(5).all()
    
    latest_sim = None
    latest_decision = None
    
    for scenario in scenarios:
        sim_run = db.query(SimulationRun).filter(
            SimulationRun.scenario_id == scenario.id
        ).order_by(SimulationRun.created_at.desc()).first()
        
        if sim_run:
            if latest_sim is None or sim_run.created_at > latest_sim.created_at:
                latest_sim = sim_run
            
            decision = db.query(Decision).filter(
                Decision.simulation_run_id == sim_run.id
            ).order_by(Decision.created_at.desc()).first()
            
            if decision:
                if latest_decision is None or decision.created_at > latest_decision.created_at:
                    latest_decision = decision
    
    financial_records = db.query(FinancialRecord).filter(
        FinancialRecord.company_id == company.id
    ).order_by(FinancialRecord.period_end.desc()).limit(12).all()
    
    uploaded_metrics = db.query(FinancialMetricPoint).filter(
        FinancialMetricPoint.company_id == company.id
    ).order_by(FinancialMetricPoint.period.desc()).limit(200).all()
    
    context = {
        "company": {
            "id": company.id,
            "name": company.name,
            "industry": company.industry,
            "stage": company.stage,
            "currency": company.currency
        },
        "truth_scan": None,
        "financial_baseline": None,
        "financial_history": [],
        "uploaded_metrics": {},
        "latest_simulation": None,
        "latest_decision": None,
        "scenarios": []
    }
    
    if truth_scan:
        ts_data = truth_scan.outputs_json
        context["truth_scan"] = {
            "id": truth_scan.id,
            "computed_at": truth_scan.created_at.isoformat(),
            "metrics": ts_data.get("metrics", {}),
            "flags": ts_data.get("flags", []),
            "data_confidence_score": ts_data.get("data_confidence_score", 0),
            "quality_of_growth_index": ts_data.get("quality_of_growth_index", 0),
            "benchmark_comparisons": ts_data.get("benchmark_comparisons", [])
        }
    
    if financial_records:
        context["financial_history"] = [
            _serialize_financial_record(rec) for rec in financial_records
        ]
        latest_financial = financial_records[0]
        if not truth_scan:
            cash = float(latest_financial.cash_balance or 0)
            revenue = float(latest_financial.revenue or 0)
            total_costs = (
                float(latest_financial.opex or 0) + 
                float(latest_financial.payroll or 0) + 
                float(latest_financial.cogs or 0) + 
                float(latest_financial.other_costs or 0)
            )
            net_burn = total_costs - revenue
            runway = cash / max(net_burn, 1) if net_burn > 0 else None
            gross_margin = (revenue - float(latest_financial.cogs or 0)) / max(revenue, 1) if revenue > 0 else None
            
            context["financial_baseline"] = {
                "as_of_date": latest_financial.period_end.isoformat() if latest_financial.period_end else None,
                "metrics": {
                    "monthly_revenue": revenue,
                    "cash_balance": cash,
                    "total_expenses": total_costs,
                    "net_burn": net_burn,
                    "runway_months": runway,
                    "gross_margin": gross_margin,
                    "payroll": float(latest_financial.payroll or 0),
                    "opex": float(latest_financial.opex or 0),
                    "headcount": int(latest_financial.headcount or 0) if latest_financial.headcount else None,
                },
                "data_source": "financial_records",
                "data_confidence_note": "Based on manually entered or imported financial data. Run a Truth Scan for more comprehensive analysis."
            }
    
    if uploaded_metrics:
        metrics_by_key: Dict[str, List[Dict[str, Any]]] = {}
        for mp in uploaded_metrics:
            key = mp.metric_key
            if key not in metrics_by_key:
                metrics_by_key[key] = []
            if len(metrics_by_key[key]) < 12:
                metrics_by_key[key].append({
                    "period": mp.period.isoformat() if mp.period else None,
                    "value": float(mp.value),
                    "source": mp.source_type,
                    "confidence": mp.confidence,
                })
        context["uploaded_metrics"] = metrics_by_key
    
    if latest_sim:
        sim_data = latest_sim.outputs_json
        context["latest_simulation"] = {
            "id": latest_sim.id,
            "scenario_id": latest_sim.scenario_id,
            "computed_at": latest_sim.created_at.isoformat(),
            "runway": sim_data.get("runway", {}),
            "survival": sim_data.get("survival", {}),
            "summary": sim_data.get("summary", {})
        }
    
    if latest_decision:
        context["latest_decision"] = {
            "id": latest_decision.id,
            "computed_at": latest_decision.created_at.isoformat(),
            "recommendations": latest_decision.recommended_actions_json
        }
    
    for scenario in scenarios:
        context["scenarios"].append({
            "id": scenario.id,
            "name": scenario.name,
            "inputs": scenario.inputs_json
        })
    
    return context
