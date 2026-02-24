from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from server.core.db import get_db
from server.core.security import get_current_user, require_company_access, is_master_user
from server.core.pagination import paginate, create_paginated_response, PaginatedResponse
from server.models.user import User
from server.models.company import Company
from server.lib.web_search import search_company_info
from server.models.conversation import Conversation, ConversationMessage, ConversationRecommendation
from server.models.scenario import Scenario
from server.models.financial import FinancialRecord, FinancialMetricPoint, ImportSession
from server.models.chat import ChatMessage
from server.models.truth_scan import TruthScan
from server.models.dataset import Dataset
from server.models.customer import CustomerRecord
from server.models.transaction import TransactionRecord
from server.models.assumption_set import AssumptionSetModel, SimulationCache
from server.models.company_decision import CompanyDecision, CompanyScenario
from server.models.company_source import CompanySource, CompanyDriverModel, CompanyWorkstream, CompanyAlert
from server.models.fundraising import CompanyCapTable, FundraisingRound, InvestorPipeline
from server.models.scenario_version import MacroEnvironment, SensitivityRun, Recommendation
from server.models.company_state import CompanyState, compute_snapshot_id
import json
import logging

logger = logging.getLogger(__name__)


def _get_stage_sample_financials(stage: str = None) -> dict:
    """Return stage-appropriate sample financial data for new companies."""
    stage_defaults = {
        "pre_seed": {
            "cashBalance": 150000, "monthlyBurn": 12000, "revenueMonthly": 0,
            "revenueGrowthRate": 0, "expensesMonthly": 12000,
            "mrr": 0, "arr": 0, "arpu": 0, "customers": 0
        },
        "seed": {
            "cashBalance": 500000, "monthlyBurn": 25000, "revenueMonthly": 8000,
            "revenueGrowthRate": 12.0, "expensesMonthly": 33000,
            "mrr": 8000, "arr": 96000, "arpu": 100, "customers": 80
        },
        "series_a": {
            "cashBalance": 2000000, "monthlyBurn": 80000, "revenueMonthly": 60000,
            "revenueGrowthRate": 15.0, "expensesMonthly": 140000,
            "mrr": 60000, "arr": 720000, "arpu": 200, "customers": 300
        },
        "series_b": {
            "cashBalance": 8000000, "monthlyBurn": 250000, "revenueMonthly": 300000,
            "revenueGrowthRate": 10.0, "expensesMonthly": 550000,
            "mrr": 300000, "arr": 3600000, "arpu": 300, "customers": 1000
        },
    }
    return stage_defaults.get(stage, stage_defaults["seed"])


router = APIRouter(prefix="/companies", tags=["companies"])

async def require_company_access_by_path(
    company_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Resolve company access using the path `company_id` at request time."""
    dependency = require_company_access(company_id)
    return await dependency(current_user=current_user, db=db)

class CompanyCreate(BaseModel):
    name: str
    website: Optional[str] = None
    industry: Optional[str] = None
    stage: Optional[str] = None
    currency: str = "USD"
    amount_scale: str = "UNITS"

class CompanyResponse(BaseModel):
    id: int
    name: str
    website: Optional[str]
    industry: Optional[str]
    stage: Optional[str]
    currency: str
    amount_scale: str
    description: Optional[str] = None
    
    class Config:
        from_attributes = True

@router.post("", response_model=CompanyResponse)
def create_company(
    request: CompanyCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # MasterUser cannot create companies - they can only view and manage existing ones
    if is_master_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="MasterUser cannot create companies. Use a regular user account."
        )

    existing = db.query(Company).filter(
        Company.user_id == current_user.id,
        Company.name == request.name
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="A company with this name already exists")

    company = Company(
        user_id=current_user.id,
        name=request.name,
        website=request.website,
        industry=request.industry,
        stage=request.stage,
        currency=request.currency,
        amount_scale=request.amount_scale
    )
    db.add(company)
    db.flush()

    try:
        sample_data = _get_stage_sample_financials(request.stage)
        state = CompanyState(
            company_id=company.id,
            environment="user",
            state_json=json.dumps(sample_data),
            snapshot_id=compute_snapshot_id(sample_data),
            cash_balance=sample_data.get("cashBalance", 0),
            monthly_burn=sample_data.get("monthlyBurn", 0),
            revenue_monthly=sample_data.get("revenueMonthly", 0),
            revenue_growth_rate=str(sample_data.get("revenueGrowthRate", 0)),
            expenses_monthly=sample_data.get("expensesMonthly", 0)
        )
        db.add(state)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create CompanyState for company {company.id}: {e}")
        db.add(company)
        db.commit()

    db.refresh(company)
    return company

@router.get("")
def list_companies(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page (max 200)"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    List companies with pagination.

    - **page**: Page number (1-indexed, default=1)
    - **page_size**: Items per page (default=50, max=200)

    MasterUser can see all companies, regular users see only their own.
    """
    # Build query based on user type
    if is_master_user(current_user):
        query = db.query(Company)
        # Log MasterUser access for audit purposes
        from server.core.security import log_audit
        log_audit(
            db,
            user_id=current_user.id,
            action="master_user_list_companies",
            resource_type="company_list",
            details={"page": page, "page_size": page_size}
        )
    else:
        query = db.query(Company).filter(Company.user_id == current_user.id)

    # Order by created_at descending
    query = query.order_by(Company.created_at.desc())

    # Apply pagination
    items, total = paginate(query, page=page, page_size=page_size)

    # Convert to response models
    response_items = [CompanyResponse.from_orm(item) for item in items]

    return create_paginated_response(
        items=response_items,
        total=total,
        page=page,
        page_size=page_size
    )

class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    stage: Optional[str] = None
    currency: Optional[str] = None
    amount_scale: Optional[str] = None
    description: Optional[str] = None  # Business summary


@router.get("/{company_id}", response_model=CompanyResponse)
def get_company(
    company_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_company_access_by_path)
):
    # Authorization check already performed by require_company_access dependency
    # This includes audit logging for MasterUser access
    company = db.query(Company).filter(Company.id == company_id).first()

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )

    return company


@router.put("/{company_id}", response_model=CompanyResponse)
def update_company(
    company_id: int,
    request: CompanyUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(require_company_access_by_path)
):
    # Authorization check already performed by require_company_access dependency
    company = db.query(Company).filter(Company.id == company_id).first()

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )

    if request.name is not None:
        company.name = request.name
    if request.website is not None:
        company.website = request.website
    if request.industry is not None:
        company.industry = request.industry
    if request.stage is not None:
        company.stage = request.stage
    if request.currency is not None:
        company.currency = request.currency
    if request.description is not None:
        company.description = request.description
    if request.amount_scale is not None:
        company.amount_scale = request.amount_scale

    db.commit()
    db.refresh(company)
    return company


@router.delete("/{company_id}")
def delete_company(
    company_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_company_access_by_path)
):
    # Authorization check already performed by require_company_access dependency
    company = db.query(Company).filter(Company.id == company_id).first()

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    try:
        # Use explicit nested transaction to ensure atomic cascade delete
        db.begin_nested()

        # Conversation related
        conversations = db.query(Conversation).filter(Conversation.company_id == company_id).all()
        for conv in conversations:
            db.query(ConversationRecommendation).filter(ConversationRecommendation.conversation_id == conv.id).delete(synchronize_session='fetch')
            db.query(ConversationMessage).filter(ConversationMessage.conversation_id == conv.id).delete(synchronize_session='fetch')
        db.query(Conversation).filter(Conversation.company_id == company_id).delete(synchronize_session='fetch')

        # Scenario versions and related
        db.query(MacroEnvironment).filter(MacroEnvironment.company_id == company_id).delete(synchronize_session='fetch')
        db.query(SensitivityRun).filter(SensitivityRun.company_id == company_id).delete(synchronize_session='fetch')
        db.query(Recommendation).filter(Recommendation.company_id == company_id).delete(synchronize_session='fetch')

        # Simulation cache (child of assumption_set)
        assumption_sets = db.query(AssumptionSetModel).filter(AssumptionSetModel.company_id == company_id).all()
        for a in assumption_sets:
            db.query(SimulationCache).filter(SimulationCache.assumption_set_id == a.id).delete(synchronize_session='fetch')
        db.query(AssumptionSetModel).filter(AssumptionSetModel.company_id == company_id).delete(synchronize_session='fetch')

        # Company state
        db.query(CompanyState).filter(CompanyState.company_id == company_id).delete(synchronize_session='fetch')

        # Other related tables
        db.query(Scenario).filter(Scenario.company_id == company_id).delete(synchronize_session='fetch')
        db.query(FinancialRecord).filter(FinancialRecord.company_id == company_id).delete(synchronize_session='fetch')
        db.query(FinancialMetricPoint).filter(FinancialMetricPoint.company_id == company_id).delete(synchronize_session='fetch')
        db.query(ImportSession).filter(ImportSession.company_id == company_id).delete(synchronize_session='fetch')
        db.query(ChatMessage).filter(ChatMessage.company_id == company_id).delete(synchronize_session='fetch')
        db.query(TruthScan).filter(TruthScan.company_id == company_id).delete(synchronize_session='fetch')
        db.query(Dataset).filter(Dataset.company_id == company_id).delete(synchronize_session='fetch')
        db.query(CustomerRecord).filter(CustomerRecord.company_id == company_id).delete(synchronize_session='fetch')
        db.query(TransactionRecord).filter(TransactionRecord.company_id == company_id).delete(synchronize_session='fetch')
        db.query(CompanyScenario).filter(CompanyScenario.company_id == company_id).delete(synchronize_session='fetch')
        db.query(CompanyDecision).filter(CompanyDecision.company_id == company_id).delete(synchronize_session='fetch')
        db.query(CompanySource).filter(CompanySource.company_id == company_id).delete(synchronize_session='fetch')
        db.query(CompanyDriverModel).filter(CompanyDriverModel.company_id == company_id).delete(synchronize_session='fetch')
        db.query(CompanyWorkstream).filter(CompanyWorkstream.company_id == company_id).delete(synchronize_session='fetch')
        db.query(CompanyAlert).filter(CompanyAlert.company_id == company_id).delete(synchronize_session='fetch')
        db.query(CompanyCapTable).filter(CompanyCapTable.company_id == company_id).delete(synchronize_session='fetch')
        db.query(FundraisingRound).filter(FundraisingRound.company_id == company_id).delete(synchronize_session='fetch')
        db.query(InvestorPipeline).filter(InvestorPipeline.company_id == company_id).delete(synchronize_session='fetch')

        db.delete(company)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete company {company_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete company. No data was removed.")
    
    return {"message": "Company deleted successfully"}


@router.post("/{company_id}/seed-sample")
def seed_sample(
    company_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_company_access_by_path)
):
    # Authorization check already performed by require_company_access dependency
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    from server.services.sample_data import seed_sample_company
    result = seed_sample_company(db, company_id)
    from server.models.analytics_event import AnalyticsEvent
    from datetime import datetime
    event = AnalyticsEvent(event_name="sample_seed_success", company_id=company_id, user_id=current_user.id, meta_json={"template": "saas_series_a"}, created_at=datetime.utcnow())
    db.add(event)
    db.commit()
    return result


@router.post("/{company_id}/web-search", response_model=Dict[str, Any])
async def search_company_web_info(
    company_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_company_access_by_path)
):
    """Search the web for company information using AI."""
    # Authorization check already performed by require_company_access dependency
    company = db.query(Company).filter(Company.id == company_id).first()

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    result = await search_company_info(company.name, company.website)
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=result.get("error", "Web search failed")
        )
    
    return {
        "description": result.get("description"),
        "citations": result.get("citations", []),
        "company_id": company_id
    }
