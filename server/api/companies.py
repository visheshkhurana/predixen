from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from server.core.db import get_db
from server.core.security import get_current_user
from server.models.user import User
from server.models.company import Company
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

router = APIRouter(prefix="/companies", tags=["companies"])

class CompanyCreate(BaseModel):
    name: str
    website: Optional[str] = None
    industry: Optional[str] = None
    stage: Optional[str] = None
    currency: str = "USD"

class CompanyResponse(BaseModel):
    id: int
    name: str
    website: Optional[str]
    industry: Optional[str]
    stage: Optional[str]
    currency: str
    
    class Config:
        from_attributes = True

@router.post("", response_model=CompanyResponse)
def create_company(
    request: CompanyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    company = Company(
        user_id=current_user.id,
        name=request.name,
        website=request.website,
        industry=request.industry,
        stage=request.stage,
        currency=request.currency
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    return company

@router.get("", response_model=List[CompanyResponse])
def list_companies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    companies = db.query(Company).filter(Company.user_id == current_user.id).all()
    return companies

class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    stage: Optional[str] = None
    currency: Optional[str] = None


@router.get("/{company_id}", response_model=CompanyResponse)
def get_company(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
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
    current_user: User = Depends(get_current_user)
):
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
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
    
    db.commit()
    db.refresh(company)
    return company


@router.delete("/{company_id}")
def delete_company(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.user_id == current_user.id
    ).first()
    
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    # Delete all related records in proper order (children before parents)
    # Conversation related
    conversations = db.query(Conversation).filter(Conversation.company_id == company_id).all()
    for conv in conversations:
        db.query(ConversationRecommendation).filter(ConversationRecommendation.conversation_id == conv.id).delete()
        db.query(ConversationMessage).filter(ConversationMessage.conversation_id == conv.id).delete()
    db.query(Conversation).filter(Conversation.company_id == company_id).delete()
    
    # Scenario versions and related
    db.query(MacroEnvironment).filter(MacroEnvironment.company_id == company_id).delete()
    db.query(SensitivityRun).filter(SensitivityRun.company_id == company_id).delete()
    db.query(Recommendation).filter(Recommendation.company_id == company_id).delete()
    
    # Simulation cache (child of assumption_set)
    assumption_sets = db.query(AssumptionSetModel).filter(AssumptionSetModel.company_id == company_id).all()
    for a in assumption_sets:
        db.query(SimulationCache).filter(SimulationCache.assumption_set_id == a.id).delete()
    db.query(AssumptionSetModel).filter(AssumptionSetModel.company_id == company_id).delete()
    
    # Other related tables
    db.query(Scenario).filter(Scenario.company_id == company_id).delete()
    db.query(FinancialRecord).filter(FinancialRecord.company_id == company_id).delete()
    db.query(FinancialMetricPoint).filter(FinancialMetricPoint.company_id == company_id).delete()
    db.query(ImportSession).filter(ImportSession.company_id == company_id).delete()
    db.query(ChatMessage).filter(ChatMessage.company_id == company_id).delete()
    db.query(TruthScan).filter(TruthScan.company_id == company_id).delete()
    db.query(Dataset).filter(Dataset.company_id == company_id).delete()
    db.query(CustomerRecord).filter(CustomerRecord.company_id == company_id).delete()
    db.query(TransactionRecord).filter(TransactionRecord.company_id == company_id).delete()
    db.query(CompanyScenario).filter(CompanyScenario.company_id == company_id).delete()
    db.query(CompanyDecision).filter(CompanyDecision.company_id == company_id).delete()
    db.query(CompanySource).filter(CompanySource.company_id == company_id).delete()
    db.query(CompanyDriverModel).filter(CompanyDriverModel.company_id == company_id).delete()
    db.query(CompanyWorkstream).filter(CompanyWorkstream.company_id == company_id).delete()
    db.query(CompanyAlert).filter(CompanyAlert.company_id == company_id).delete()
    db.query(CompanyCapTable).filter(CompanyCapTable.company_id == company_id).delete()
    db.query(FundraisingRound).filter(FundraisingRound.company_id == company_id).delete()
    db.query(InvestorPipeline).filter(InvestorPipeline.company_id == company_id).delete()
    
    # Finally delete the company
    db.delete(company)
    db.commit()
    
    return {"message": "Company deleted successfully"}
