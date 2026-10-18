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


SUSTAINABLE_RUNWAY = 999  # sentinel: revenue covers costs; never render as "999mo"


def survival_cost_lines(monthly_revenue: float, monthly_expenses: float) -> dict:
    """Engine cost lines whose month-one cash flow is revenue - total expenses.

    ``monthly_expenses`` is TOTAL monthly cost (COGS included). The old code
    estimated COGS as 30% of expenses, lowered the gross margin by it, and then
    ALSO charged 100% of expenses as opex/payroll/other -- COGS counted twice.
    The form has no COGS split, so the margin is pinned at the engine's top
    bound (95%, with no margin noise) and the cost lines are reduced by the
    remaining 5% of revenue so total cost equals the entered expenses exactly.
    The split across opex/payroll/other only changes noise weights.
    """
    gm = 95.0
    fixed = max(0.0, monthly_expenses - monthly_revenue * (1 - gm / 100.0))
    return {
        "gross_margin": gm,
        "opex": fixed * 0.4,
        "payroll": fixed * 0.5,
        "other_costs": fixed * 0.1,
    }


def split_hires_by_quarter(planned_hires: int, avg_hire_cost: float) -> list:
    """Spread N hires over four quarters (months 2, 5, 8, 11), N in total.

    The old max(1, N // 4) gave 1-2 planned hires three hires.
    """
    plan = []
    if planned_hires <= 0:
        return plan
    base, rem = divmod(int(planned_hires), 4)
    for q in range(4):
        count = base + (1 if q < rem else 0)
        if count > 0:
            plan.append({"start_month": q * 3 + 2, "count": count, "monthly_cost": count * avg_hire_cost})
    return plan


@router.post("/run")
def run_survival_simulation(req: SurvivalSimRequest):
    from server.simulate.simulation_engine import SimulationInputs, run_monte_carlo
    from server.lib.lazy_imports import np

    costs = survival_cost_lines(req.monthly_revenue, req.monthly_expenses)
    hiring_plan = split_hires_by_quarter(req.planned_hires, req.avg_hire_cost)

    inputs = SimulationInputs(
        baseline_revenue=req.monthly_revenue,
        # The engine has no churn term, so revenue churn is applied as a
        # monthly decay on top of new-revenue growth: growth is "before churn".
        baseline_growth_rate=req.growth_rate - req.monthly_churn,
        gross_margin=costs["gross_margin"],
        margin_sigma=0.0,
        opex=costs["opex"],
        payroll=costs["payroll"],
        other_costs=costs["other_costs"],
        cash_balance=req.cash_on_hand,
        hiring_plan=hiring_plan or None,
        fundraise_month=req.fundraising_month,
        fundraise_amount=req.fundraising_amount,
        horizon_months=24,
        n_simulations=1000,
    )

    # distribution_limit=None: the default payload keeps only the first 100
    # runway values while this endpoint runs (and labels) 1000. Histogram the
    # full run so the bin counts add up to n_simulations.
    result = run_monte_carlo(inputs, seed=None, distribution_limit=None)

    net_burn = req.monthly_expenses - req.monthly_revenue
    simple_runway = round(req.cash_on_hand / net_burn, 1) if net_burn > 0 else SUSTAINABLE_RUNWAY

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
        "n_simulations": result["n_simulations"],
        "assumptions": {
            "total_monthly_cost": req.monthly_expenses,
            "churn_applied_as": "monthly revenue decay (growth_rate - monthly_churn)",
            "hiring_plan": hiring_plan,
        },
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

    if p50 < 12 and p50 < SUSTAINABLE_RUNWAY:
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
