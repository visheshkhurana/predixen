"""
Fundraising API - Cap tables, rounds, dilution simulation, and investor room.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from datetime import date, datetime
from uuid import UUID

from server.core.db import get_db
from server.core.security import get_current_user
from server.models.user import User
from server.models.company import Company
from server.models.fundraising import (
    CompanyCapTable, FundraisingRound, RoundTerms, 
    Investor, InvestorPipeline,
    InstrumentType, RoundStatus, InvestorType, PipelineStage
)
from server.lib.fundraising.cap_table_engine import (
    compute_fully_diluted,
    apply_equity_round,
    apply_safe_or_note,
    compute_ownership_summary,
    simulate_round_scenarios,
)

router = APIRouter(tags=["fundraising"])


class CapTableCreate(BaseModel):
    name: str = "Current Cap Table"
    as_of_date: Optional[date] = None
    currency: str = "USD"
    cap_table: Optional[Dict[str, Any]] = None


class CapTableUpdate(BaseModel):
    name: Optional[str] = None
    as_of_date: Optional[date] = None
    cap_table: Optional[Dict[str, Any]] = None


class RoundCreate(BaseModel):
    name: str
    target_raise: Optional[float] = None
    pre_money: Optional[float] = None
    instrument: str = "equity"
    option_pool_refresh_percent: Optional[float] = None
    use_of_funds: Optional[Dict[str, Any]] = None


class RoundUpdate(BaseModel):
    name: Optional[str] = None
    target_raise: Optional[float] = None
    pre_money: Optional[float] = None
    post_money: Optional[float] = None
    instrument: Optional[str] = None
    option_pool_refresh_percent: Optional[float] = None
    use_of_funds: Optional[Dict[str, Any]] = None
    status: Optional[str] = None


class TermsUpdate(BaseModel):
    terms: Dict[str, Any]


class InvestorCreate(BaseModel):
    name: str
    type: str = "vc"
    geography: Optional[str] = None
    stage_focus: Optional[str] = None
    thesis_tags: Optional[List[str]] = None
    contact: Optional[Dict[str, Any]] = None


class PipelineUpdate(BaseModel):
    stage: Optional[str] = None
    probability: Optional[float] = None
    notes: Optional[str] = None


class SimulateRoundRequest(BaseModel):
    cap_table_id: str
    rounds: List[Dict[str, Any]]


class InvestorRoomRequest(BaseModel):
    round_id: str
    mode: str = "vc"


@router.get("/companies/{company_id}/cap-tables")
def list_cap_tables(
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
    
    cap_tables = db.query(CompanyCapTable).filter(
        CompanyCapTable.company_id == company_id
    ).order_by(CompanyCapTable.created_at.desc()).all()
    
    return {"cap_tables": [ct.to_dict() for ct in cap_tables]}


@router.post("/companies/{company_id}/cap-tables")
def create_cap_table(
    company_id: int,
    data: CapTableCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    default_cap_table = {
        "common": [],
        "preferred": [],
        "options": {"pool_percent": 0.0, "allocated_percent": 0.0},
        "notes": [],
        "fully_diluted_shares": 0
    }
    
    cap_table = CompanyCapTable(
        company_id=company_id,
        name=data.name,
        as_of_date=data.as_of_date,
        currency=data.currency,
        cap_table_json=data.cap_table or default_cap_table
    )
    db.add(cap_table)
    db.commit()
    db.refresh(cap_table)
    
    return cap_table.to_dict()


@router.get("/companies/{company_id}/cap-tables/{cap_table_id}")
def get_cap_table(
    company_id: int,
    cap_table_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    cap_table = db.query(CompanyCapTable).filter(
        CompanyCapTable.id == cap_table_id,
        CompanyCapTable.company_id == company_id
    ).first()
    
    if not cap_table:
        raise HTTPException(status_code=404, detail="Cap table not found")
    
    result = cap_table.to_dict()
    result["fully_diluted"] = compute_fully_diluted(cap_table.cap_table_json or {})
    
    return result


@router.patch("/companies/{company_id}/cap-tables/{cap_table_id}")
def update_cap_table(
    company_id: int,
    cap_table_id: str,
    data: CapTableUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    cap_table = db.query(CompanyCapTable).filter(
        CompanyCapTable.id == cap_table_id,
        CompanyCapTable.company_id == company_id
    ).first()
    
    if not cap_table:
        raise HTTPException(status_code=404, detail="Cap table not found")
    
    if data.name is not None:
        cap_table.name = data.name
    if data.as_of_date is not None:
        cap_table.as_of_date = data.as_of_date
    if data.cap_table is not None:
        cap_table.cap_table_json = data.cap_table
    
    cap_table.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(cap_table)
    
    return cap_table.to_dict()


@router.get("/companies/{company_id}/fundraising/rounds")
def list_rounds(
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
    
    rounds = db.query(FundraisingRound).filter(
        FundraisingRound.company_id == company_id
    ).order_by(FundraisingRound.created_at.desc()).all()
    
    return {"rounds": [r.to_dict() for r in rounds]}


@router.post("/companies/{company_id}/fundraising/rounds")
def create_round(
    company_id: int,
    data: RoundCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    post_money = None
    if data.pre_money and data.target_raise:
        post_money = data.pre_money + data.target_raise
    
    round_obj = FundraisingRound(
        company_id=company_id,
        name=data.name,
        target_raise=data.target_raise,
        pre_money=data.pre_money,
        post_money=post_money,
        instrument=data.instrument,
        option_pool_refresh_percent=data.option_pool_refresh_percent,
        use_of_funds_json=data.use_of_funds or {}
    )
    db.add(round_obj)
    db.commit()
    db.refresh(round_obj)
    
    terms = RoundTerms(round_id=round_obj.id, terms_json={})
    db.add(terms)
    db.commit()
    
    return round_obj.to_dict()


@router.get("/companies/{company_id}/fundraising/rounds/{round_id}")
def get_round(
    company_id: int,
    round_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    round_obj = db.query(FundraisingRound).filter(
        FundraisingRound.id == round_id,
        FundraisingRound.company_id == company_id
    ).first()
    
    if not round_obj:
        raise HTTPException(status_code=404, detail="Round not found")
    
    result = round_obj.to_dict()
    
    if round_obj.terms:
        result["terms"] = round_obj.terms.to_dict()
    
    pipeline = db.query(InvestorPipeline).filter(
        InvestorPipeline.round_id == round_id
    ).all()
    result["pipeline"] = [p.to_dict() for p in pipeline]
    
    return result


@router.patch("/companies/{company_id}/fundraising/rounds/{round_id}")
def update_round(
    company_id: int,
    round_id: str,
    data: RoundUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    round_obj = db.query(FundraisingRound).filter(
        FundraisingRound.id == round_id,
        FundraisingRound.company_id == company_id
    ).first()
    
    if not round_obj:
        raise HTTPException(status_code=404, detail="Round not found")
    
    for field in ["name", "target_raise", "pre_money", "post_money", "instrument", 
                  "option_pool_refresh_percent", "status"]:
        value = getattr(data, field, None)
        if value is not None:
            setattr(round_obj, field, value)
    
    if data.use_of_funds is not None:
        round_obj.use_of_funds_json = data.use_of_funds
    
    round_obj.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(round_obj)
    
    return round_obj.to_dict()


@router.put("/companies/{company_id}/fundraising/rounds/{round_id}/terms")
def update_round_terms(
    company_id: int,
    round_id: str,
    data: TermsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    round_obj = db.query(FundraisingRound).filter(
        FundraisingRound.id == round_id,
        FundraisingRound.company_id == company_id
    ).first()
    
    if not round_obj:
        raise HTTPException(status_code=404, detail="Round not found")
    
    terms = db.query(RoundTerms).filter(RoundTerms.round_id == round_id).first()
    
    if not terms:
        terms = RoundTerms(round_id=round_obj.id, terms_json=data.terms)
        db.add(terms)
    else:
        terms.terms_json = data.terms
        terms.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(terms)
    
    return terms.to_dict()


@router.post("/companies/{company_id}/fundraising/simulate")
def simulate_fundraising(
    company_id: int,
    data: SimulateRoundRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    cap_table = db.query(CompanyCapTable).filter(
        CompanyCapTable.id == data.cap_table_id,
        CompanyCapTable.company_id == company_id
    ).first()
    
    if not cap_table:
        raise HTTPException(status_code=404, detail="Cap table not found")
    
    results = simulate_round_scenarios(
        cap_table.cap_table_json or {},
        data.rounds
    )
    
    return results


@router.get("/companies/{company_id}/investors")
def list_investors(
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
    
    investors = db.query(Investor).filter(
        Investor.company_id == company_id
    ).order_by(Investor.created_at.desc()).all()
    
    return {"investors": [i.to_dict() for i in investors]}


@router.post("/companies/{company_id}/investors")
def create_investor(
    company_id: int,
    data: InvestorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    investor = Investor(
        company_id=company_id,
        name=data.name,
        type=data.type,
        geography=data.geography,
        stage_focus=data.stage_focus,
        thesis_tags=data.thesis_tags or [],
        contact_json=data.contact or {}
    )
    db.add(investor)
    db.commit()
    db.refresh(investor)
    
    return investor.to_dict()


@router.post("/companies/{company_id}/fundraising/rounds/{round_id}/pipeline")
def add_to_pipeline(
    company_id: int,
    round_id: str,
    investor_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    round_obj = db.query(FundraisingRound).filter(
        FundraisingRound.id == round_id,
        FundraisingRound.company_id == company_id
    ).first()
    
    if not round_obj:
        raise HTTPException(status_code=404, detail="Round not found")
    
    investor = db.query(Investor).filter(
        Investor.id == investor_id,
        Investor.company_id == company_id
    ).first()
    
    if not investor:
        raise HTTPException(status_code=404, detail="Investor not found")
    
    existing = db.query(InvestorPipeline).filter(
        InvestorPipeline.round_id == round_id,
        InvestorPipeline.investor_id == investor_id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Investor already in pipeline")
    
    pipeline_entry = InvestorPipeline(
        round_id=round_obj.id,
        investor_id=investor.id
    )
    db.add(pipeline_entry)
    db.commit()
    db.refresh(pipeline_entry)
    
    return pipeline_entry.to_dict()


@router.patch("/companies/{company_id}/fundraising/pipeline/{pipeline_id}")
def update_pipeline_entry(
    company_id: int,
    pipeline_id: str,
    data: PipelineUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    pipeline_entry = db.query(InvestorPipeline).filter(
        InvestorPipeline.id == pipeline_id
    ).first()
    
    if not pipeline_entry:
        raise HTTPException(status_code=404, detail="Pipeline entry not found")
    
    round_obj = db.query(FundraisingRound).filter(
        FundraisingRound.id == pipeline_entry.round_id,
        FundraisingRound.company_id == company_id
    ).first()
    
    if not round_obj:
        raise HTTPException(status_code=404, detail="Round not found")
    
    if data.stage is not None:
        pipeline_entry.stage = data.stage
        pipeline_entry.last_contacted_at = datetime.utcnow()
    if data.probability is not None:
        pipeline_entry.probability = data.probability
    if data.notes is not None:
        pipeline_entry.notes = data.notes
    
    pipeline_entry.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(pipeline_entry)
    
    return pipeline_entry.to_dict()


@router.post("/companies/{company_id}/investor-room/generate")
def generate_investor_room(
    company_id: int,
    data: InvestorRoomRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    round_obj = db.query(FundraisingRound).filter(
        FundraisingRound.id == data.round_id,
        FundraisingRound.company_id == company_id
    ).first()
    
    if not round_obj:
        raise HTTPException(status_code=404, detail="Round not found")
    
    data_room_checklist = generate_data_room_checklist(company.stage, company.industry)
    
    investor_faq = generate_investor_faq(company, round_obj, data.mode)
    
    kpi_snapshot = generate_kpi_snapshot(company, db)
    
    return {
        "round_id": str(round_obj.id),
        "round_name": round_obj.name,
        "mode": data.mode,
        "investor_memo_markdown": generate_memo_template(company, round_obj),
        "data_room_checklist": data_room_checklist,
        "kpi_snapshot": kpi_snapshot,
        "investor_faq": investor_faq
    }


def generate_data_room_checklist(stage: Optional[str], industry: Optional[str]) -> Dict[str, Any]:
    """Generate a stage-aware data room checklist."""
    base_checklist = {
        "finance": [
            {"item": "Last 12 months P&L", "required": True, "completed": False},
            {"item": "Cash flow statement", "required": True, "completed": False},
            {"item": "Balance sheet", "required": True, "completed": False},
            {"item": "Bank statements (last 6 months)", "required": True, "completed": False},
            {"item": "AR/AP aging report", "required": False, "completed": False},
            {"item": "Revenue breakdown by customer/product", "required": True, "completed": False},
            {"item": "Financial projections (3-5 years)", "required": True, "completed": False},
        ],
        "legal": [
            {"item": "Certificate of incorporation", "required": True, "completed": False},
            {"item": "Articles of association", "required": True, "completed": False},
            {"item": "Cap table", "required": True, "completed": False},
            {"item": "Previous funding documents", "required": True, "completed": False},
            {"item": "Key customer contracts", "required": True, "completed": False},
            {"item": "IP assignments", "required": True, "completed": False},
            {"item": "Employment agreements", "required": False, "completed": False},
        ],
        "product_tech": [
            {"item": "Product roadmap", "required": True, "completed": False},
            {"item": "Technical architecture diagram", "required": False, "completed": False},
            {"item": "Security audit/SOC2", "required": False, "completed": False},
            {"item": "Uptime/SLA metrics", "required": False, "completed": False},
        ],
        "gtm": [
            {"item": "Sales pipeline report", "required": True, "completed": False},
            {"item": "Customer cohort analysis", "required": True, "completed": False},
            {"item": "Churn analysis", "required": True, "completed": False},
            {"item": "Marketing spend breakdown", "required": False, "completed": False},
            {"item": "Key customer references", "required": True, "completed": False},
        ],
        "hr": [
            {"item": "Org chart", "required": True, "completed": False},
            {"item": "ESOP plan", "required": True, "completed": False},
            {"item": "Key hire bios", "required": True, "completed": False},
        ]
    }
    
    if stage in ["series_a", "series_b", "growth"]:
        base_checklist["finance"].append(
            {"item": "Audited financials", "required": True, "completed": False}
        )
        base_checklist["product_tech"].append(
            {"item": "SOC 2 Type II certification", "required": True, "completed": False}
        )
    
    if industry and "saas" in industry.lower():
        base_checklist["gtm"].append(
            {"item": "MRR/ARR growth chart", "required": True, "completed": False}
        )
        base_checklist["gtm"].append(
            {"item": "NDR/GDR metrics", "required": True, "completed": False}
        )
    
    return base_checklist


def generate_investor_faq(company: Company, round_obj: FundraisingRound, mode: str) -> List[Dict[str, str]]:
    """Generate top investor questions with suggested answers."""
    faqs = [
        {
            "question": "What problem are you solving?",
            "suggested_answer": f"{company.name} addresses [key problem] in the {company.industry or 'technology'} space."
        },
        {
            "question": "What is your business model?",
            "suggested_answer": "We generate revenue through [primary revenue stream]."
        },
        {
            "question": "What are your key metrics?",
            "suggested_answer": "Our key metrics include [MRR/ARR], [customer count], and [growth rate]."
        },
        {
            "question": "Who are your competitors?",
            "suggested_answer": "Our main competitors include [competitor 1, 2, 3]. We differentiate through [key differentiator]."
        },
        {
            "question": "What is your go-to-market strategy?",
            "suggested_answer": "We acquire customers through [primary channels] with a CAC of [amount]."
        },
        {
            "question": "What is your current runway?",
            "suggested_answer": "With current burn of [amount]/month, we have [X] months of runway."
        },
        {
            "question": "How will you use the funds?",
            "suggested_answer": f"The ${round_obj.target_raise or 0:,.0f} raise will be allocated to [primary use cases]."
        },
        {
            "question": "What are the key risks?",
            "suggested_answer": "Key risks include [market, execution, or technical risks] which we mitigate through [strategies]."
        },
        {
            "question": "What is your team background?",
            "suggested_answer": "Our founding team has [X] years combined experience in [relevant domains]."
        },
        {
            "question": "What are your expansion plans?",
            "suggested_answer": "We plan to expand into [new markets/products] within [timeframe]."
        },
    ]
    
    if mode == "growth_pe":
        faqs.extend([
            {
                "question": "What are your path to profitability assumptions?",
                "suggested_answer": "We expect to reach profitability in [timeframe] through [key levers]."
            },
            {
                "question": "What is your EBITDA margin trajectory?",
                "suggested_answer": "Current EBITDA margin is [X]%, targeting [Y]% within [timeframe]."
            },
        ])
    
    return faqs


def generate_kpi_snapshot(company: Company, db: Session) -> Dict[str, Any]:
    """Generate a snapshot of key KPIs for investor presentations."""
    from server.models.financial import FinancialRecord
    
    latest_record = db.query(FinancialRecord).filter(
        FinancialRecord.company_id == company.id
    ).order_by(FinancialRecord.period_end.desc()).first()
    
    if latest_record:
        return {
            "mrr": latest_record.mrr or 0,
            "arr": latest_record.arr or 0,
            "gross_margin": latest_record.gross_margin,
            "runway_months": latest_record.runway_months,
            "headcount": latest_record.headcount,
            "customers": latest_record.customers,
            "mom_growth": latest_record.mom_growth,
            "ndr": latest_record.ndr,
            "ltv_cac_ratio": latest_record.ltv_cac_ratio,
            "as_of": latest_record.period_end.isoformat() if latest_record.period_end else None
        }
    
    return {
        "mrr": 0,
        "arr": 0,
        "gross_margin": None,
        "runway_months": None,
        "headcount": None,
        "customers": None,
        "mom_growth": None,
        "ndr": None,
        "ltv_cac_ratio": None,
        "as_of": None
    }


def generate_memo_template(company: Company, round_obj: FundraisingRound) -> str:
    """Generate a basic investor memo template."""
    return f"""# {company.name} - Investment Memo

## Executive Summary
{company.name} is raising ${round_obj.target_raise or 0:,.0f} in a {round_obj.name} round at a ${round_obj.pre_money or 0:,.0f} pre-money valuation.

## Company Overview
- **Industry**: {company.industry or 'Technology'}
- **Stage**: {company.stage or 'Early Stage'}
- **Website**: {company.website or 'N/A'}

## The Opportunity
[Describe the market opportunity and problem being solved]

## Solution
[Describe your product/service and its key differentiators]

## Traction
[Key metrics and milestones achieved]

## Business Model
[How you make money]

## Use of Funds
{_format_use_of_funds(round_obj.use_of_funds_json or {})}

## Team
[Key team members and their backgrounds]

## Financial Projections
[Summary of 3-year projections]

## Investment Terms
- **Round**: {round_obj.name}
- **Target Raise**: ${round_obj.target_raise or 0:,.0f}
- **Pre-Money Valuation**: ${round_obj.pre_money or 0:,.0f}
- **Instrument**: {round_obj.instrument.upper()}
"""


def _format_use_of_funds(use_of_funds: Dict[str, Any]) -> str:
    """Format use of funds dict into markdown."""
    if not use_of_funds:
        return "- To be specified"
    
    lines = []
    for category, amount in use_of_funds.items():
        if isinstance(amount, (int, float)):
            lines.append(f"- **{category}**: ${amount:,.0f}")
        else:
            lines.append(f"- **{category}**: {amount}")
    
    return "\n".join(lines) if lines else "- To be specified"
