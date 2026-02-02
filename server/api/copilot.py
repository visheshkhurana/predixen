from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any, Optional, List, Literal
from datetime import datetime
from server.core.db import get_db
from server.core.security import get_current_user
from server.models.user import User
from server.models.company import Company
from server.models.scenario import Scenario
from server.models.simulation_run import SimulationRun
from server.models.truth_scan import TruthScan
from server.copilot.context_pack import build_context_pack
from server.copilot.trust import fetchVerifiedRunResult, GroundingStatus
from server.simulate.simulation_engine import SimulationInputs, run_monte_carlo
from server.lib.privacy.pii_redactor import redact_text, detect_pii
from server.api.simulations import extract_metric_value

router = APIRouter(tags=["copilot"])

class SimulateDeltas(BaseModel):
    pricing_change_pct: float = 0
    growth_uplift_pct: float = 0
    burn_reduction_pct: float = 0
    fundraise_month: Optional[int] = None
    fundraise_amount: float = 0
    gross_margin_delta_pct: float = 0

class CompareRequest(BaseModel):
    action_ids: List[str]

@router.get("/companies/{company_id}/context", response_model=Dict[str, Any])
def get_context(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    context = build_context_pack(company, db)
    return context

@router.post("/companies/{company_id}/simulate", response_model=Dict[str, Any])
def quick_simulate(
    company_id: int,
    deltas: SimulateDeltas,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    truth_scan = db.query(TruthScan).filter(
        TruthScan.company_id == company_id
    ).order_by(TruthScan.created_at.desc()).first()
    
    if not truth_scan:
        raise HTTPException(status_code=400, detail="Run a truth scan first")
    
    metrics = truth_scan.outputs_json.get("metrics", {})
    
    scenario = Scenario(
        company_id=company_id,
        name=f"Quick simulation",
        inputs_json=deltas.model_dump()
    )
    db.add(scenario)
    db.commit()
    db.refresh(scenario)
    
    inputs = SimulationInputs(
        baseline_revenue=extract_metric_value(metrics.get("monthly_revenue"), 50000),
        baseline_growth_rate=extract_metric_value(metrics.get("revenue_growth_mom"), 5),
        gross_margin=extract_metric_value(metrics.get("gross_margin"), 70) + deltas.gross_margin_delta_pct,
        opex=extract_metric_value(metrics.get("opex"), 20000),
        payroll=extract_metric_value(metrics.get("payroll"), 30000),
        other_costs=extract_metric_value(metrics.get("other_costs"), 5000),
        cash_balance=extract_metric_value(metrics.get("cash_balance"), 500000),
        pricing_change_pct=deltas.pricing_change_pct,
        growth_uplift_pct=deltas.growth_uplift_pct,
        burn_reduction_pct=deltas.burn_reduction_pct,
        fundraise_month=deltas.fundraise_month,
        fundraise_amount=deltas.fundraise_amount,
        n_simulations=500
    )
    
    outputs = run_monte_carlo(inputs, seed=None)
    
    sim_run = SimulationRun(
        scenario_id=scenario.id,
        n_sims=500,
        seed=None,
        outputs_json=outputs
    )
    db.add(sim_run)
    db.commit()
    db.refresh(sim_run)
    
    return {
        "scenario_id": scenario.id,
        "simulation_id": sim_run.id,
        **outputs
    }

@router.post("/companies/{company_id}/decision/compare", response_model=Dict[str, Any])
def compare_decisions(
    company_id: int,
    request: CompareRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    truth_scan = db.query(TruthScan).filter(
        TruthScan.company_id == company_id
    ).order_by(TruthScan.created_at.desc()).first()
    
    if not truth_scan:
        raise HTTPException(status_code=400, detail="Run a truth scan first")
    
    metrics = truth_scan.outputs_json.get("metrics", {})
    confidence = truth_scan.outputs_json.get("data_confidence_score", 50)
    
    from server.decision.decision_engine import generate_recommendations
    
    baseline_inputs = SimulationInputs(
        baseline_revenue=extract_metric_value(metrics.get("monthly_revenue"), 50000),
        baseline_growth_rate=extract_metric_value(metrics.get("revenue_growth_mom"), 5),
        gross_margin=extract_metric_value(metrics.get("gross_margin"), 70),
        opex=extract_metric_value(metrics.get("opex"), 20000),
        payroll=extract_metric_value(metrics.get("payroll"), 30000),
        other_costs=extract_metric_value(metrics.get("other_costs"), 5000),
        cash_balance=extract_metric_value(metrics.get("cash_balance"), 500000),
        n_simulations=500
    )
    
    recommendations = generate_recommendations(metrics, confidence, baseline_inputs)
    
    return {
        "recommendations": recommendations,
        "compared_actions": request.action_ids
    }


class PrivacySettings(BaseModel):
    """Privacy settings for PII redaction."""
    pii_mode: str = "standard"


class CopilotContextRequest(BaseModel):
    """Active context for Copilot - ensures grounding in correct data."""
    activeScenarioId: Optional[int] = None
    activeRunId: Optional[int] = None
    topBarScenarioId: Optional[int] = None
    mode: str = "FREE"
    uiSurface: Optional[str] = None


class CopilotChatRequest(BaseModel):
    """Request for copilot chat."""
    message: str
    include_financials: bool = True
    include_market: bool = False
    include_strategy: bool = True
    mode: str = "advisor"
    scenario_id: Optional[str] = None
    run_id: Optional[int] = None
    create_decision: bool = False
    challenge_mode: bool = False
    investor_lens: Optional[str] = None
    show_sources: bool = False
    privacy: Optional[PrivacySettings] = None
    context: Optional[CopilotContextRequest] = None
    response_mode: Optional[Literal["explain", "compare", "plan", "teach", "json"]] = None


class Citation(BaseModel):
    """Citation reference."""
    source_id: str
    label: str


class HighlightedClaim(BaseModel):
    """Claim with source citations."""
    text: str
    source_ids: List[str]
    confidence: str


class ProvenanceResponse(BaseModel):
    """Provenance block for response verification."""
    companyId: int
    scenarioId: Optional[int] = None
    scenarioName: Optional[str] = None
    runId: Optional[int] = None
    runTimestamp: Optional[str] = None
    dataSnapshotId: Optional[str] = None
    status: Optional[str] = None
    validationFlags: Optional[List[str]] = None


class CopilotChatResponse(BaseModel):
    """Response from copilot chat."""
    executive_summary: List[str]
    company_snapshot: List[str]
    financials: Optional[Dict[str, Any]] = None
    market_and_customers: Optional[Dict[str, Any]] = None
    strategy_options: Optional[List[Dict[str, Any]]] = None
    recommendations: Optional[List[Dict[str, Any]]] = None
    assumptions: List[str]
    risks: List[str]
    next_questions: List[str]
    confidence: str
    ckb_updated: bool = False
    decision_created: Optional[Dict[str, Any]] = None
    challenge: Optional[Dict[str, Any]] = None
    investor_analysis: Optional[Dict[str, Any]] = None
    citations: Optional[List[Dict[str, Any]]] = None
    highlighted_claims: Optional[List[Dict[str, Any]]] = None
    data_health: Optional[Dict[str, Any]] = None
    pii_findings: Optional[List[Dict[str, Any]]] = None
    pii_mode: Optional[str] = None
    simulation_result: Optional[Dict[str, Any]] = None
    intent_detected: Optional[str] = None
    clarifications: Optional[List[Dict[str, Any]]] = None
    follow_up_actions: Optional[List[Dict[str, Any]]] = None
    decision_advisor: Optional[Dict[str, Any]] = None
    provenance: Optional[ProvenanceResponse] = None
    grounding_status: Optional[str] = None
    response_mode: Optional[str] = None
    session_context: Optional[Dict[str, Any]] = None
    causal_drivers: Optional[List[Dict[str, Any]]] = None
    feedback_prompt: Optional[str] = None
    message_id: Optional[str] = None


class CopilotFeedbackRequest(BaseModel):
    """Request for copilot feedback."""
    message_id: str
    helpful: bool
    feedback_text: Optional[str] = None
    improvement_suggestion: Optional[str] = None


@router.post("/companies/{company_id}/chat", response_model=CopilotChatResponse)
async def copilot_chat(
    company_id: int,
    request: CopilotChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Multi-agent copilot chat endpoint.
    
    Routes the user's message to appropriate specialist agents (CFO, Market, Strategy)
    and returns a structured, actionable response.
    
    Modes:
    - advisor: Standard advisory mode (default)
    - analyst: Deep analysis mode with more detail
    - pitch: Investor-ready framing
    
    Additional features:
    - challenge_mode: Stress-tests the recommendation with counterarguments
    - investor_lens: Analyzes from a specific investor perspective (seed, series_a, series_b, pe)
    - create_decision: Creates a tracked decision from the recommendation
    - scenario_id: Uses a specific scenario's assumptions as context
    """
    from server.copilot.agents import RouterAgent
    from server.copilot.agents.base import CompanyKnowledgeBase
    from server.copilot.ckb_storage import CKBStorage
    from server.models.company_decision import CompanyDecision, CompanyScenario
    from server.lib.llm.llm_router import get_llm_router
    from server.copilot.conversation_state import conversation_store
    from server.copilot.prompt_templates import detect_response_mode, detect_clarification_needed, get_mode_instructions
    import uuid as uuid_lib
    
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    conv_state = conversation_store.get(company_id, current_user.id)
    session_context = conv_state.get_session_context()
    
    response_mode = request.response_mode or detect_response_mode(request.message)
    if request.response_mode:
        conv_state.set_response_mode(request.response_mode)
    
    if request.run_id:
        conv_state.set_active_context(run_id=request.run_id)
    
    ckb_storage = CKBStorage(db)
    ckb = ckb_storage.get_ckb(company_id)
    
    if not ckb:
        ckb = CompanyKnowledgeBase(
            company_id=company.id,
            company_name=company.name or "",
            industry=company.industry or "",
            stage=company.stage or "",
            currency=company.currency or "USD"
        )
    
    truth_scan = db.query(TruthScan).filter(
        TruthScan.company_id == company_id
    ).order_by(TruthScan.created_at.desc()).first()
    
    scenario_assumptions = {}
    request_scenario = None
    request_scenario_id = None
    if request.scenario_id:
        try:
            scenario_uuid = uuid_lib.UUID(request.scenario_id)
            request_scenario = db.query(CompanyScenario).filter(
                CompanyScenario.id == scenario_uuid,
                CompanyScenario.company_id == company_id
            ).first()
            if request_scenario:
                scenario_assumptions = request_scenario.assumptions_json or {}
                request_scenario_id = request_scenario.id
                conv_state.set_active_context(scenario_id=request_scenario.id)
                conv_state.set_last_simulation(scenario_name=request_scenario.name)
        except ValueError:
            pass
    
    clarification_needed = detect_clarification_needed(request.message, session_context)
    if clarification_needed and not session_context.get("hasPendingClarification"):
        conv_state.set_pending_clarification(clarification_needed)
        return CopilotChatResponse(
            executive_summary=[clarification_needed.get("question", "Could you clarify your question?")],
            company_snapshot=[],
            assumptions=[],
            risks=[],
            next_questions=clarification_needed.get("options", []),
            confidence="Low",
            clarifications=[clarification_needed],
            response_mode=response_mode if isinstance(response_mode, str) else response_mode.value,
            session_context=session_context
        )
    
    pii_mode = "standard"
    if request.privacy and request.privacy.pii_mode:
        pii_mode = request.privacy.pii_mode
    
    redaction_result = redact_text(request.message, mode=pii_mode)
    redacted_message = redaction_result.redacted_text
    pii_findings = redaction_result.findings
    
    from server.copilot.intent_parser import parse_intent, CopilotIntent
    from server.copilot.simulation_handler import SimulationHandler
    
    parsed_intent = parse_intent(redacted_message)
    simulation_result = None
    intent_detected = parsed_intent.intent.value
    clarifications = None
    follow_up_actions = None
    
    simulation_intents = {
        CopilotIntent.RUN_SIMULATION,
        CopilotIntent.COMPARE_SCENARIOS,
        CopilotIntent.SAVE_SCENARIO,
        CopilotIntent.LOAD_SCENARIO,
        CopilotIntent.MODIFY_PREVIOUS,
    }
    
    if parsed_intent.intent in simulation_intents:
        handler = SimulationHandler(db, company_id, current_user.id)
        sim_response = handler.handle_intent(parsed_intent)
        
        if sim_response.get('pass_to_agents'):
            pass
        else:
            simulation_result = sim_response
            clarifications = sim_response.get('clarifications')
            follow_up_actions = sim_response.get('follow_up_actions')
            
            if sim_response.get('success') or sim_response.get('action') == 'clarification_needed':
                from server.api.data_health import calculate_data_health
                data_health = calculate_data_health(truth_scan)
                
                sim_provenance = sim_response.get('provenance')
                sim_grounding = sim_response.get('grounding_status', GroundingStatus.NOT_AVAILABLE.value)
                
                sim_provenance_response = None
                if sim_provenance:
                    sim_provenance_response = ProvenanceResponse(
                        companyId=sim_provenance.get('companyId', company_id),
                        scenarioId=sim_provenance.get('scenarioId'),
                        scenarioName=sim_provenance.get('scenarioName'),
                        runId=sim_provenance.get('runId'),
                        runTimestamp=sim_provenance.get('runTimestamp'),
                        dataSnapshotId=sim_provenance.get('dataSnapshotId'),
                        status=sim_provenance.get('status'),
                        validationFlags=None
                    )
                
                return CopilotChatResponse(
                    executive_summary=[sim_response.get('summary', '')],
                    company_snapshot=[],
                    financials=None,
                    market_and_customers=None,
                    strategy_options=None,
                    recommendations=None,
                    assumptions=[],
                    risks=[],
                    next_questions=[],
                    confidence="High" if sim_response.get('success') else "Medium",
                    ckb_updated=False,
                    decision_created=None,
                    challenge=None,
                    investor_analysis=None,
                    citations=None,
                    highlighted_claims=None,
                    data_health=data_health,
                    pii_findings=pii_findings if pii_findings else None,
                    pii_mode=pii_mode,
                    simulation_result=simulation_result,
                    intent_detected=intent_detected,
                    clarifications=clarifications,
                    follow_up_actions=follow_up_actions,
                    provenance=sim_provenance_response,
                    grounding_status=sim_grounding,
                    response_mode=response_mode if isinstance(response_mode, str) else response_mode.value,
                    session_context=session_context
                )
    
    response_mode_str = response_mode if isinstance(response_mode, str) else response_mode.value
    mode_instructions = get_mode_instructions(response_mode) if hasattr(response_mode, 'value') else ""
    
    context = {
        "has_document": False,
        "extracted_financials": None,
        "truth_scan": truth_scan.outputs_json if truth_scan else None,
        "mode": request.mode,
        "challenge_mode": request.challenge_mode,
        "investor_lens": request.investor_lens,
        "scenario_assumptions": scenario_assumptions,
        "pii_mode": pii_mode,
        "response_mode": response_mode_str,
        "response_mode_instructions": mode_instructions,
        "session_context": session_context
    }
    
    llm_router = get_llm_router(
        db_session=db,
        company_id=company_id,
        user_id=current_user.id,
        pii_mode=pii_mode
    )
    
    router = RouterAgent(llm_router=llm_router)
    response = await router.process(redacted_message, ckb, context)
    
    ckb_storage.save_ckb(ckb)
    
    output = response.structured_output
    
    from server.api.data_health import calculate_data_health
    data_health = calculate_data_health(truth_scan)
    
    scenario_id_for_citation = None
    run_id_for_citation = None
    
    if request_scenario_id:
        scenario_id_for_citation = request_scenario_id
        latest_run_for_scenario = db.query(SimulationRun).filter(
            SimulationRun.scenario_id == request_scenario_id
        ).order_by(SimulationRun.created_at.desc()).first()
        if latest_run_for_scenario:
            run_id_for_citation = latest_run_for_scenario.id
    else:
        latest_run = db.query(SimulationRun).join(Scenario).filter(
            Scenario.company_id == company_id
        ).order_by(SimulationRun.created_at.desc()).first()
        if latest_run:
            scenario_id_for_citation = latest_run.scenario_id
            run_id_for_citation = latest_run.id
    
    provenance_response = None
    grounding_status_value = GroundingStatus.NOT_AVAILABLE.value
    
    if scenario_id_for_citation:
        run_result = fetchVerifiedRunResult(
            db=db,
            company_id=company_id,
            scenario_id=scenario_id_for_citation
        )
        
        grounding_status_value = run_result.grounding_status.value
        
        if run_result.provenance:
            scenario_for_provenance = db.query(Scenario).filter(
                Scenario.id == scenario_id_for_citation
            ).first()
            
            validation_flags = []
            if run_result.grounding_status == GroundingStatus.UNVERIFIED:
                validation_flags.append("INVALID_RUN")
            
            if run_result.outputs:
                run_validation = run_result.outputs.get('validation', {})
                if run_validation.get('runwayCashBurnMismatch'):
                    validation_flags.append("RUNWAY_CASH_BURN_MISMATCH")
                if run_validation.get('survivalRunwayMismatch'):
                    validation_flags.append("SURVIVAL_RUNWAY_MISMATCH")
                if run_validation.get('monteCarloZeroVariance'):
                    validation_flags.append("MONTE_CARLO_ZERO_VARIANCE")
            
            provenance_response = ProvenanceResponse(
                companyId=company_id,
                scenarioId=scenario_id_for_citation,
                scenarioName=scenario_for_provenance.name if scenario_for_provenance else None,
                runId=run_result.run_id,
                runTimestamp=run_result.provenance.run_timestamp.isoformat() if run_result.provenance.run_timestamp else None,
                dataSnapshotId=run_result.provenance.data_snapshot_id,
                status=run_result.provenance.status,
                validationFlags=validation_flags if validation_flags else None
            )
    elif run_id_for_citation:
        latest_run_for_provenance = db.query(SimulationRun).filter(
            SimulationRun.id == run_id_for_citation
        ).first()
        
        if latest_run_for_provenance:
            grounding_status_value = GroundingStatus.VERIFIED.value if latest_run_for_provenance.status == "completed" else GroundingStatus.UNVERIFIED.value
            
            scenario_for_provenance = db.query(Scenario).filter(
                Scenario.id == latest_run_for_provenance.scenario_id
            ).first()
            
            validation_flags = []
            if latest_run_for_provenance.status == "invalid":
                validation_flags.append("INVALID_RUN")
            
            provenance_response = ProvenanceResponse(
                companyId=company_id,
                scenarioId=latest_run_for_provenance.scenario_id,
                scenarioName=scenario_for_provenance.name if scenario_for_provenance else None,
                runId=run_id_for_citation,
                runTimestamp=latest_run_for_provenance.created_at.isoformat() if latest_run_for_provenance.created_at else None,
                dataSnapshotId=None,
                status=latest_run_for_provenance.status,
                validationFlags=validation_flags if validation_flags else None
            )
    
    provenance_dict = provenance_response.model_dump() if provenance_response else None
    
    from server.copilot.response_formatter import format_response_by_mode, ensure_citations, extract_causal_drivers
    
    output = format_response_by_mode(
        output,
        mode=response_mode_str,
        provenance=provenance_dict,
        session_context=session_context
    )
    output = ensure_citations(output, provenance=provenance_dict)
    causal_drivers = extract_causal_drivers(output, simulation_result=simulation_result)
    if causal_drivers:
        output["causal_drivers"] = causal_drivers
    
    conv_state.clear_pending_clarification()
    conversation_store.save(conv_state)
    
    decision_created = None
    if request.create_decision and output.get("recommendations"):
        rec = output.get("recommendations", [{}])[0] if output.get("recommendations") else {}
        decision = CompanyDecision(
            company_id=company_id,
            title=rec.get("action", request.message[:100]),
            context=request.message,
            options_json=[{"name": r.get("action", "Option"), "description": r.get("rationale", "")} 
                         for r in output.get("recommendations", [])],
            recommendation_json=rec,
            status="proposed",
            confidence=response.confidence.value,
            sources_json=["copilot"]
        )
        db.add(decision)
        db.commit()
        db.refresh(decision)
        decision_created = decision.to_dict()
    
    challenge_result = None
    if request.challenge_mode and output.get("recommendations"):
        challenge_result = generate_challenge(output.get("recommendations", []), context)
    
    investor_analysis = None
    if request.investor_lens and output.get("recommendations"):
        investor_analysis = generate_investor_analysis(
            output.get("recommendations", []), 
            request.investor_lens,
            truth_scan.outputs_json if truth_scan else {}
        )
    
    citations = generate_citations(truth_scan, output, scenario_id_for_citation, run_id_for_citation)
    highlighted_claims = generate_highlighted_claims(output, citations)
    
    conv_state.add_message("user", request.message)
    conv_state.add_message("assistant", output.get("executive_summary", [""])[0] if output.get("executive_summary") else "")
    
    return CopilotChatResponse(
        executive_summary=output.get("executive_summary", []),
        company_snapshot=output.get("company_snapshot", []),
        financials=output.get("financials"),
        market_and_customers=output.get("market_and_customers"),
        strategy_options=output.get("strategy_options"),
        recommendations=output.get("recommendations"),
        assumptions=response.assumptions,
        risks=response.risks,
        next_questions=response.next_questions,
        confidence=response.confidence.value,
        ckb_updated=True,
        decision_created=decision_created,
        challenge=challenge_result,
        investor_analysis=investor_analysis,
        citations=citations if request.show_sources else None,
        highlighted_claims=highlighted_claims if request.show_sources else None,
        data_health=data_health,
        pii_findings=pii_findings if pii_findings else None,
        pii_mode=pii_mode,
        simulation_result=simulation_result,
        intent_detected=intent_detected,
        clarifications=clarifications,
        follow_up_actions=follow_up_actions,
        decision_advisor=response.decision_advisor_output,
        provenance=provenance_response,
        grounding_status=grounding_status_value,
        response_mode=response_mode if isinstance(response_mode, str) else response_mode.value,
        session_context=session_context,
        causal_drivers=output.get("causal_drivers"),
        feedback_prompt="Was this helpful?",
        message_id=f"msg_{company_id}_{current_user.id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    )


@router.post("/companies/{company_id}/chat/feedback")
async def submit_copilot_feedback(
    company_id: int,
    request: CopilotFeedbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submit feedback for a copilot response.
    
    Tracks whether responses were helpful and captures improvement suggestions.
    """
    from server.copilot.conversation_state import conversation_store
    
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    conv_state = conversation_store.get(company_id, current_user.id)
    conv_state.add_message(
        role="feedback",
        content=f"Helpful: {request.helpful}",
        metadata={
            "message_id": request.message_id,
            "helpful": request.helpful,
            "feedback_text": request.feedback_text,
            "improvement_suggestion": request.improvement_suggestion
        }
    )
    conversation_store.save(conv_state)
    
    return {
        "success": True,
        "message": "Thank you for your feedback!",
        "message_id": request.message_id
    }


def generate_challenge(recommendations: List[Dict[str, Any]], context: Dict[str, Any]) -> Dict[str, Any]:
    """Generate challenge/counterarguments for recommendations."""
    challenges = []
    for rec in recommendations[:3]:
        action = rec.get("action", "")
        challenges.append({
            "recommendation": action,
            "counterarguments": [
                f"What if market conditions don't support this?",
                f"Have you considered the resource constraints?",
                f"What's the backup plan if this fails?"
            ],
            "stress_test": {
                "downside_scenario": f"If {action} underperforms by 30%, what's the impact?",
                "dependency_risk": "What external factors could derail this?",
                "timing_risk": "Is the timing right given current market conditions?"
            },
            "alternative_perspectives": [
                "A more conservative approach might be...",
                "A more aggressive approach might be...",
                "A pivot-focused approach might be..."
            ]
        })
    
    return {
        "mode": "challenge",
        "challenges": challenges,
        "summary": "These counterarguments help stress-test your decision before committing."
    }


def generate_investor_analysis(
    recommendations: List[Dict[str, Any]], 
    investor_type: str,
    truth_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate analysis from specific investor perspective."""
    metrics = truth_data.get("metrics", {})
    
    investor_criteria = {
        "seed": {
            "focus": ["team", "market_size", "innovation", "early_traction"],
            "concerns": ["burn_rate", "path_to_product_market_fit"],
            "typical_check": "$500K - $3M",
            "horizon": "12-18 months to next milestone"
        },
        "series_a": {
            "focus": ["product_market_fit", "growth_rate", "unit_economics", "team_scaling"],
            "concerns": ["cac_payback", "retention", "competitive_moat"],
            "typical_check": "$5M - $15M",
            "horizon": "18-24 months to Series B metrics"
        },
        "series_b": {
            "focus": ["scalability", "efficiency", "market_leadership", "repeatability"],
            "concerns": ["path_to_profitability", "market_saturation", "competition"],
            "typical_check": "$20M - $50M",
            "horizon": "24-36 months to profitability or later stage"
        },
        "pe": {
            "focus": ["profitability", "cash_flow", "market_position", "operational_efficiency"],
            "concerns": ["growth_sustainability", "margin_improvement", "integration_risk"],
            "typical_check": "$50M+",
            "horizon": "3-5 year value creation plan"
        }
    }
    
    criteria = investor_criteria.get(investor_type, investor_criteria["series_a"])
    
    analysis = {
        "investor_type": investor_type,
        "evaluation_criteria": criteria,
        "company_fit_analysis": {
            "strengths": [],
            "gaps": [],
            "score": "medium"
        },
        "recommendation_alignment": []
    }
    
    mrr = metrics.get("monthly_revenue", 0)
    growth = metrics.get("revenue_growth_mom", 0)
    runway = metrics.get("runway_months", 0)
    
    if investor_type == "seed":
        if growth > 10:
            analysis["company_fit_analysis"]["strengths"].append("Strong early growth signals")
        if runway < 6:
            analysis["company_fit_analysis"]["gaps"].append("Limited runway for experimentation")
    elif investor_type == "series_a":
        if mrr > 50000:
            analysis["company_fit_analysis"]["strengths"].append("Revenue at Series A threshold")
        if growth < 15:
            analysis["company_fit_analysis"]["gaps"].append("Growth rate below Series A expectations")
    elif investor_type == "series_b":
        if mrr > 500000:
            analysis["company_fit_analysis"]["strengths"].append("Revenue demonstrates market fit")
        if growth < 10:
            analysis["company_fit_analysis"]["gaps"].append("Need to demonstrate continued growth")
    
    for rec in recommendations[:3]:
        analysis["recommendation_alignment"].append({
            "action": rec.get("action", ""),
            "investor_perspective": f"From a {investor_type} investor view, this addresses key criteria",
            "concerns": f"Consider how this impacts {criteria['concerns'][0] if criteria['concerns'] else 'key metrics'}"
        })
    
    return analysis


def generate_citations(
    truth_scan, 
    output: Dict[str, Any], 
    scenario_id: Optional[int] = None,
    run_id: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Generate citations from truth scan and output data with scenario/run provenance."""
    citations = []
    citation_index = 1
    
    provenance_meta = {}
    if scenario_id:
        provenance_meta["scenario_id"] = scenario_id
    if run_id:
        provenance_meta["run_id"] = run_id
    if truth_scan:
        provenance_meta["truth_scan_id"] = truth_scan.id
        provenance_meta["truth_scan_at"] = truth_scan.computed_at.isoformat() if truth_scan.computed_at else None
    
    if truth_scan and truth_scan.outputs_json:
        metrics = truth_scan.outputs_json.get("metrics", {})
        
        monthly_revenue = metrics.get("monthly_revenue")
        if isinstance(monthly_revenue, (int, float)):
            citations.append({
                "source_id": f"truth_scan_{citation_index}",
                "label": "Truth Scan - Financial Metrics",
                "kind": "analysis",
                "snippet": f"Revenue: ${monthly_revenue:,.0f}/mo",
                **provenance_meta
            })
            citation_index += 1
        
        runway_months = metrics.get("runway_months")
        if isinstance(runway_months, (int, float)):
            citations.append({
                "source_id": f"truth_scan_{citation_index}",
                "label": "Truth Scan - Runway Analysis",
                "kind": "analysis",
                "snippet": f"Runway: {runway_months:.1f} months",
                **provenance_meta
            })
            citation_index += 1
    
    if output.get("financials") and output["financials"].get("sources"):
        for source in output["financials"]["sources"]:
            citations.append({
                "source_id": f"financial_{citation_index}",
                "label": f"Financial Data - {source.get('type', 'Document')}",
                "kind": source.get("kind", "pdf"),
                "page": source.get("page"),
                "snippet": source.get("snippet", "")
            })
            citation_index += 1
    
    if output.get("market_and_customers") and output["market_and_customers"].get("sources"):
        for source in output["market_and_customers"]["sources"]:
            citations.append({
                "source_id": f"market_{citation_index}",
                "label": f"Web: {source.get('title', 'Research')}",
                "kind": "web",
                "url": source.get("url"),
                "snippet": source.get("snippet", "")
            })
            citation_index += 1
    
    return citations


def generate_highlighted_claims(output: Dict[str, Any], citations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate highlighted claims with citation references."""
    claims = []
    
    if output.get("executive_summary"):
        for i, summary in enumerate(output["executive_summary"][:3]):
            if "$" in summary or "%" in summary or any(word in summary.lower() for word in ["revenue", "growth", "runway", "burn"]):
                citation_ids = [c["source_id"] for c in citations[:2]] if citations else []
                claims.append({
                    "text": summary,
                    "source_ids": citation_ids,
                    "confidence": "high" if citations else "medium"
                })
    
    if output.get("financials") and output["financials"].get("metrics"):
        metrics = output["financials"]["metrics"]
        if metrics.get("monthly_revenue"):
            claims.append({
                "text": f"Monthly revenue is ${metrics['monthly_revenue']:,.0f}",
                "source_ids": [c["source_id"] for c in citations if "Financial" in c.get("label", "")][:1],
                "confidence": "high"
            })
    
    return claims


@router.get("/companies/{company_id}/ckb", response_model=Dict[str, Any])
def get_company_knowledge_base(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the Company Knowledge Base for a company."""
    from server.copilot.ckb_storage import CKBStorage
    
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    ckb_storage = CKBStorage(db)
    ckb = ckb_storage.get_ckb(company_id)
    
    if not ckb:
        return {"company_id": company_id, "message": "No CKB data available"}
    
    return ckb.to_dict()


@router.put("/companies/{company_id}/ckb/{section}")
def update_ckb_section(
    company_id: int,
    section: str,
    data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a specific section of the Company Knowledge Base."""
    from server.copilot.ckb_storage import CKBStorage
    
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    ckb_storage = CKBStorage(db)
    success = ckb_storage.update_ckb_section(company_id, section, data)
    
    if not success:
        raise HTTPException(status_code=400, detail=f"Failed to update {section}")
    
    return {"success": True, "section": section}


class MemoExportRequest(BaseModel):
    """Request for memo export."""
    format: str = "markdown"
    include_sections: List[str] = ["executive_summary", "financials", "recommendations", "risks"]
    decision_id: Optional[str] = None
    scenario_id: Optional[str] = None


@router.post("/companies/{company_id}/memo/export")
async def export_memo(
    company_id: int,
    request: MemoExportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export a formatted memo for sharing with investors or board members.
    
    Generates a professional memo combining company data, decisions, and recommendations
    in a format suitable for investor updates or board presentations.
    """
    from server.copilot.ckb_storage import CKBStorage
    from server.models.company_decision import CompanyDecision, CompanyScenario
    from datetime import datetime
    import uuid as uuid_lib
    
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    ckb_storage = CKBStorage(db)
    ckb = ckb_storage.get_ckb(company_id)
    
    truth_scan = db.query(TruthScan).filter(
        TruthScan.company_id == company_id
    ).order_by(TruthScan.created_at.desc()).first()
    
    decision = None
    if request.decision_id:
        try:
            decision_uuid = uuid_lib.UUID(request.decision_id)
            decision = db.query(CompanyDecision).filter(
                CompanyDecision.id == decision_uuid,
                CompanyDecision.company_id == company_id
            ).first()
        except ValueError:
            pass
    
    scenario = None
    if request.scenario_id:
        try:
            scenario_uuid = uuid_lib.UUID(request.scenario_id)
            scenario = db.query(CompanyScenario).filter(
                CompanyScenario.id == scenario_uuid,
                CompanyScenario.company_id == company_id
            ).first()
        except ValueError:
            pass
    
    memo = generate_memo(
        company=company,
        ckb=ckb,
        truth_scan=truth_scan,
        decision=decision,
        scenario=scenario,
        sections=request.include_sections,
        format=request.format
    )
    
    return {
        "company_id": company_id,
        "format": request.format,
        "generated_at": datetime.utcnow().isoformat(),
        "memo": memo
    }


def generate_memo(
    company,
    ckb,
    truth_scan,
    decision,
    scenario,
    sections: List[str],
    format: str = "markdown"
) -> Dict[str, Any]:
    """Generate a formatted memo."""
    from datetime import datetime
    
    memo = {
        "title": f"{company.name} - Strategic Memo",
        "date": datetime.utcnow().strftime("%B %d, %Y"),
        "sections": []
    }
    
    if "executive_summary" in sections:
        summary = {
            "title": "Executive Summary",
            "content": []
        }
        
        if ckb and ckb.overview:
            summary["content"].append(ckb.overview.get("description", f"{company.name} overview"))
        
        if truth_scan:
            metrics = truth_scan.outputs_json.get("metrics", {})
            runway = metrics.get("runway_months", "N/A")
            mrr = metrics.get("monthly_revenue", 0)
            summary["content"].append(f"Current MRR: ${mrr:,.0f}" if mrr else "MRR: Data pending")
            summary["content"].append(f"Runway: {runway} months" if runway != "N/A" else "Runway: Data pending")
        
        memo["sections"].append(summary)
    
    if "financials" in sections and truth_scan:
        metrics = truth_scan.outputs_json.get("metrics", {})
        financials = {
            "title": "Financial Snapshot",
            "metrics": {
                "monthly_revenue": metrics.get("monthly_revenue"),
                "gross_margin": metrics.get("gross_margin"),
                "net_burn": metrics.get("net_burn"),
                "runway_months": metrics.get("runway_months"),
                "cash_balance": metrics.get("cash_balance"),
                "growth_rate": metrics.get("revenue_growth_mom")
            }
        }
        memo["sections"].append(financials)
    
    if "recommendations" in sections:
        recommendations = {
            "title": "Strategic Recommendations",
            "items": []
        }
        
        if decision:
            recommendations["items"].append({
                "decision": decision.title,
                "status": decision.status,
                "recommendation": decision.recommendation_json,
                "options": decision.options_json[:3] if decision.options_json else []
            })
        
        if ckb and ckb.decisions_made:
            for d in ckb.decisions_made[-3:]:
                recommendations["items"].append({
                    "decision": d.get("title", d.get("action", "Decision")),
                    "status": d.get("status", "proposed"),
                    "recommendation": d
                })
        
        memo["sections"].append(recommendations)
    
    if "scenario" in sections and scenario:
        scenario_section = {
            "title": f"Scenario Analysis: {scenario.name}",
            "assumptions": scenario.assumptions_json,
            "projected_outcomes": scenario.outputs_json
        }
        memo["sections"].append(scenario_section)
    
    if "risks" in sections:
        risks = {
            "title": "Key Risks & Mitigations",
            "items": []
        }
        
        if ckb and ckb.risks:
            risks["items"] = ckb.risks[:5] if isinstance(ckb.risks, list) else []
        
        if not risks["items"]:
            risks["items"] = [
                "Market conditions and competitive landscape changes",
                "Cash runway and fundraising timing",
                "Execution risk on key initiatives"
            ]
        
        memo["sections"].append(risks)
    
    if "market" in sections and ckb:
        market = {
            "title": "Market & Competitive Position",
            "icp": ckb.icp if ckb.icp else {},
            "competitors": ckb.competitors[:5] if ckb.competitors else []
        }
        memo["sections"].append(market)
    
    if format == "markdown":
        memo["formatted"] = format_memo_as_markdown(memo)
    
    return memo


def format_memo_as_markdown(memo: Dict[str, Any]) -> str:
    """Format memo as markdown string."""
    lines = [
        f"# {memo['title']}",
        f"*Generated: {memo['date']}*",
        "",
        "---",
        ""
    ]
    
    for section in memo.get("sections", []):
        lines.append(f"## {section['title']}")
        lines.append("")
        
        if "content" in section:
            for item in section["content"]:
                lines.append(f"- {item}")
            lines.append("")
        
        if "metrics" in section:
            for key, value in section["metrics"].items():
                if value is not None:
                    display_key = key.replace("_", " ").title()
                    if isinstance(value, (int, float)) and "revenue" in key or "burn" in key or "cash" in key:
                        lines.append(f"- **{display_key}**: ${value:,.0f}")
                    elif isinstance(value, (int, float)):
                        lines.append(f"- **{display_key}**: {value:.1f}")
                    else:
                        lines.append(f"- **{display_key}**: {value}")
            lines.append("")
        
        if "items" in section:
            for item in section["items"]:
                if isinstance(item, str):
                    lines.append(f"- {item}")
                elif isinstance(item, dict):
                    lines.append(f"- **{item.get('decision', 'Item')}** ({item.get('status', 'pending')})")
            lines.append("")
        
        if "assumptions" in section:
            lines.append("### Assumptions")
            for key, value in section.get("assumptions", {}).items():
                lines.append(f"- {key}: {value}")
            lines.append("")
        
        if "projected_outcomes" in section:
            lines.append("### Projected Outcomes")
            for key, value in section.get("projected_outcomes", {}).items():
                if key != "assumptions_applied":
                    lines.append(f"- {key.replace('_', ' ').title()}: {value}")
            lines.append("")
    
    lines.extend(["---", "", "*This memo was generated by Predixen Intelligence OS*"])
    
    return "\n".join(lines)
