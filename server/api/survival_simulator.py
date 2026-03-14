"""
Public Survival Simulator API — no auth required.
POST /survival-sim/run   → run Monte Carlo simulation
GET  /survival-sim/:id   → retrieve shared result
"""
import json
import uuid
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from server.core.db import SessionLocal
from sqlalchemy import text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/survival-sim", tags=["Survival Simulator"])


class SurvivalSimRequest(BaseModel):
    cash_on_hand: float = Field(..., ge=0, description="Current cash balance")
    monthly_revenue: float = Field(..., ge=0, description="Current monthly revenue")
    monthly_expenses: float = Field(..., ge=0, description="Total monthly expenses")
    growth_rate: float = Field(default=0, ge=-100, le=500, description="Monthly revenue growth %")
    monthly_churn: float = Field(default=0, ge=0, le=100, description="Monthly churn rate %")
    planned_hires: int = Field(default=0, ge=0, le=100, description="Number of planned hires")
    avg_hire_cost: float = Field(default=8000, ge=0, description="Average monthly cost per hire")
    fundraising_month: Optional[int] = Field(default=None, ge=1, le=24, description="Month of planned fundraise")
    fundraising_amount: float = Field(default=0, ge=0, description="Expected fundraise amount")


@router.post("/run")
def run_survival_simulation(req: SurvivalSimRequest):
    from server.simulate.simulation_engine import SimulationInputs, run_monte_carlo
    from server.lib.lazy_imports import np

    gross_margin_pct = 70.0
    if req.monthly_revenue > 0:
        cogs_estimate = req.monthly_expenses * 0.3
        gross_profit = req.monthly_revenue - cogs_estimate
        gross_margin_pct = max(10, min(95, (gross_profit / req.monthly_revenue) * 100))

    opex_share = req.monthly_expenses * 0.4
    payroll_share = req.monthly_expenses * 0.5
    other_share = req.monthly_expenses * 0.1

    hiring_plan = []
    if req.planned_hires > 0:
        hires_per_quarter = max(1, req.planned_hires // 4)
        for q in range(4):
            start = q * 3 + 2
            count = hires_per_quarter if q < 3 else req.planned_hires - hires_per_quarter * 3
            if count > 0 and start <= 24:
                hiring_plan.append({
                    "start_month": start,
                    "monthly_cost": count * req.avg_hire_cost
                })

    inputs = SimulationInputs(
        baseline_revenue=req.monthly_revenue,
        baseline_growth_rate=req.growth_rate,
        gross_margin=gross_margin_pct,
        opex=opex_share,
        payroll=payroll_share,
        other_costs=other_share,
        cash_balance=req.cash_on_hand,
        hiring_plan=hiring_plan if hiring_plan else None,
        fundraise_month=req.fundraising_month,
        fundraise_amount=req.fundraising_amount,
        horizon_months=24,
        n_simulations=1000,
    )

    result = run_monte_carlo(inputs, seed=None)

    net_burn = req.monthly_expenses - req.monthly_revenue
    simple_runway = round(req.cash_on_hand / net_burn, 1) if net_burn > 0 else 999

    runway_dist = result["runway"]["distribution"]
    burn_values = result["bands"]["burn"]["p50"]

    histogram_bins = _build_histogram(runway_dist, 20)

    survival_12m = result["survival"]["12m"]
    if survival_12m >= 80:
        grade = "A"
        grade_label = "Strong"
        grade_color = "emerald"
    elif survival_12m >= 60:
        grade = "B"
        grade_label = "Moderate"
        grade_color = "yellow"
    elif survival_12m >= 40:
        grade = "C"
        grade_label = "At Risk"
        grade_color = "orange"
    else:
        grade = "D"
        grade_label = "Critical"
        grade_color = "red"

    recommendations = _generate_recommendations(req, result, simple_runway)

    sim_id = str(uuid.uuid4())[:12]
    response_data = {
        "simulation_id": sim_id,
        "inputs": req.model_dump(),
        "runway": {
            "p10": result["runway"]["p10"],
            "p50": result["runway"]["p50"],
            "p90": result["runway"]["p90"],
            "simple": simple_runway,
        },
        "survival": result["survival"],
        "grade": {"letter": grade, "label": grade_label, "color": grade_color},
        "histogram": histogram_bins,
        "burn_trajectory": [
            {"month": i + 1, "p10": round(result["bands"]["burn"]["p10"][i]), "p50": round(burn_values[i]), "p90": round(result["bands"]["burn"]["p90"][i])}
            for i in range(len(burn_values))
        ],
        "cash_trajectory": [
            {"month": i + 1, "p10": round(result["bands"]["cash"]["p10"][i]), "p50": round(result["bands"]["cash"]["p50"][i]), "p90": round(result["bands"]["cash"]["p90"][i])}
            for i in range(len(result["bands"]["cash"]["p50"]))
        ],
        "revenue_trajectory": [
            {"month": i + 1, "p10": round(result["bands"]["revenue"]["p10"][i]), "p50": round(result["bands"]["revenue"]["p50"][i]), "p90": round(result["bands"]["revenue"]["p90"][i])}
            for i in range(len(result["bands"]["revenue"]["p50"]))
        ],
        "recommendations": recommendations,
        "n_simulations": 1000,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        with SessionLocal() as db:
            db.execute(
                text("""
                    INSERT INTO survival_simulations (sim_id, inputs_json, results_json, created_at)
                    VALUES (:sid, :inputs, :results, NOW())
                """),
                {"sid": sim_id, "inputs": json.dumps(req.model_dump()), "results": json.dumps(response_data)},
            )
            db.commit()
    except Exception as e:
        logger.warning(f"Failed to persist simulation: {e}")

    return response_data


@router.get("/results/{sim_id}")
def get_simulation_result(sim_id: str):
    try:
        with SessionLocal() as db:
            row = db.execute(
                text("SELECT results_json FROM survival_simulations WHERE sim_id = :sid"),
                {"sid": sim_id},
            ).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Simulation not found")
            return json.loads(row[0])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve simulation: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve simulation")


def _build_histogram(values: list, n_bins: int = 20) -> list:
    from server.lib.lazy_imports import np
    arr = np.array(values)
    arr = np.clip(arr, 0, 60)
    counts, edges = np.histogram(arr, bins=n_bins, range=(0, 60))
    return [
        {"range_start": round(float(edges[i]), 1), "range_end": round(float(edges[i + 1]), 1), "count": int(counts[i])}
        for i in range(len(counts))
    ]


def _generate_recommendations(req: SurvivalSimRequest, result: dict, simple_runway: float) -> list:
    recs = []
    p50 = result["runway"]["p50"]
    survival_12 = result["survival"]["12m"]

    if p50 < 12:
        recs.append({
            "priority": "critical",
            "title": "Extend Your Runway",
            "description": f"Your median runway is {p50} months. Consider cutting expenses by 20-30% to buy more time.",
            "icon": "alert-triangle"
        })

    if req.monthly_expenses > 0 and req.monthly_revenue / req.monthly_expenses < 0.5:
        recs.append({
            "priority": "high",
            "title": "Revenue Gap",
            "description": "Revenue covers less than 50% of expenses. Focus on revenue growth or cost reduction.",
            "icon": "trending-up"
        })

    if req.monthly_churn > 5:
        recs.append({
            "priority": "high",
            "title": "High Churn Rate",
            "description": f"At {req.monthly_churn}% monthly churn, you're losing customers faster than most benchmarks (2-5%). Prioritize retention.",
            "icon": "users"
        })

    if req.planned_hires > 3 and p50 < 18:
        recs.append({
            "priority": "medium",
            "title": "Hiring vs Runway Trade-off",
            "description": f"Planning {req.planned_hires} hires with {p50}-month runway is risky. Consider phased hiring.",
            "icon": "user-plus"
        })

    if not req.fundraising_month and p50 < 18:
        recs.append({
            "priority": "medium",
            "title": "Consider Fundraising",
            "description": "With limited runway, start fundraising conversations now. Most rounds take 3-6 months.",
            "icon": "dollar-sign"
        })

    if survival_12 >= 80 and req.growth_rate > 5:
        recs.append({
            "priority": "low",
            "title": "Strong Position",
            "description": f"With {survival_12}% survival probability at 12 months, you have room to invest in growth.",
            "icon": "rocket"
        })

    if not recs:
        recs.append({
            "priority": "info",
            "title": "Looking Good",
            "description": "Your startup's financial trajectory appears healthy. Keep monitoring key metrics.",
            "icon": "check-circle"
        })

    return recs
