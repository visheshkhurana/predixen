from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from server.models.company import Company
from server.models.truth_scan import TruthScan
from server.models.scenario import Scenario
from server.models.simulation_run import SimulationRun
from server.models.decision import Decision
from server.models.financial import FinancialRecord

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
    
    # Fallback: Get latest financial record if no truth scan
    latest_financial = None
    if not truth_scan:
        latest_financial = db.query(FinancialRecord).filter(
            FinancialRecord.company_id == company.id
        ).order_by(FinancialRecord.period_end.desc()).first()
    
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
    elif latest_financial:
        # Provide financial baseline as a fallback for AI context
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
