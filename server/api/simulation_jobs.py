from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
import uuid
import logging

from server.core.db import get_db, SessionLocal
from server.core.security import get_current_user
from server.models.user import User
from server.models.scenario import Scenario
from server.models.company import Company
from server.models.simulation_job import SimulationJob, ScenarioVersion, SensitivityAnalysis, SimulationJobStatus
from server.models.truth_scan import TruthDataset, TruthScanUpload
from server.simulate.enhanced_monte_carlo import (
    run_enhanced_monte_carlo, 
    run_sensitivity_analysis,
    compute_scenario_diff,
    EnhancedSimulationInputs,
    SimulationConfig,
    ScenarioEvent,
    DistributionParams
)

router = APIRouter(prefix="/api/simulations", tags=["simulations"])
logger = logging.getLogger(__name__)


class SimulationConfigRequest(BaseModel):
    iterations: int = 1000
    horizon_months: int = 24
    seed: Optional[int] = None
    confidence_intervals: List[int] = [10, 25, 50, 75, 90]


class RunSimulationRequest(BaseModel):
    scenario_id: int
    config: Optional[SimulationConfigRequest] = None
    events: Optional[List[Dict[str, Any]]] = None
    async_execution: bool = False


class SensitivityRequest(BaseModel):
    scenario_id: int
    parameters: List[Dict[str, Any]]
    target_metric: str = "runway"
    config: Optional[SimulationConfigRequest] = None


class CreateVersionRequest(BaseModel):
    scenario_id: int
    change_notes: Optional[str] = None


class DiffRequest(BaseModel):
    version_a: int
    version_b: int


def parse_events(events_data: List[Dict]) -> List[ScenarioEvent]:
    parsed_events = []
    for e in events_data:
        impact = {}
        if e.get("impact"):
            for key, val in e["impact"].items():
                if val:
                    impact[key] = DistributionParams(
                        type=val.get("type", "fixed"),
                        value=val.get("value"),
                        mean=val.get("mean"),
                        std_dev=val.get("stdDev"),
                        min_val=val.get("min"),
                        max_val=val.get("max"),
                        mode=val.get("mode"),
                        values=val.get("values")
                    )
        
        duration = None
        if e.get("duration"):
            d = e["duration"]
            duration = DistributionParams(
                type=d.get("type", "fixed"),
                value=d.get("value", 1),
                mean=d.get("mean"),
                std_dev=d.get("stdDev"),
                min_val=d.get("min"),
                max_val=d.get("max")
            )
        
        parsed_events.append(ScenarioEvent(
            id=e.get("id", str(uuid.uuid4())),
            type=e.get("type", "custom"),
            name=e.get("name", "Event"),
            month=e.get("month", 1),
            probability=e.get("probability", 1.0),
            duration=duration,
            impact=impact,
            description=e.get("description", "")
        ))
    return parsed_events


def run_simulation_job_sync(job_id: str, db: Session):
    """Run simulation synchronously with an existing session"""
    _execute_simulation_job(job_id, db)


def run_simulation_job_async(job_id: str):
    """Run simulation asynchronously with a fresh session"""
    db = SessionLocal()
    try:
        _execute_simulation_job(job_id, db)
    finally:
        db.close()


def _execute_simulation_job(job_id: str, db: Session):
    """Core simulation job execution logic"""
    try:
        job = db.query(SimulationJob).filter(SimulationJob.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found")
            return
        
        job.status = SimulationJobStatus.RUNNING.value
        job.started_at = datetime.utcnow()
        db.commit()
        
        scenario = db.query(Scenario).filter(Scenario.id == job.scenario_id).first()
        if not scenario:
            job.status = SimulationJobStatus.FAILED.value
            job.error_message = "Scenario not found"
            db.commit()
            return
        
        inputs_json = scenario.inputs_json or {}
        events_json = inputs_json.get("events", [])
        
        config = SimulationConfig(
            iterations=job.config_json.get("iterations", 1000),
            horizon_months=job.config_json.get("horizon_months", 24),
            seed=job.seed,
            confidence_intervals=job.config_json.get("confidence_intervals", [10, 25, 50, 75, 90])
        )
        
        events = parse_events(events_json)
        
        inputs = EnhancedSimulationInputs(
            baseline_revenue=inputs_json.get("baseline_revenue", 100000),
            baseline_growth_rate=inputs_json.get("baseline_growth_rate", 5),
            gross_margin=inputs_json.get("gross_margin", 70),
            opex=inputs_json.get("opex", 20000),
            payroll=inputs_json.get("payroll", 50000),
            other_costs=inputs_json.get("other_costs", 10000),
            cash_balance=inputs_json.get("cash_balance", 500000),
            churn_rate=inputs_json.get("churn_rate", 5),
            pricing_change_pct=inputs_json.get("pricing_change_pct", 0),
            growth_uplift_pct=inputs_json.get("growth_uplift_pct", 0),
            burn_reduction_pct=inputs_json.get("burn_reduction_pct", 0),
            fundraise_month=inputs_json.get("fundraise_month"),
            fundraise_amount=inputs_json.get("fundraise_amount", 0),
            gross_margin_delta_pct=inputs_json.get("gross_margin_delta_pct", 0),
            events=events
        )
        
        result = run_enhanced_monte_carlo(inputs, config)
        result["scenarioId"] = scenario.id
        result["jobId"] = job_id
        
        job.results_json = result
        job.status = SimulationJobStatus.COMPLETED.value
        job.completed_at = datetime.utcnow()
        job.execution_time_ms = int(result.get("executionTime", 0))
        job.progress = 100
        db.commit()
        
    except Exception as e:
        logger.error(f"Simulation job {job_id} failed: {str(e)}")
        job = db.query(SimulationJob).filter(SimulationJob.id == job_id).first()
        if job:
            job.status = SimulationJobStatus.FAILED.value
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            db.commit()


@router.post("/run")
async def run_simulation(
    request: RunSimulationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip_truth_check: bool = False,
):
    scenario = db.query(Scenario).filter(Scenario.id == request.scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    if not skip_truth_check:
        company = db.query(Company).filter(Company.id == scenario.company_id).first()
        if company:
            truth_dataset_id = company.latest_truth_dataset_id
            
            if truth_dataset_id:
                truth_dataset = db.query(TruthDataset).filter(
                    TruthDataset.id == truth_dataset_id
                ).first()
                
                if truth_dataset and not truth_dataset.finalized:
                    upload = db.query(TruthScanUpload).filter(
                        TruthScanUpload.id == truth_dataset.source_upload_id
                    ).first()
                    
                    raise HTTPException(
                        status_code=409,
                        detail={
                            "code": "TRUTH_SCAN_REQUIRED",
                            "message": "Simulation locked until Truth Scan completed",
                            "upload_id": upload.id if upload else None,
                            "truth_dataset_id": truth_dataset_id,
                        }
                    )
    
    job_id = str(uuid.uuid4())
    config = request.config or SimulationConfigRequest()
    
    job = SimulationJob(
        id=job_id,
        scenario_id=request.scenario_id,
        status=SimulationJobStatus.PENDING.value,
        config_json={
            "iterations": config.iterations,
            "horizon_months": config.horizon_months,
            "confidence_intervals": config.confidence_intervals
        },
        seed=config.seed,
        created_by=current_user.id
    )
    
    if request.events:
        inputs_json = scenario.inputs_json or {}
        inputs_json["events"] = request.events
        scenario.inputs_json = inputs_json
    
    db.add(job)
    db.commit()
    db.refresh(job)
    
    if request.async_execution:
        background_tasks.add_task(run_simulation_job_async, job_id)
        return {
            "jobId": job_id,
            "status": "pending",
            "message": "Simulation job queued"
        }
    else:
        run_simulation_job_sync(job_id, db)
        db.refresh(job)
        
        if job.status == SimulationJobStatus.FAILED.value:
            raise HTTPException(status_code=500, detail=job.error_message)
        
        return job.results_json


@router.get("/jobs/{job_id}")
async def get_simulation_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    job = db.query(SimulationJob).filter(SimulationJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "id": job.id,
        "scenarioId": job.scenario_id,
        "status": job.status,
        "progress": job.progress,
        "config": job.config_json,
        "createdAt": job.created_at.isoformat() if job.created_at else None,
        "startedAt": job.started_at.isoformat() if job.started_at else None,
        "completedAt": job.completed_at.isoformat() if job.completed_at else None,
        "executionTime": job.execution_time_ms,
        "error": job.error_message,
        "results": job.results_json if job.status == SimulationJobStatus.COMPLETED.value else None
    }


@router.get("/jobs")
async def list_simulation_jobs(
    scenario_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(SimulationJob)
    
    if scenario_id:
        query = query.filter(SimulationJob.scenario_id == scenario_id)
    if status:
        query = query.filter(SimulationJob.status == status)
    
    jobs = query.order_by(SimulationJob.created_at.desc()).limit(limit).all()
    
    return [{
        "id": job.id,
        "scenarioId": job.scenario_id,
        "status": job.status,
        "progress": job.progress,
        "createdAt": job.created_at.isoformat() if job.created_at else None,
        "completedAt": job.completed_at.isoformat() if job.completed_at else None,
        "executionTime": job.execution_time_ms
    } for job in jobs]


@router.post("/sensitivity")
async def run_sensitivity_analysis_endpoint(
    request: SensitivityRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    scenario = db.query(Scenario).filter(Scenario.id == request.scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    inputs_json = scenario.inputs_json or {}
    events_json = inputs_json.get("events", [])
    
    config_data = request.config or SimulationConfigRequest()
    config = SimulationConfig(
        iterations=config_data.iterations,
        horizon_months=config_data.horizon_months,
        seed=config_data.seed
    )
    
    events = parse_events(events_json)
    
    inputs = EnhancedSimulationInputs(
        baseline_revenue=inputs_json.get("baseline_revenue", 100000),
        baseline_growth_rate=inputs_json.get("baseline_growth_rate", 5),
        gross_margin=inputs_json.get("gross_margin", 70),
        opex=inputs_json.get("opex", 20000),
        payroll=inputs_json.get("payroll", 50000),
        other_costs=inputs_json.get("other_costs", 10000),
        cash_balance=inputs_json.get("cash_balance", 500000),
        churn_rate=inputs_json.get("churn_rate", 5),
        pricing_change_pct=inputs_json.get("pricing_change_pct", 0),
        growth_uplift_pct=inputs_json.get("growth_uplift_pct", 0),
        burn_reduction_pct=inputs_json.get("burn_reduction_pct", 0),
        fundraise_month=inputs_json.get("fundraise_month"),
        fundraise_amount=inputs_json.get("fundraise_amount", 0),
        gross_margin_delta_pct=inputs_json.get("gross_margin_delta_pct", 0),
        events=events
    )
    
    result = run_sensitivity_analysis(
        inputs=inputs,
        config=config,
        parameters=request.parameters,
        target_metric=request.target_metric
    )
    
    result["scenarioId"] = scenario.id
    
    analysis = SensitivityAnalysis(
        scenario_id=scenario.id,
        target_metric=request.target_metric,
        parameters_json=request.parameters,
        results_json=result,
        execution_time_ms=int(result.get("executionTime", 0))
    )
    db.add(analysis)
    db.commit()
    
    return result


@router.post("/versions")
async def create_scenario_version(
    request: CreateVersionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    scenario = db.query(Scenario).filter(Scenario.id == request.scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    latest_version = db.query(ScenarioVersion).filter(
        ScenarioVersion.scenario_id == request.scenario_id
    ).order_by(ScenarioVersion.version.desc()).first()
    
    new_version_num = (latest_version.version + 1) if latest_version else 1
    
    inputs_json = scenario.inputs_json or {}
    
    version = ScenarioVersion(
        scenario_id=scenario.id,
        version=new_version_num,
        name=scenario.name,
        description=scenario.description,
        inputs_json=inputs_json,
        events_json=inputs_json.get("events", []),
        tags=scenario.tags or [],
        change_notes=request.change_notes,
        created_by=current_user.id
    )
    
    db.add(version)
    
    scenario.version = new_version_num
    scenario.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(version)
    
    return {
        "id": version.id,
        "scenarioId": version.scenario_id,
        "version": version.version,
        "name": version.name,
        "createdAt": version.created_at.isoformat(),
        "changeNotes": version.change_notes
    }


@router.get("/versions/{scenario_id}")
async def list_scenario_versions(
    scenario_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    versions = db.query(ScenarioVersion).filter(
        ScenarioVersion.scenario_id == scenario_id
    ).order_by(ScenarioVersion.version.desc()).all()
    
    return [{
        "id": v.id,
        "scenarioId": v.scenario_id,
        "version": v.version,
        "name": v.name,
        "description": v.description,
        "tags": v.tags,
        "createdAt": v.created_at.isoformat() if v.created_at else None,
        "changeNotes": v.change_notes
    } for v in versions]


@router.get("/versions/{scenario_id}/{version}")
async def get_scenario_version(
    scenario_id: int,
    version: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    v = db.query(ScenarioVersion).filter(
        ScenarioVersion.scenario_id == scenario_id,
        ScenarioVersion.version == version
    ).first()
    
    if not v:
        raise HTTPException(status_code=404, detail="Version not found")
    
    return {
        "id": v.id,
        "scenarioId": v.scenario_id,
        "version": v.version,
        "name": v.name,
        "description": v.description,
        "inputs": v.inputs_json,
        "events": v.events_json,
        "tags": v.tags,
        "createdAt": v.created_at.isoformat() if v.created_at else None,
        "changeNotes": v.change_notes
    }


@router.post("/versions/diff")
async def diff_scenario_versions(
    request: DiffRequest,
    scenario_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    version_a = db.query(ScenarioVersion).filter(
        ScenarioVersion.scenario_id == scenario_id,
        ScenarioVersion.version == request.version_a
    ).first()
    
    version_b = db.query(ScenarioVersion).filter(
        ScenarioVersion.scenario_id == scenario_id,
        ScenarioVersion.version == request.version_b
    ).first()
    
    if not version_a or not version_b:
        raise HTTPException(status_code=404, detail="One or both versions not found")
    
    diff = compute_scenario_diff(
        {
            "version": version_a.version,
            "inputs_json": version_a.inputs_json,
            "events_json": version_a.events_json,
            "tags": version_a.tags
        },
        {
            "version": version_b.version,
            "inputs_json": version_b.inputs_json,
            "events_json": version_b.events_json,
            "tags": version_b.tags
        }
    )
    
    return diff


@router.post("/versions/{scenario_id}/{version}/restore")
async def restore_scenario_version(
    scenario_id: int,
    version: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    target_version = db.query(ScenarioVersion).filter(
        ScenarioVersion.scenario_id == scenario_id,
        ScenarioVersion.version == version
    ).first()
    
    if not target_version:
        raise HTTPException(status_code=404, detail="Version not found")
    
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    latest_version = db.query(ScenarioVersion).filter(
        ScenarioVersion.scenario_id == scenario_id
    ).order_by(ScenarioVersion.version.desc()).first()
    
    new_version_num = (latest_version.version + 1) if latest_version else 1
    
    new_version = ScenarioVersion(
        scenario_id=scenario.id,
        version=new_version_num,
        name=target_version.name,
        description=target_version.description,
        inputs_json=target_version.inputs_json,
        events_json=target_version.events_json,
        tags=target_version.tags,
        change_notes=f"Restored from version {version}",
        created_by=current_user.id
    )
    db.add(new_version)
    
    scenario.name = target_version.name
    scenario.description = target_version.description
    scenario.inputs_json = target_version.inputs_json
    scenario.tags = target_version.tags
    scenario.version = new_version_num
    scenario.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(new_version)
    
    return {
        "id": new_version.id,
        "scenarioId": new_version.scenario_id,
        "version": new_version.version,
        "restoredFrom": version,
        "message": f"Scenario restored to version {version}"
    }
