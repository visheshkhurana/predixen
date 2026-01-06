from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from server.models.company import Company
from server.models.truth_scan import TruthScan
from server.models.scenario import Scenario
from server.models.simulation_run import SimulationRun
from server.models.decision import Decision

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
    
    context = {
        "company": {
            "id": company.id,
            "name": company.name,
            "industry": company.industry,
            "stage": company.stage,
            "currency": company.currency
        },
        "truth_scan": None,
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
