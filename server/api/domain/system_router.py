"""
Domain Router: /system
Aggregates system-level endpoints — events, flags, autopilot, admin tools.
All endpoints require platform admin authentication.
"""
from fastapi import APIRouter, Depends, Query, UploadFile, File, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import text
from server.core.db import get_db
from server.api.admin import require_platform_admin

router = APIRouter(prefix="/system", tags=["System Domain"])


@router.get("/events")
def get_events(
    company_id: Optional[int] = None,
    event_type: Optional[str] = None,
    aggregate_type: Optional[str] = None,
    limit: int = Query(50, le=500),
    user=Depends(require_platform_admin),
):
    from server.events.event_store import get_events as _get_events
    cid = company_id or _get_primary_company(user)
    if not cid:
        return {"events": []}
    return {"events": _get_events(cid, event_type=event_type, aggregate_type=aggregate_type, limit=limit)}


@router.get("/events/stats")
def get_event_stats(company_id: Optional[int] = None, user=Depends(require_platform_admin)):
    from server.events.event_store import get_event_stats
    cid = company_id or _get_primary_company(user)
    if not cid:
        return {"total_events": 0, "by_type": {}}
    return get_event_stats(cid)


@router.get("/flags")
def get_all_flags(user=Depends(require_platform_admin)):
    from server.core.feature_flags import get_all_flags
    return {"flags": get_all_flags()}


@router.post("/flags/{flag_key}")
def toggle_flag(flag_key: str, enabled: bool = True, user=Depends(require_platform_admin)):
    from server.core.feature_flags import set_feature_flag
    set_feature_flag(flag_key, enabled)
    return {"key": flag_key, "enabled": enabled}


@router.get("/agents")
def get_agents(user=Depends(require_platform_admin)):
    from server.copilot.ai_governance import get_all_permissions
    return {"agents": get_all_permissions()}


@router.get("/agents/stats")
def agent_usage_stats(days: int = 7, user=Depends(require_platform_admin)):
    from server.copilot.ai_governance import get_agent_stats
    return get_agent_stats(days=days)


@router.get("/autopilot/briefing")
def get_briefing(company_id: Optional[int] = None, user=Depends(require_platform_admin)):
    from server.services.founder_autopilot import get_latest_briefing
    cid = company_id or _get_primary_company(user)
    if not cid:
        return {"message": "No company found for this user."}
    briefing = get_latest_briefing(cid)
    if not briefing:
        return {"message": "No briefing available yet. Run autopilot first."}
    return briefing


@router.post("/autopilot/run")
def run_autopilot_endpoint(company_id: Optional[int] = None, user=Depends(require_platform_admin)):
    from server.services.founder_autopilot import run_autopilot
    cid = company_id or _get_primary_company(user)
    if not cid:
        return {"error": "No company found"}
    return run_autopilot(cid)


@router.get("/autopilot/history")
def autopilot_history(company_id: Optional[int] = None, user=Depends(require_platform_admin)):
    from server.services.founder_autopilot import get_briefing_history
    cid = company_id or _get_primary_company(user)
    if not cid:
        return {"history": []}
    return {"history": get_briefing_history(cid)}


@router.get("/autopilot/risks")
def detect_risks(company_id: Optional[int] = None, user=Depends(require_platform_admin)):
    from server.services.founder_autopilot import detect_risks
    cid = company_id or _get_primary_company(user)
    if not cid:
        return {"risks": []}
    return {"risks": detect_risks(cid)}


@router.get("/confidence")
def get_confidence(company_id: Optional[int] = None, user=Depends(require_platform_admin)):
    from server.services.data_confidence import compute_all_confidence
    cid = company_id or _get_primary_company(user)
    if not cid:
        return {"overall_confidence": 0, "metrics": {}}
    return compute_all_confidence(cid)


@router.get("/platform-intelligence")
def get_platform_intelligence(
    db: Session = Depends(get_db),
    user=Depends(require_platform_admin),
):
    from server.services.pattern_aggregator import get_platform_intelligence_stats
    return get_platform_intelligence_stats(db)


@router.post("/platform-intelligence/aggregate")
def trigger_aggregation(
    db: Session = Depends(get_db),
    user=Depends(require_platform_admin),
):
    from server.services.pattern_aggregator import aggregate_decision_patterns, aggregate_benchmark_updates
    patterns_result = aggregate_decision_patterns(db)
    benchmarks_result = aggregate_benchmark_updates(db)
    return {
        "patterns": patterns_result,
        "benchmarks": benchmarks_result,
    }


class BenchmarkImport(BaseModel):
    industry: str
    stage: str
    metric_name: str
    p25: float
    p50: float
    p75: float
    direction: str = "higher_is_better"
    source: Optional[str] = None

class PatternImport(BaseModel):
    industry: str
    stage: str
    decision_type: str
    success_rate: float
    sample_size: int = 0
    median_impact: float = 0
    p25_impact: float = 0
    p75_impact: float = 0
    source: Optional[str] = None
    notes: Optional[str] = None

class ResearchDataImport(BaseModel):
    benchmarks: List[BenchmarkImport] = Field(default_factory=list)
    decision_patterns: List[PatternImport] = Field(default_factory=list)


@router.post("/import-research-data-csv")
def import_research_data_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(require_platform_admin),
):
    import csv
    import io
    import json
    from datetime import datetime
    from server.models.benchmark import Benchmark

    MAX_CSV_SIZE = 10 * 1024 * 1024
    raw = file.file.read(MAX_CSV_SIZE + 1)
    if len(raw) > MAX_CSV_SIZE:
        raise HTTPException(status_code=413, detail="CSV file exceeds 10 MB limit")
    content = raw.decode("utf-8")
    reader = csv.DictReader(io.StringIO(content))
    rows = list(reader)

    if not rows:
        return {"benchmarks": {"inserted": 0, "updated": 0}, "patterns": {"inserted": 0, "updated": 0}, "skipped_rows": 0}

    first_keys = {k.strip().lower() for k in rows[0].keys()}
    is_benchmark = "metric_name" in first_keys and "p25" in first_keys
    is_pattern = "decision_type" in first_keys and "success_rate" in first_keys

    if not is_benchmark and not is_pattern:
        raise HTTPException(
            status_code=400,
            detail="Unrecognized CSV schema. Benchmark CSVs require columns: industry, stage, metric_name, p25, p50, p75. Pattern CSVs require: industry, stage, decision_type, success_rate, sample_size.",
        )

    inserted_benchmarks = 0
    updated_benchmarks = 0
    inserted_patterns = 0
    updated_patterns = 0
    skipped_rows = 0

    if is_benchmark:
        for row in rows:
            industry = row.get("industry", "").strip().lower()
            stage = row.get("stage", "").strip().lower()
            metric_name = row.get("metric_name", "").strip().lower()
            if not all([industry, stage, metric_name]):
                skipped_rows += 1
                continue
            try:
                p25 = float(row.get("p25", 0))
                p50 = float(row.get("p50", 0))
                p75 = float(row.get("p75", 0))
            except (ValueError, TypeError):
                skipped_rows += 1
                continue
            direction = row.get("direction", "higher_is_better").strip()

            existing = db.query(Benchmark).filter_by(
                industry=industry, stage=stage, metric_name=metric_name
            ).first()
            if existing:
                existing.p25 = p25
                existing.p50 = p50
                existing.p75 = p75
                existing.direction = direction
                existing.updated_at = datetime.utcnow()
                updated_benchmarks += 1
            else:
                db.add(Benchmark(
                    industry=industry, stage=stage, metric_name=metric_name,
                    p25=p25, p50=p50, p75=p75, direction=direction,
                ))
                inserted_benchmarks += 1

    elif is_pattern:
        for row in rows:
            industry = row.get("industry", "").strip().lower()
            stage = row.get("stage", "").strip().lower()
            decision_type = row.get("decision_type", "").strip().lower()
            if not all([industry, stage, decision_type]):
                skipped_rows += 1
                continue
            try:
                success_rate = float(row.get("success_rate", 0))
                sample_size = int(float(row.get("sample_size", 0)))
                median_impact = float(row.get("median_impact", 0))
                p25_impact = float(row.get("p25_impact", 0))
                p75_impact = float(row.get("p75_impact", 0))
            except (ValueError, TypeError):
                skipped_rows += 1
                continue
            metadata = json.dumps({
                "source": row.get("source", ""),
                "notes": row.get("notes", ""),
            })

            existing_row = db.execute(
                text("""
                    SELECT id FROM cross_company_patterns
                    WHERE pattern_type='research' AND industry=:industry AND stage=:stage AND decision_type=:dt
                """),
                {"industry": industry, "stage": stage, "dt": decision_type},
            ).fetchone()
            if existing_row:
                db.execute(
                    text("""
                        UPDATE cross_company_patterns
                        SET success_rate=:sr, sample_size=:ss, median_impact=:mi,
                            p25_impact=:p25, p75_impact=:p75, metadata_json=:mj,
                            computed_at=:now
                        WHERE id=:id
                    """),
                    {
                        "sr": success_rate, "ss": sample_size, "mi": median_impact,
                        "p25": p25_impact, "p75": p75_impact, "mj": metadata,
                        "now": datetime.utcnow(), "id": existing_row[0],
                    },
                )
                updated_patterns += 1
            else:
                db.execute(
                    text("""
                        INSERT INTO cross_company_patterns
                            (pattern_type, industry, stage, decision_type, sample_size,
                             success_rate, median_impact, p25_impact, p75_impact,
                             metadata_json, contributing_companies, computed_at)
                        VALUES
                            ('research', :industry, :stage, :dt, :ss,
                             :sr, :mi, :p25, :p75, :mj, 0, :now)
                    """),
                    {
                        "industry": industry, "stage": stage, "dt": decision_type,
                        "ss": sample_size, "sr": success_rate, "mi": median_impact,
                        "p25": p25_impact, "p75": p75_impact,
                        "mj": metadata, "now": datetime.utcnow(),
                    },
                )
                inserted_patterns += 1

    db.commit()

    return {
        "benchmarks": {"inserted": inserted_benchmarks, "updated": updated_benchmarks},
        "patterns": {"inserted": inserted_patterns, "updated": updated_patterns},
        "skipped_rows": skipped_rows,
    }


@router.post("/import-research-data")
def import_research_data(
    payload: ResearchDataImport,
    db: Session = Depends(get_db),
    user=Depends(require_platform_admin),
):
    import json
    from datetime import datetime
    from server.models.benchmark import Benchmark

    inserted_benchmarks = 0
    updated_benchmarks = 0
    for b in payload.benchmarks:
        ind = b.industry.strip().lower()
        stg = b.stage.strip().lower()
        mn = b.metric_name.strip().lower()
        existing = db.query(Benchmark).filter_by(
            industry=ind, stage=stg, metric_name=mn
        ).first()
        if existing:
            existing.p25 = b.p25
            existing.p50 = b.p50
            existing.p75 = b.p75
            existing.direction = b.direction
            existing.updated_at = datetime.utcnow()
            updated_benchmarks += 1
        else:
            db.add(Benchmark(
                industry=ind, stage=stg, metric_name=mn,
                p25=b.p25, p50=b.p50, p75=b.p75, direction=b.direction,
            ))
            inserted_benchmarks += 1

    inserted_patterns = 0
    updated_patterns = 0
    for p in payload.decision_patterns:
        ind = p.industry.strip().lower()
        stg = p.stage.strip().lower()
        dt = p.decision_type.strip().lower()
        metadata = json.dumps({"source": p.source or "", "notes": p.notes or ""})
        row = db.execute(
            text("""
                SELECT id FROM cross_company_patterns
                WHERE pattern_type='research' AND industry=:industry AND stage=:stage AND decision_type=:dt
            """),
            {"industry": ind, "stage": stg, "dt": dt},
        ).fetchone()
        if row:
            db.execute(
                text("""
                    UPDATE cross_company_patterns
                    SET success_rate=:sr, sample_size=:ss, median_impact=:mi,
                        p25_impact=:p25, p75_impact=:p75, metadata_json=:mj,
                        computed_at=:now
                    WHERE id=:id
                """),
                {
                    "sr": p.success_rate, "ss": p.sample_size, "mi": p.median_impact,
                    "p25": p.p25_impact, "p75": p.p75_impact, "mj": metadata,
                    "now": datetime.utcnow(), "id": row[0],
                },
            )
            updated_patterns += 1
        else:
            db.execute(
                text("""
                    INSERT INTO cross_company_patterns
                        (pattern_type, industry, stage, decision_type, sample_size,
                         success_rate, median_impact, p25_impact, p75_impact,
                         metadata_json, contributing_companies, computed_at)
                    VALUES
                        ('research', :industry, :stage, :dt, :ss,
                         :sr, :mi, :p25, :p75, :mj, 0, :now)
                """),
                {
                    "industry": ind, "stage": stg, "dt": dt,
                    "ss": p.sample_size, "sr": p.success_rate, "mi": p.median_impact,
                    "p25": p.p25_impact, "p75": p.p75_impact,
                    "mj": metadata, "now": datetime.utcnow(),
                },
            )
            inserted_patterns += 1

    db.commit()

    return {
        "benchmarks": {"inserted": inserted_benchmarks, "updated": updated_benchmarks},
        "patterns": {"inserted": inserted_patterns, "updated": updated_patterns},
    }


@router.get("/research-data-stats")
def get_research_data_stats(
    db: Session = Depends(get_db),
    user=Depends(require_platform_admin),
):
    benchmarks_by_industry = {}
    rows = db.execute(text("SELECT industry, COUNT(*) FROM benchmarks GROUP BY industry ORDER BY industry")).fetchall()
    for r in rows:
        benchmarks_by_industry[r[0]] = r[1]

    patterns_by_type = {}
    rows = db.execute(text(
        "SELECT decision_type, COUNT(*) FROM cross_company_patterns WHERE pattern_type='research' GROUP BY decision_type ORDER BY decision_type"
    )).fetchall()
    for r in rows:
        patterns_by_type[r[0]] = r[1]

    total_benchmarks = db.execute(text("SELECT COUNT(*) FROM benchmarks")).scalar() or 0
    total_patterns = db.execute(text("SELECT COUNT(*) FROM cross_company_patterns WHERE pattern_type='research'")).scalar() or 0

    return {
        "total_benchmarks": total_benchmarks,
        "benchmarks_by_industry": benchmarks_by_industry,
        "total_patterns": total_patterns,
        "patterns_by_type": patterns_by_type,
    }


def _get_primary_company(user) -> Optional[int]:
    try:
        from server.core.db import SessionLocal
        from sqlalchemy import text
        with SessionLocal() as db:
            row = db.execute(
                text("""
                    SELECT c.id FROM companies c
                    LEFT JOIN workspace_members wm ON wm.company_id = c.id AND wm.user_id = :uid
                    WHERE c.user_id = :uid OR wm.user_id = :uid
                    ORDER BY c.id LIMIT 1
                """),
                {"uid": user.id},
            ).fetchone()
            return row[0] if row else None
    except Exception:
        return None
