from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from server.core.db import get_db
from server.core.security import get_current_user
from server.models.user import User
from server.models.company import Company

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
