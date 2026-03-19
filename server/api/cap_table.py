"""
Cap Table Management API - Carta-like equity management system.
Shareholders, equity holdings, option grants, vesting, transactions, 409A valuations,
convertible securities, scenarios, waterfall analysis, views, audit log, and export.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from uuid import UUID
import csv
import io
import json

from server.core.db import get_db
from server.core.security import get_current_user
from server.core.company_access import get_user_company
from server.models.user import User
from server.models.cap_table import (
    Shareholder, EquityHolding, OptionGrant,
    EquityTransaction, Valuation409A,
    ConvertibleSecurity, CapTableScenario, AuditLogEntry,
    ShareClass, GrantType, GrantStatus, TransactionType, VestingType,
    SecurityType, ConversionStatus, ScenarioType,
)

router = APIRouter(prefix="/companies/{company_id}/cap-table", tags=["cap-table"])


class ShareholderCreate(BaseModel):
    name: str
    email: Optional[str] = None
    type: str = "founder"
    relationship_type: Optional[str] = None
    tax_id: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None


class ShareholderUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    type: Optional[str] = None
    relationship_type: Optional[str] = None
    tax_id: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class EquityIssueRequest(BaseModel):
    shareholder_id: str
    share_class: str = "common"
    series: Optional[str] = None
    shares: float
    price_per_share: Optional[float] = None
    issue_date: Optional[date] = None
    board_approval_date: Optional[date] = None
    certificate_number: Optional[str] = None
    notes: Optional[str] = None


class EquityTransferRequest(BaseModel):
    from_shareholder_id: str
    to_shareholder_id: str
    holding_id: str
    shares: float
    price_per_share: Optional[float] = None
    effective_date: Optional[date] = None
    notes: Optional[str] = None


class OptionGrantCreate(BaseModel):
    shareholder_id: str
    grant_type: str = "iso"
    shares_granted: float
    exercise_price: float
    grant_date: Optional[date] = None
    expiration_date: Optional[date] = None
    vesting_type: str = "4y_1y_cliff"
    vesting_start_date: Optional[date] = None
    cliff_months: int = 12
    vesting_months: int = 48
    board_approval_date: Optional[date] = None
    notes: Optional[str] = None


class OptionExerciseRequest(BaseModel):
    shares_to_exercise: float
    effective_date: Optional[date] = None
    notes: Optional[str] = None


class Valuation409ACreate(BaseModel):
    valuation_date: date
    fair_market_value: float
    price_per_share: float
    methodology: Optional[str] = None
    provider: Optional[str] = None
    expiration_date: Optional[date] = None
    notes: Optional[str] = None


class DilutionModelRequest(BaseModel):
    pre_money: float
    raise_amount: float
    new_shares_percent: float = 0
    option_pool_refresh_percent: float = 0


class ConvertibleSecurityCreate(BaseModel):
    shareholder_id: Optional[str] = None
    type: str
    holder: str
    principal: float
    valuation_cap: Optional[float] = None
    discount_rate: Optional[float] = 0
    interest_rate: Optional[float] = 0
    maturity_date: Optional[date] = None
    issue_date: Optional[date] = None
    terms_json: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


class ConvertibleConvertRequest(BaseModel):
    pre_money_valuation: float
    price_per_share: Optional[float] = None
    notes: Optional[str] = None


class CapTableScenarioCreate(BaseModel):
    name: str
    description: Optional[str] = None
    scenario_type: str
    inputs_json: Optional[Dict[str, Any]] = None


class WaterfallRequest(BaseModel):
    exit_value: float


def _log_audit(db: Session, company_id: int, entity_type: str, entity_id: str, action: str, user_id: str, changes_json: Optional[Dict] = None):
    entry = AuditLogEntry(
        company_id=company_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        user_id=str(user_id),
        changes_json=changes_json,
    )
    db.add(entry)


# ─── Shareholders ───────────────────────────────────────────────────

@router.get("/shareholders")
def list_shareholders(
    company_id: int,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_user_company(db, company_id, current_user)
    query = db.query(Shareholder).filter(Shareholder.company_id == company_id)
    if not include_inactive:
        query = query.filter(Shareholder.is_active == True)
    shareholders = query.order_by(Shareholder.name).all()

    result = []
    for sh in shareholders:
        d = sh.to_dict()
        total_shares = sum(h.shares for h in sh.equity_holdings if h.company_id == company_id)
        total_options = sum(g.shares_granted for g in sh.option_grants if g.company_id == company_id and g.status == GrantStatus.ACTIVE.value)
        total_vested = sum(g.shares_vested for g in sh.option_grants if g.company_id == company_id and g.status == GrantStatus.ACTIVE.value)
        d["total_shares"] = total_shares
        d["total_options_granted"] = total_options
        d["total_options_vested"] = total_vested
        result.append(d)
    return {"shareholders": result}


@router.post("/shareholders")
def create_shareholder(
    company_id: int,
    data: ShareholderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_user_company(db, company_id, current_user)

    from sqlalchemy import or_, and_
    conditions = [Shareholder.name == data.name]
    if data.email and data.email.strip():
        conditions.append(
            and_(
                Shareholder.email == data.email,
                Shareholder.email != None,
                Shareholder.email != ""
            )
        )
    existing = db.query(Shareholder).filter(
        Shareholder.company_id == company_id,
        or_(*conditions)
    ).first()
    if existing:
        if existing.name == data.name:
            for field_name in ["email", "type", "relationship_type", "tax_id", "address", "notes"]:
                val = getattr(data, field_name, None)
                if val is not None and val != "":
                    setattr(existing, field_name, val)
            if not existing.is_active:
                existing.is_active = True
            db.commit()
            db.refresh(existing)
            return existing.to_dict()
        else:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=409,
                detail=f"A stakeholder with email '{data.email}' already exists: {existing.name}"
            )

    sh = Shareholder(
        company_id=company_id,
        name=data.name,
        email=data.email,
        type=data.type,
        relationship_type=data.relationship_type,
        tax_id=data.tax_id,
        address=data.address,
        notes=data.notes
    )
    db.add(sh)
    db.commit()
    db.refresh(sh)
    _log_audit(db, company_id, "shareholder", str(sh.id), "create", str(current_user.id), {"after": sh.to_dict()})
    db.commit()
    return sh.to_dict()


@router.patch("/shareholders/{shareholder_id}")
def update_shareholder(
    company_id: int,
    shareholder_id: str,
    data: ShareholderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_user_company(db, company_id, current_user)
    sh = db.query(Shareholder).filter(
        Shareholder.id == shareholder_id,
        Shareholder.company_id == company_id
    ).first()
    if not sh:
        raise HTTPException(status_code=404, detail="Shareholder not found")

    before = sh.to_dict()
    for field in ["name", "email", "type", "relationship_type", "notes", "is_active", "tax_id", "address"]:
        val = getattr(data, field, None)
        if val is not None:
            setattr(sh, field, val)

    sh.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(sh)
    _log_audit(db, company_id, "shareholder", shareholder_id, "update", str(current_user.id), {"before": before, "after": sh.to_dict()})
    db.commit()
    return sh.to_dict()


# ─── Equity Holdings ────────────────────────────────────────────────

@router.get("/holdings")
def list_holdings(
    company_id: int,
    shareholder_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_user_company(db, company_id, current_user)
    query = db.query(EquityHolding).filter(EquityHolding.company_id == company_id)
    if shareholder_id:
        query = query.filter(EquityHolding.shareholder_id == shareholder_id)
    holdings = query.options(joinedload(EquityHolding.shareholder)).all()
    return {"holdings": [h.to_dict() for h in holdings]}


@router.post("/issue")
def issue_equity(
    company_id: int,
    data: EquityIssueRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_user_company(db, company_id, current_user)

    if data.shares <= 0:
        raise HTTPException(status_code=400, detail="Shares must be positive")
    if data.share_class not in ("common", "preferred"):
        raise HTTPException(status_code=400, detail="Share class must be 'common' or 'preferred'")
    if data.price_per_share is not None and data.price_per_share < 0:
        raise HTTPException(status_code=400, detail="Price per share cannot be negative")

    sh = db.query(Shareholder).filter(
        Shareholder.id == data.shareholder_id,
        Shareholder.company_id == company_id
    ).first()
    if not sh:
        raise HTTPException(status_code=404, detail="Shareholder not found")

    holding = EquityHolding(
        company_id=company_id,
        shareholder_id=sh.id,
        share_class=data.share_class,
        series=data.series,
        shares=data.shares,
        price_per_share=data.price_per_share,
        issue_date=data.issue_date or date.today(),
        board_approval_date=data.board_approval_date,
        certificate_number=data.certificate_number,
        notes=data.notes,
    )
    db.add(holding)

    tx = EquityTransaction(
        company_id=company_id,
        transaction_type=TransactionType.ISSUANCE.value,
        to_shareholder_id=sh.id,
        share_class=data.share_class,
        series=data.series,
        shares=data.shares,
        price_per_share=data.price_per_share,
        total_value=(data.shares * data.price_per_share) if data.price_per_share else None,
        effective_date=data.issue_date or date.today(),
        board_approval_date=data.board_approval_date,
        notes=data.notes,
    )
    db.add(tx)
    db.commit()
    db.refresh(holding)
    _log_audit(db, company_id, "equity_holding", str(holding.id), "issue", str(current_user.id), {"after": holding.to_dict()})
    db.commit()
    return holding.to_dict()


@router.post("/transfer")
def transfer_equity(
    company_id: int,
    data: EquityTransferRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_user_company(db, company_id, current_user)

    if data.shares <= 0:
        raise HTTPException(status_code=400, detail="Shares must be positive")

    holding = db.query(EquityHolding).filter(
        EquityHolding.id == data.holding_id,
        EquityHolding.company_id == company_id,
        EquityHolding.shareholder_id == data.from_shareholder_id
    ).first()
    if not holding:
        raise HTTPException(status_code=404, detail="Holding not found")

    if holding.shares < data.shares:
        raise HTTPException(status_code=400, detail=f"Insufficient shares. Available: {holding.shares}")

    to_sh = db.query(Shareholder).filter(
        Shareholder.id == data.to_shareholder_id,
        Shareholder.company_id == company_id
    ).first()
    if not to_sh:
        raise HTTPException(status_code=404, detail="Destination shareholder not found")

    holding.shares -= data.shares
    holding.updated_at = datetime.utcnow()

    new_holding = EquityHolding(
        company_id=company_id,
        shareholder_id=to_sh.id,
        share_class=holding.share_class,
        series=holding.series,
        shares=data.shares,
        price_per_share=data.price_per_share or holding.price_per_share,
        issue_date=data.effective_date or date.today(),
        notes=data.notes,
    )
    db.add(new_holding)

    tx = EquityTransaction(
        company_id=company_id,
        transaction_type=TransactionType.TRANSFER.value,
        from_shareholder_id=holding.shareholder_id,
        to_shareholder_id=to_sh.id,
        share_class=holding.share_class,
        series=holding.series,
        shares=data.shares,
        price_per_share=data.price_per_share,
        total_value=(data.shares * data.price_per_share) if data.price_per_share else None,
        holding_id=holding.id,
        effective_date=data.effective_date or date.today(),
        notes=data.notes,
    )
    db.add(tx)
    db.commit()

    if holding.shares == 0:
        db.delete(holding)
        db.commit()

    db.refresh(new_holding)
    _log_audit(db, company_id, "equity_holding", str(new_holding.id), "transfer", str(current_user.id), {"shares": data.shares, "from": data.from_shareholder_id, "to": data.to_shareholder_id})
    db.commit()
    return new_holding.to_dict()


# ─── Option Grants ──────────────────────────────────────────────────

@router.get("/grants")
def list_grants(
    company_id: int,
    shareholder_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_user_company(db, company_id, current_user)
    query = db.query(OptionGrant).filter(OptionGrant.company_id == company_id)
    if shareholder_id:
        query = query.filter(OptionGrant.shareholder_id == shareholder_id)
    if status:
        query = query.filter(OptionGrant.status == status)
    grants = query.options(joinedload(OptionGrant.shareholder)).order_by(OptionGrant.grant_date.desc()).all()
    return {"grants": [g.to_dict() for g in grants]}


@router.post("/grants")
def create_grant(
    company_id: int,
    data: OptionGrantCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_user_company(db, company_id, current_user)

    if data.shares_granted <= 0:
        raise HTTPException(status_code=400, detail="Shares must be positive")
    if data.exercise_price < 0:
        raise HTTPException(status_code=400, detail="Exercise price cannot be negative")
    valid_grant_types = {gt.value for gt in GrantType}
    if data.grant_type not in valid_grant_types:
        raise HTTPException(status_code=400, detail=f"Grant type must be one of: {', '.join(valid_grant_types)}")
    valid_vesting_types = {vt.value for vt in VestingType}
    if data.vesting_type not in valid_vesting_types:
        raise HTTPException(status_code=400, detail=f"Vesting type must be one of: {', '.join(valid_vesting_types)}")

    sh = db.query(Shareholder).filter(
        Shareholder.id == data.shareholder_id,
        Shareholder.company_id == company_id
    ).first()
    if not sh:
        raise HTTPException(status_code=404, detail="Shareholder not found")

    grant = OptionGrant(
        company_id=company_id,
        shareholder_id=sh.id,
        grant_type=data.grant_type,
        shares_granted=data.shares_granted,
        exercise_price=data.exercise_price,
        grant_date=data.grant_date or date.today(),
        expiration_date=data.expiration_date,
        vesting_type=data.vesting_type,
        vesting_start_date=data.vesting_start_date or data.grant_date or date.today(),
        cliff_months=data.cliff_months,
        vesting_months=data.vesting_months,
        board_approval_date=data.board_approval_date,
        notes=data.notes,
        status=GrantStatus.ACTIVE.value,
    )
    db.add(grant)
    db.commit()
    db.refresh(grant)

    _update_vesting(grant, db)
    _log_audit(db, company_id, "option_grant", str(grant.id), "create", str(current_user.id), {"after": grant.to_dict()})
    db.commit()
    return grant.to_dict()


@router.get("/grants/{grant_id}")
def get_grant(
    company_id: int,
    grant_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_user_company(db, company_id, current_user)
    grant = db.query(OptionGrant).filter(
        OptionGrant.id == grant_id,
        OptionGrant.company_id == company_id
    ).options(joinedload(OptionGrant.shareholder)).first()
    if not grant:
        raise HTTPException(status_code=404, detail="Grant not found")

    _update_vesting(grant, db)
    result = grant.to_dict()
    result["vesting_schedule"] = _compute_vesting_schedule(grant)
    return result


@router.post("/grants/{grant_id}/exercise")
def exercise_options(
    company_id: int,
    grant_id: str,
    data: OptionExerciseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_user_company(db, company_id, current_user)

    grant = db.query(OptionGrant).filter(
        OptionGrant.id == grant_id,
        OptionGrant.company_id == company_id,
        OptionGrant.status == GrantStatus.ACTIVE.value
    ).first()
    if not grant:
        raise HTTPException(status_code=404, detail="Active grant not found")

    _update_vesting(grant, db)
    exercisable = grant.shares_vested - grant.shares_exercised
    if data.shares_to_exercise > exercisable:
        raise HTTPException(status_code=400, detail=f"Only {exercisable} shares exercisable")
    if data.shares_to_exercise <= 0:
        raise HTTPException(status_code=400, detail="Shares to exercise must be positive")

    before = grant.to_dict()
    grant.shares_exercised += data.shares_to_exercise
    grant.updated_at = datetime.utcnow()

    if grant.shares_exercised >= grant.shares_granted:
        grant.status = GrantStatus.EXERCISED.value

    holding = EquityHolding(
        company_id=company_id,
        shareholder_id=grant.shareholder_id,
        share_class=ShareClass.COMMON.value,
        shares=data.shares_to_exercise,
        price_per_share=grant.exercise_price,
        issue_date=data.effective_date or date.today(),
        notes=f"Exercise of {grant.grant_type.upper()} grant",
    )
    db.add(holding)

    tx = EquityTransaction(
        company_id=company_id,
        transaction_type=TransactionType.EXERCISE.value,
        to_shareholder_id=grant.shareholder_id,
        share_class=ShareClass.COMMON.value,
        shares=data.shares_to_exercise,
        price_per_share=grant.exercise_price,
        total_value=data.shares_to_exercise * grant.exercise_price,
        grant_id=grant.id,
        effective_date=data.effective_date or date.today(),
        notes=data.notes,
    )
    db.add(tx)
    db.commit()
    db.refresh(grant)
    _log_audit(db, company_id, "option_grant", grant_id, "exercise", str(current_user.id), {"before": before, "after": grant.to_dict()})
    db.commit()
    return grant.to_dict()


@router.post("/grants/{grant_id}/cancel")
def cancel_grant(
    company_id: int,
    grant_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_user_company(db, company_id, current_user)
    grant = db.query(OptionGrant).filter(
        OptionGrant.id == grant_id,
        OptionGrant.company_id == company_id
    ).first()
    if not grant:
        raise HTTPException(status_code=404, detail="Grant not found")

    before = grant.to_dict()
    grant.status = GrantStatus.CANCELLED.value
    grant.updated_at = datetime.utcnow()

    tx = EquityTransaction(
        company_id=company_id,
        transaction_type=TransactionType.CANCELLATION.value,
        from_shareholder_id=grant.shareholder_id,
        shares=grant.shares_granted - grant.shares_exercised,
        grant_id=grant.id,
        effective_date=date.today(),
        notes="Grant cancelled",
    )
    db.add(tx)
    db.commit()
    db.refresh(grant)
    _log_audit(db, company_id, "option_grant", grant_id, "cancel", str(current_user.id), {"before": before, "after": grant.to_dict()})
    db.commit()
    return grant.to_dict()


# ─── Convertible Securities (SAFEs, Notes, Warrants) ────────────────

@router.get("/convertibles")
def list_convertibles(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_user_company(db, company_id, current_user)
    convertibles = db.query(ConvertibleSecurity).filter(
        ConvertibleSecurity.company_id == company_id
    ).options(joinedload(ConvertibleSecurity.shareholder)).order_by(ConvertibleSecurity.created_at.desc()).all()
    return {"convertibles": [c.to_dict() for c in convertibles]}


@router.post("/convertibles")
def create_convertible(
    company_id: int,
    data: ConvertibleSecurityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_user_company(db, company_id, current_user)

    valid_types = {st.value for st in SecurityType if st.value not in ("common", "preferred")}
    if data.type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Type must be one of: {', '.join(valid_types)}")
    if data.principal <= 0:
        raise HTTPException(status_code=400, detail="Principal must be positive")

    if data.shareholder_id:
        sh = db.query(Shareholder).filter(
            Shareholder.id == data.shareholder_id,
            Shareholder.company_id == company_id
        ).first()
        if not sh:
            raise HTTPException(status_code=404, detail="Shareholder not found")
    else:
        sh = db.query(Shareholder).filter(
            Shareholder.company_id == company_id,
            Shareholder.name == data.holder
        ).first()
        if not sh:
            sh = Shareholder(
                company_id=company_id,
                name=data.holder,
                type="investor",
                is_active=True,
            )
            db.add(sh)
            db.flush()

    conv = ConvertibleSecurity(
        company_id=company_id,
        shareholder_id=sh.id,
        type=data.type,
        holder=data.holder,
        principal=data.principal,
        valuation_cap=data.valuation_cap,
        discount_rate=data.discount_rate or 0,
        interest_rate=data.interest_rate or 0,
        maturity_date=data.maturity_date,
        issue_date=data.issue_date or date.today(),
        terms_json=data.terms_json,
        notes=data.notes,
        conversion_status=ConversionStatus.OUTSTANDING.value,
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    _log_audit(db, company_id, "convertible_security", str(conv.id), "create", str(current_user.id), {"after": conv.to_dict()})
    db.commit()
    return conv.to_dict()


@router.post("/convertibles/{conv_id}/convert")
def convert_convertible(
    company_id: int,
    conv_id: str,
    data: ConvertibleConvertRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_user_company(db, company_id, current_user)

    conv = db.query(ConvertibleSecurity).filter(
        ConvertibleSecurity.id == conv_id,
        ConvertibleSecurity.company_id == company_id
    ).options(joinedload(ConvertibleSecurity.shareholder)).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Convertible security not found")
    if conv.conversion_status != ConversionStatus.OUTSTANDING.value:
        raise HTTPException(status_code=400, detail=f"Cannot convert: status is {conv.conversion_status}")

    before = conv.to_dict()

    holdings = db.query(EquityHolding).filter(EquityHolding.company_id == company_id).all()
    grants = db.query(OptionGrant).filter(
        OptionGrant.company_id == company_id,
        OptionGrant.status == GrantStatus.ACTIVE.value
    ).all()
    total_shares = sum(h.shares for h in holdings)
    total_options = sum(g.shares_granted - g.shares_exercised for g in grants)
    current_fd = total_shares + total_options
    if current_fd == 0:
        current_fd = 10000000

    accrued_interest = 0
    if conv.interest_rate and conv.interest_rate > 0 and conv.issue_date:
        days_outstanding = (date.today() - conv.issue_date).days
        accrued_interest = conv.principal * (conv.interest_rate / 100) * (days_outstanding / 365)
    total_converting = conv.principal + accrued_interest

    round_pps = data.pre_money_valuation / current_fd if current_fd > 0 else 0

    discount_pps = round_pps * (1 - (conv.discount_rate or 0) / 100) if round_pps > 0 else 0
    cap_pps = (conv.valuation_cap / current_fd) if conv.valuation_cap and conv.valuation_cap > 0 else None

    if cap_pps is not None and discount_pps > 0:
        conversion_pps = min(cap_pps, discount_pps)
    elif cap_pps is not None:
        conversion_pps = cap_pps
    elif discount_pps > 0:
        conversion_pps = discount_pps
    else:
        conversion_pps = round_pps

    if data.price_per_share is not None and data.price_per_share > 0:
        conversion_pps = data.price_per_share

    if conversion_pps <= 0:
        raise HTTPException(status_code=400, detail="Cannot determine conversion price")

    shares_issued = total_converting / conversion_pps

    holding = EquityHolding(
        company_id=company_id,
        shareholder_id=conv.shareholder_id,
        share_class=ShareClass.PREFERRED.value,
        series=f"Converted {conv.type.upper()}",
        shares=round(shares_issued, 2),
        price_per_share=round(conversion_pps, 4),
        issue_date=date.today(),
        notes=f"Conversion of {conv.type}: {conv.holder}",
    )
    db.add(holding)

    tx = EquityTransaction(
        company_id=company_id,
        transaction_type=TransactionType.CONVERSION.value,
        to_shareholder_id=conv.shareholder_id,
        share_class=ShareClass.PREFERRED.value,
        series=f"Converted {conv.type.upper()}",
        shares=round(shares_issued, 2),
        price_per_share=round(conversion_pps, 4),
        total_value=round(total_converting, 2),
        effective_date=date.today(),
        notes=f"Conversion of {conv.type} ({conv.holder})",
    )
    db.add(tx)

    db.commit()
    db.refresh(holding)

    conv.conversion_status = ConversionStatus.CONVERTED.value
    conv.converted_to_holding_id = holding.id
    conv.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(conv)

    _log_audit(db, company_id, "convertible_security", conv_id, "convert", str(current_user.id), {"before": before, "after": conv.to_dict(), "shares_issued": round(shares_issued, 2), "conversion_pps": round(conversion_pps, 4)})
    db.commit()

    return {
        "convertible": conv.to_dict(),
        "holding": holding.to_dict(),
        "shares_issued": round(shares_issued, 2),
        "conversion_price": round(conversion_pps, 4),
        "total_converting": round(total_converting, 2),
        "accrued_interest": round(accrued_interest, 2),
    }


# ─── Ownership Views ────────────────────────────────────────────────

@router.get("/views/fully-diluted")
def view_fully_diluted(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_user_company(db, company_id, current_user)
    return _build_ownership_view(db, company_id, view_type="fully_diluted")


@router.get("/views/by-class")
def view_by_class(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_user_company(db, company_id, current_user)

    holdings = db.query(EquityHolding).filter(
        EquityHolding.company_id == company_id
    ).options(joinedload(EquityHolding.shareholder)).all()

    grants = db.query(OptionGrant).filter(
        OptionGrant.company_id == company_id,
        OptionGrant.status == GrantStatus.ACTIVE.value
    ).all()

    classes = {}
    for h in holdings:
        key = h.share_class or "common"
        if h.series:
            key = f"{h.share_class}_{h.series}"
        if key not in classes:
            classes[key] = {"share_class": h.share_class, "series": h.series, "total_shares": 0, "holders": []}
        classes[key]["total_shares"] += h.shares
        classes[key]["holders"].append({
            "shareholder_id": str(h.shareholder_id),
            "name": h.shareholder.name if h.shareholder else "Unknown",
            "shares": h.shares,
        })

    total_options_outstanding = sum(g.shares_granted - g.shares_exercised for g in grants)
    if total_options_outstanding > 0:
        classes["options"] = {
            "share_class": "options",
            "series": None,
            "total_shares": total_options_outstanding,
            "holders": [],
        }

    total_all = sum(c["total_shares"] for c in classes.values())
    for key, c in classes.items():
        c["percent"] = round((c["total_shares"] / total_all * 100), 2) if total_all > 0 else 0

    return {"classes": list(classes.values()), "total_shares": total_all}


@router.get("/views/as-converted")
def view_as_converted(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_user_company(db, company_id, current_user)

    holdings = db.query(EquityHolding).filter(
        EquityHolding.company_id == company_id
    ).options(joinedload(EquityHolding.shareholder)).all()

    holder_map = {}
    for h in holdings:
        sid = str(h.shareholder_id)
        if sid not in holder_map:
            holder_map[sid] = {
                "shareholder_id": sid,
                "name": h.shareholder.name if h.shareholder else "Unknown",
                "type": h.shareholder.type if h.shareholder else "unknown",
                "original_common": 0,
                "original_preferred": 0,
                "converted_shares": 0,
            }
        conversion_ratio = 1.0
        converted = h.shares * conversion_ratio
        holder_map[sid]["converted_shares"] += converted
        if h.share_class == ShareClass.COMMON.value:
            holder_map[sid]["original_common"] += h.shares
        else:
            holder_map[sid]["original_preferred"] += h.shares

    total = sum(v["converted_shares"] for v in holder_map.values())
    result = []
    for v in holder_map.values():
        v["percent"] = round((v["converted_shares"] / total * 100), 2) if total > 0 else 0
        result.append(v)

    result.sort(key=lambda x: x["percent"], reverse=True)
    return {"as_converted": result, "total_as_converted_shares": total}


@router.get("/views/as-exercised")
def view_as_exercised(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_user_company(db, company_id, current_user)

    holdings = db.query(EquityHolding).filter(
        EquityHolding.company_id == company_id
    ).options(joinedload(EquityHolding.shareholder)).all()

    grants = db.query(OptionGrant).filter(
        OptionGrant.company_id == company_id,
        OptionGrant.status == GrantStatus.ACTIVE.value
    ).options(joinedload(OptionGrant.shareholder)).all()

    for g in grants:
        _update_vesting(g, db)

    holder_map = {}
    for h in holdings:
        sid = str(h.shareholder_id)
        if sid not in holder_map:
            holder_map[sid] = {
                "shareholder_id": sid,
                "name": h.shareholder.name if h.shareholder else "Unknown",
                "equity_shares": 0,
                "exercisable_options": 0,
                "total_shares": 0,
            }
        holder_map[sid]["equity_shares"] += h.shares

    for g in grants:
        sid = str(g.shareholder_id)
        if sid not in holder_map:
            holder_map[sid] = {
                "shareholder_id": sid,
                "name": g.shareholder.name if g.shareholder else "Unknown",
                "equity_shares": 0,
                "exercisable_options": 0,
                "total_shares": 0,
            }
        exercisable = max(0, g.shares_vested - g.shares_exercised)
        holder_map[sid]["exercisable_options"] += exercisable

    for v in holder_map.values():
        v["total_shares"] = v["equity_shares"] + v["exercisable_options"]

    total = sum(v["total_shares"] for v in holder_map.values())
    result = []
    for v in holder_map.values():
        v["percent"] = round((v["total_shares"] / total * 100), 2) if total > 0 else 0
        result.append(v)

    result.sort(key=lambda x: x["percent"], reverse=True)
    return {"as_exercised": result, "total_as_exercised_shares": total}


# ─── Scenarios ───────────────────────────────────────────────────────

@router.get("/scenarios")
def list_scenarios(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_user_company(db, company_id, current_user)
    scenarios = db.query(CapTableScenario).filter(
        CapTableScenario.company_id == company_id
    ).order_by(CapTableScenario.created_at.desc()).all()
    return {"scenarios": [s.to_dict() for s in scenarios]}


@router.post("/scenarios")
def create_scenario(
    company_id: int,
    data: CapTableScenarioCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_user_company(db, company_id, current_user)

    valid_types = {st.value for st in ScenarioType}
    if data.scenario_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Scenario type must be one of: {', '.join(valid_types)}")

    results_json = None
    inputs = data.inputs_json or {}

    if data.scenario_type == ScenarioType.NEW_ROUND.value:
        pre_money = inputs.get("pre_money", 0)
        raise_amount = inputs.get("raise_amount", 0)
        option_pool = inputs.get("option_pool_refresh_percent", 0)
        if pre_money > 0 and raise_amount > 0:
            results_json = _compute_dilution_scenario(db, company_id, pre_money, raise_amount, option_pool)

    elif data.scenario_type == ScenarioType.EXIT_WATERFALL.value:
        exit_value = inputs.get("exit_value", 0)
        if exit_value > 0:
            results_json = _compute_waterfall_scenario(db, company_id, exit_value)

    elif data.scenario_type == ScenarioType.OPTION_POOL.value:
        pool_percent = inputs.get("pool_percent", 0)
        if pool_percent > 0:
            results_json = {"pool_percent": pool_percent, "note": "Option pool expansion scenario"}

    scenario = CapTableScenario(
        company_id=company_id,
        name=data.name,
        description=data.description,
        scenario_type=data.scenario_type,
        inputs_json=inputs,
        results_json=results_json,
    )
    db.add(scenario)
    db.commit()
    db.refresh(scenario)
    _log_audit(db, company_id, "cap_table_scenario", str(scenario.id), "create", str(current_user.id), {"after": scenario.to_dict()})
    db.commit()
    return scenario.to_dict()


@router.get("/scenarios/{scenario_id}")
def get_scenario(
    company_id: int,
    scenario_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_user_company(db, company_id, current_user)
    scenario = db.query(CapTableScenario).filter(
        CapTableScenario.id == scenario_id,
        CapTableScenario.company_id == company_id
    ).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario.to_dict()


@router.delete("/scenarios/{scenario_id}")
def delete_scenario(
    company_id: int,
    scenario_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_user_company(db, company_id, current_user)
    scenario = db.query(CapTableScenario).filter(
        CapTableScenario.id == scenario_id,
        CapTableScenario.company_id == company_id
    ).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    _log_audit(db, company_id, "cap_table_scenario", scenario_id, "delete", str(current_user.id), {"before": scenario.to_dict()})
    db.delete(scenario)
    db.commit()
    return {"status": "deleted", "id": scenario_id}


# ─── Waterfall Analysis ─────────────────────────────────────────────

@router.post("/waterfall")
def run_waterfall(
    company_id: int,
    data: WaterfallRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_user_company(db, company_id, current_user)

    if data.exit_value <= 0:
        raise HTTPException(status_code=400, detail="Exit value must be positive")

    result = _compute_waterfall_scenario(db, company_id, data.exit_value)
    return result


# ─── Transactions (Audit Log) ───────────────────────────────────────

@router.get("/transactions")
def list_transactions(
    company_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    transaction_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_user_company(db, company_id, current_user)
    query = db.query(EquityTransaction).filter(EquityTransaction.company_id == company_id)
    if transaction_type:
        query = query.filter(EquityTransaction.transaction_type == transaction_type)

    total = query.count()
    transactions = (
        query
        .options(
            joinedload(EquityTransaction.from_shareholder),
            joinedload(EquityTransaction.to_shareholder)
        )
        .order_by(EquityTransaction.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "transactions": [t.to_dict() for t in transactions],
        "total": total,
        "page": page,
        "page_size": page_size
    }


# ─── 409A Valuations ────────────────────────────────────────────────

@router.get("/valuations")
def list_valuations(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_user_company(db, company_id, current_user)
    vals = db.query(Valuation409A).filter(
        Valuation409A.company_id == company_id
    ).order_by(Valuation409A.valuation_date.desc()).all()
    return {"valuations": [v.to_dict() for v in vals]}


@router.post("/valuations")
def create_valuation(
    company_id: int,
    data: Valuation409ACreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_user_company(db, company_id, current_user)

    db.query(Valuation409A).filter(
        Valuation409A.company_id == company_id,
        Valuation409A.status == "active"
    ).update({"status": "superseded"})

    val = Valuation409A(
        company_id=company_id,
        valuation_date=data.valuation_date,
        fair_market_value=data.fair_market_value,
        price_per_share=data.price_per_share,
        methodology=data.methodology,
        provider=data.provider,
        expiration_date=data.expiration_date,
        notes=data.notes,
    )
    db.add(val)
    db.commit()
    db.refresh(val)
    _log_audit(db, company_id, "valuation_409a", str(val.id), "create", str(current_user.id), {"after": val.to_dict()})
    db.commit()
    return val.to_dict()


# ─── Summary & Ownership ────────────────────────────────────────────

@router.get("/summary")
def cap_table_summary(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_user_company(db, company_id, current_user)

    holdings = db.query(EquityHolding).filter(
        EquityHolding.company_id == company_id
    ).options(joinedload(EquityHolding.shareholder)).all()

    grants = db.query(OptionGrant).filter(
        OptionGrant.company_id == company_id,
        OptionGrant.status == GrantStatus.ACTIVE.value
    ).options(joinedload(OptionGrant.shareholder)).all()

    for g in grants:
        _update_vesting(g, db)

    total_shares_issued = sum(h.shares for h in holdings)
    total_options_granted = sum(g.shares_granted for g in grants)
    total_options_vested = sum(g.shares_vested for g in grants)
    total_options_exercised = sum(g.shares_exercised for g in grants)
    total_options_unvested = total_options_granted - total_options_vested
    fully_diluted = total_shares_issued + total_options_granted - total_options_exercised

    ownership = {}
    for h in holdings:
        sid = str(h.shareholder_id)
        if sid not in ownership:
            ownership[sid] = {
                "shareholder_id": sid,
                "name": h.shareholder.name if h.shareholder else "Unknown",
                "type": h.shareholder.type if h.shareholder else "unknown",
                "common_shares": 0,
                "preferred_shares": 0,
                "options_granted": 0,
                "options_vested": 0,
                "options_exercised": 0,
            }
        if h.share_class == ShareClass.COMMON.value:
            ownership[sid]["common_shares"] += h.shares
        else:
            ownership[sid]["preferred_shares"] += h.shares

    for g in grants:
        sid = str(g.shareholder_id)
        if sid not in ownership:
            ownership[sid] = {
                "shareholder_id": sid,
                "name": g.shareholder.name if g.shareholder else "Unknown",
                "type": g.shareholder.type if g.shareholder else "unknown",
                "common_shares": 0,
                "preferred_shares": 0,
                "options_granted": 0,
                "options_vested": 0,
                "options_exercised": 0,
            }
        ownership[sid]["options_granted"] += g.shares_granted
        ownership[sid]["options_vested"] += g.shares_vested
        ownership[sid]["options_exercised"] += g.shares_exercised

    ownership_list = []
    for sid, data in ownership.items():
        total = data["common_shares"] + data["preferred_shares"] + data["options_granted"] - data["options_exercised"]
        data["total_fully_diluted"] = total
        data["ownership_percent"] = round((total / fully_diluted * 100), 2) if fully_diluted > 0 else 0
        ownership_list.append(data)

    ownership_list.sort(key=lambda x: x["ownership_percent"], reverse=True)

    latest_409a = db.query(Valuation409A).filter(
        Valuation409A.company_id == company_id,
        Valuation409A.status == "active"
    ).first()

    return {
        "total_shares_issued": total_shares_issued,
        "total_options_granted": total_options_granted,
        "total_options_vested": total_options_vested,
        "total_options_exercised": total_options_exercised,
        "total_options_unvested": total_options_unvested,
        "fully_diluted_shares": fully_diluted,
        "ownership": ownership_list,
        "latest_409a": latest_409a.to_dict() if latest_409a else None,
    }


@router.post("/model-dilution")
def model_dilution(
    company_id: int,
    data: DilutionModelRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_user_company(db, company_id, current_user)

    holdings = db.query(EquityHolding).filter(EquityHolding.company_id == company_id).all()
    grants = db.query(OptionGrant).filter(
        OptionGrant.company_id == company_id,
        OptionGrant.status == GrantStatus.ACTIVE.value
    ).all()

    total_shares = sum(h.shares for h in holdings)
    total_options = sum(g.shares_granted - g.shares_exercised for g in grants)
    current_fd = total_shares + total_options

    if current_fd == 0:
        raise HTTPException(status_code=400, detail="No shares issued yet. Add shareholders and issue equity first.")

    post_money = data.pre_money + data.raise_amount
    new_investor_percent = (data.raise_amount / post_money) * 100

    pool_shares = 0
    if data.option_pool_refresh_percent > 0:
        pool_shares = int(current_fd * data.option_pool_refresh_percent / (100 - data.option_pool_refresh_percent))

    price_per_share = data.pre_money / current_fd
    new_investor_shares = int(data.raise_amount / price_per_share) if price_per_share > 0 else 0
    new_fd = current_fd + new_investor_shares + pool_shares

    before_ownership = []
    after_ownership = []

    shareholder_shares = {}
    for h in holdings:
        sid = str(h.shareholder_id)
        shareholder_shares[sid] = shareholder_shares.get(sid, 0) + h.shares

    for sid, shares in shareholder_shares.items():
        pct_before = (shares / current_fd * 100) if current_fd > 0 else 0
        pct_after = (shares / new_fd * 100) if new_fd > 0 else 0
        before_ownership.append({"shareholder_id": sid, "shares": shares, "percent": round(pct_before, 2)})
        after_ownership.append({"shareholder_id": sid, "shares": shares, "percent": round(pct_after, 2), "dilution": round(pct_before - pct_after, 2)})

    return {
        "current_fully_diluted": current_fd,
        "new_fully_diluted": new_fd,
        "pre_money": data.pre_money,
        "post_money": post_money,
        "price_per_share": round(price_per_share, 4),
        "new_investor_shares": new_investor_shares,
        "new_investor_percent": round(new_investor_percent, 2),
        "option_pool_new_shares": pool_shares,
        "before_ownership": before_ownership,
        "after_ownership": after_ownership,
    }


# ─── Export ──────────────────────────────────────────────────────────

@router.get("/export/csv")
def export_csv(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_user_company(db, company_id, current_user)

    summary = _build_ownership_view(db, company_id, view_type="fully_diluted")

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Name", "Type", "Share Class", "Shares", "Ownership %"])

    for row in summary.get("ownership", []):
        common = row.get("common_shares", 0)
        preferred = row.get("preferred_shares", 0)
        options_net = row.get("options_granted", 0) - row.get("options_exercised", 0)
        if common > 0:
            writer.writerow([row["name"], row["type"], "Common", common, ""])
        if preferred > 0:
            writer.writerow([row["name"], row["type"], "Preferred", preferred, ""])
        if options_net > 0:
            writer.writerow([row["name"], row["type"], "Options (net)", options_net, ""])
        writer.writerow([row["name"], row["type"], "Total (FD)", row.get("total_fully_diluted", 0), f"{row.get('ownership_percent', 0)}%"])

    writer.writerow([])
    writer.writerow(["Total Fully Diluted Shares", summary.get("fully_diluted_shares", 0)])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=cap_table_{company_id}.csv"}
    )


@router.get("/export/json")
def export_json(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_user_company(db, company_id, current_user)

    holdings = db.query(EquityHolding).filter(
        EquityHolding.company_id == company_id
    ).options(joinedload(EquityHolding.shareholder)).all()

    grants = db.query(OptionGrant).filter(
        OptionGrant.company_id == company_id
    ).options(joinedload(OptionGrant.shareholder)).all()

    shareholders = db.query(Shareholder).filter(
        Shareholder.company_id == company_id
    ).all()

    convertibles = db.query(ConvertibleSecurity).filter(
        ConvertibleSecurity.company_id == company_id
    ).all()

    valuations = db.query(Valuation409A).filter(
        Valuation409A.company_id == company_id
    ).all()

    ocf_data = {
        "file_type": "OCF_CAP_TABLE_EXPORT",
        "version": "1.0",
        "company_id": company_id,
        "export_date": date.today().isoformat(),
        "stakeholders": [s.to_dict() for s in shareholders],
        "stock_issuances": [h.to_dict() for h in holdings],
        "stock_plans": [],
        "equity_compensation_issuances": [g.to_dict() for g in grants],
        "convertibles": [c.to_dict() for c in convertibles],
        "valuations": [v.to_dict() for v in valuations],
    }

    output = io.StringIO()
    json.dump(ocf_data, output, indent=2, default=str)
    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=cap_table_{company_id}.json"}
    )


# ─── Audit Log ───────────────────────────────────────────────────────

@router.get("/audit-log")
def get_audit_log(
    company_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    entity_type: Optional[str] = None,
    action: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_user_company(db, company_id, current_user)

    query = db.query(AuditLogEntry).filter(AuditLogEntry.company_id == company_id)
    if entity_type:
        query = query.filter(AuditLogEntry.entity_type == entity_type)
    if action:
        query = query.filter(AuditLogEntry.action == action)

    total = query.count()
    entries = (
        query
        .order_by(AuditLogEntry.timestamp.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "entries": [e.to_dict() for e in entries],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


# ─── 409A Summary Report ────────────────────────────────────────────

@router.get("/summary-409a")
def summary_409a(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_user_company(db, company_id, current_user)

    latest_val = db.query(Valuation409A).filter(
        Valuation409A.company_id == company_id,
        Valuation409A.status == "active"
    ).first()

    holdings = db.query(EquityHolding).filter(
        EquityHolding.company_id == company_id
    ).all()

    grants = db.query(OptionGrant).filter(
        OptionGrant.company_id == company_id,
        OptionGrant.status == GrantStatus.ACTIVE.value
    ).all()

    for g in grants:
        _update_vesting(g, db)

    total_shares_issued = sum(h.shares for h in holdings)
    total_common = sum(h.shares for h in holdings if h.share_class == ShareClass.COMMON.value)
    total_preferred = sum(h.shares for h in holdings if h.share_class == ShareClass.PREFERRED.value)
    total_options_granted = sum(g.shares_granted for g in grants)
    total_options_exercised = sum(g.shares_exercised for g in grants)
    total_options_outstanding = total_options_granted - total_options_exercised
    fully_diluted = total_shares_issued + total_options_outstanding

    weighted_exercise_price = 0
    if total_options_outstanding > 0:
        weighted_exercise_price = sum(
            g.exercise_price * (g.shares_granted - g.shares_exercised)
            for g in grants
        ) / total_options_outstanding

    convertibles = db.query(ConvertibleSecurity).filter(
        ConvertibleSecurity.company_id == company_id,
        ConvertibleSecurity.conversion_status == ConversionStatus.OUTSTANDING.value
    ).all()
    total_convertible_principal = sum(c.principal for c in convertibles)

    return {
        "valuation": latest_val.to_dict() if latest_val else None,
        "shares_summary": {
            "total_shares_issued": total_shares_issued,
            "total_common": total_common,
            "total_preferred": total_preferred,
            "total_options_outstanding": total_options_outstanding,
            "fully_diluted_shares": fully_diluted,
        },
        "options_summary": {
            "total_grants_active": len(grants),
            "total_options_granted": total_options_granted,
            "total_options_exercised": total_options_exercised,
            "total_options_outstanding": total_options_outstanding,
            "weighted_average_exercise_price": round(weighted_exercise_price, 4),
        },
        "convertibles_summary": {
            "total_outstanding": len(convertibles),
            "total_principal": total_convertible_principal,
        },
        "report_date": date.today().isoformat(),
    }


# ─── Helpers ─────────────────────────────────────────────────────────

def _update_vesting(grant: OptionGrant, db: Session):
    if grant.status != GrantStatus.ACTIVE.value:
        return
    if not grant.vesting_start_date:
        return

    today = date.today()
    start = grant.vesting_start_date
    months_elapsed = (today.year - start.year) * 12 + (today.month - start.month)

    if months_elapsed < grant.cliff_months:
        vested = 0
    elif months_elapsed >= grant.vesting_months:
        vested = grant.shares_granted
    else:
        vested = grant.shares_granted * (months_elapsed / grant.vesting_months)

    vested = min(vested, grant.shares_granted)
    if vested != grant.shares_vested:
        grant.shares_vested = round(vested, 2)
        grant.updated_at = datetime.utcnow()
        db.commit()


def _compute_vesting_schedule(grant: OptionGrant) -> List[Dict]:
    if not grant.vesting_start_date:
        return []

    schedule = []
    start = grant.vesting_start_date
    monthly_vest = grant.shares_granted / grant.vesting_months if grant.vesting_months > 0 else 0
    cumulative = 0

    for month in range(1, grant.vesting_months + 1):
        vest_date = start + relativedelta(months=month)
        if month < grant.cliff_months:
            shares_this_month = 0
        elif month == grant.cliff_months:
            shares_this_month = monthly_vest * grant.cliff_months
        else:
            shares_this_month = monthly_vest

        cumulative += shares_this_month
        cumulative = min(cumulative, grant.shares_granted)

        schedule.append({
            "month": month,
            "date": vest_date.isoformat(),
            "shares_vesting": round(shares_this_month, 2),
            "cumulative_vested": round(cumulative, 2),
            "percent_vested": round((cumulative / grant.shares_granted * 100), 1) if grant.shares_granted > 0 else 0,
            "is_cliff": month == grant.cliff_months,
        })

    return schedule


def _build_ownership_view(db: Session, company_id: int, view_type: str = "fully_diluted") -> Dict[str, Any]:
    holdings = db.query(EquityHolding).filter(
        EquityHolding.company_id == company_id
    ).options(joinedload(EquityHolding.shareholder)).all()

    grants = db.query(OptionGrant).filter(
        OptionGrant.company_id == company_id,
        OptionGrant.status == GrantStatus.ACTIVE.value
    ).options(joinedload(OptionGrant.shareholder)).all()

    for g in grants:
        _update_vesting(g, db)

    total_shares_issued = sum(h.shares for h in holdings)
    total_options_granted = sum(g.shares_granted for g in grants)
    total_options_exercised = sum(g.shares_exercised for g in grants)
    fully_diluted = total_shares_issued + total_options_granted - total_options_exercised

    ownership = {}
    for h in holdings:
        sid = str(h.shareholder_id)
        if sid not in ownership:
            ownership[sid] = {
                "shareholder_id": sid,
                "name": h.shareholder.name if h.shareholder else "Unknown",
                "type": h.shareholder.type if h.shareholder else "unknown",
                "common_shares": 0,
                "preferred_shares": 0,
                "options_granted": 0,
                "options_vested": 0,
                "options_exercised": 0,
            }
        if h.share_class == ShareClass.COMMON.value:
            ownership[sid]["common_shares"] += h.shares
        else:
            ownership[sid]["preferred_shares"] += h.shares

    for g in grants:
        sid = str(g.shareholder_id)
        if sid not in ownership:
            ownership[sid] = {
                "shareholder_id": sid,
                "name": g.shareholder.name if g.shareholder else "Unknown",
                "type": g.shareholder.type if g.shareholder else "unknown",
                "common_shares": 0,
                "preferred_shares": 0,
                "options_granted": 0,
                "options_vested": 0,
                "options_exercised": 0,
            }
        ownership[sid]["options_granted"] += g.shares_granted
        ownership[sid]["options_vested"] += g.shares_vested
        ownership[sid]["options_exercised"] += g.shares_exercised

    ownership_list = []
    for sid, d in ownership.items():
        total = d["common_shares"] + d["preferred_shares"] + d["options_granted"] - d["options_exercised"]
        d["total_fully_diluted"] = total
        d["ownership_percent"] = round((total / fully_diluted * 100), 2) if fully_diluted > 0 else 0
        ownership_list.append(d)

    ownership_list.sort(key=lambda x: x["ownership_percent"], reverse=True)

    return {
        "fully_diluted_shares": fully_diluted,
        "total_shares_issued": total_shares_issued,
        "ownership": ownership_list,
    }


def _compute_dilution_scenario(db: Session, company_id: int, pre_money: float, raise_amount: float, option_pool_refresh: float = 0) -> Dict[str, Any]:
    holdings = db.query(EquityHolding).filter(EquityHolding.company_id == company_id).all()
    grants = db.query(OptionGrant).filter(
        OptionGrant.company_id == company_id,
        OptionGrant.status == GrantStatus.ACTIVE.value
    ).all()

    total_shares = sum(h.shares for h in holdings)
    total_options = sum(g.shares_granted - g.shares_exercised for g in grants)
    current_fd = total_shares + total_options

    if current_fd == 0:
        return {"error": "No shares issued"}

    post_money = pre_money + raise_amount
    new_investor_percent = (raise_amount / post_money) * 100
    price_per_share = pre_money / current_fd
    new_investor_shares = int(raise_amount / price_per_share) if price_per_share > 0 else 0

    pool_shares = 0
    if option_pool_refresh > 0:
        pool_shares = int(current_fd * option_pool_refresh / (100 - option_pool_refresh))

    new_fd = current_fd + new_investor_shares + pool_shares

    return {
        "current_fully_diluted": current_fd,
        "new_fully_diluted": new_fd,
        "pre_money": pre_money,
        "post_money": post_money,
        "price_per_share": round(price_per_share, 4),
        "new_investor_shares": new_investor_shares,
        "new_investor_percent": round(new_investor_percent, 2),
        "option_pool_new_shares": pool_shares,
    }


def _compute_waterfall_scenario(db: Session, company_id: int, exit_value: float) -> Dict[str, Any]:
    holdings = db.query(EquityHolding).filter(
        EquityHolding.company_id == company_id
    ).options(joinedload(EquityHolding.shareholder)).all()

    grants = db.query(OptionGrant).filter(
        OptionGrant.company_id == company_id,
        OptionGrant.status == GrantStatus.ACTIVE.value
    ).options(joinedload(OptionGrant.shareholder)).all()

    remaining = exit_value
    tranches = []

    preferred_holdings = [h for h in holdings if h.share_class == ShareClass.PREFERRED.value]
    common_holdings = [h for h in holdings if h.share_class == ShareClass.COMMON.value]

    total_common_shares = sum(h.shares for h in common_holdings)
    total_options_exercisable = sum(max(0, g.shares_vested - g.shares_exercised) for g in grants)
    total_common_equivalent = total_common_shares + total_options_exercisable
    total_preferred_shares = sum(h.shares for h in preferred_holdings)
    total_all_shares = total_common_equivalent + total_preferred_shares

    seniority_groups = {}
    for h in preferred_holdings:
        sen = h.seniority or 1
        if sen not in seniority_groups:
            seniority_groups[sen] = []
        seniority_groups[sen].append(h)

    preferred_payouts = {}
    participating_holders = []

    for seniority_level in sorted(seniority_groups.keys(), reverse=True):
        group = seniority_groups[seniority_level]
        for h in group:
            holder_name = h.shareholder.name if h.shareholder else "Unknown"
            shares = h.shares
            pps = h.price_per_share or 0
            liq_mult = h.liquidation_preference_multiple or 1.0
            is_participating = h.is_participating or False

            preference_amount = shares * pps * liq_mult

            if is_participating:
                payout = min(preference_amount, remaining)
                remaining -= payout
                preferred_payouts[holder_name] = preferred_payouts.get(holder_name, 0) + payout
                participating_holders.append(h)
                tranches.append({
                    "holder": holder_name,
                    "share_class": "preferred",
                    "series": h.series or "",
                    "shares": shares,
                    "payout": round(payout, 2),
                    "payout_percent": round((payout / exit_value) * 100, 2) if exit_value > 0 else 0,
                    "method": "liquidation_preference",
                })
            else:
                as_converted_payout = (shares / total_all_shares * exit_value) if total_all_shares > 0 else 0

                if preference_amount >= as_converted_payout:
                    payout = min(preference_amount, remaining)
                    remaining -= payout
                    method = "liquidation_preference"
                else:
                    payout = min(as_converted_payout, remaining)
                    remaining -= payout
                    method = "as_converted"

                preferred_payouts[holder_name] = preferred_payouts.get(holder_name, 0) + payout
                tranches.append({
                    "holder": holder_name,
                    "share_class": "preferred",
                    "series": h.series or "",
                    "shares": shares,
                    "payout": round(payout, 2),
                    "payout_percent": round((payout / exit_value) * 100, 2) if exit_value > 0 else 0,
                    "method": method,
                })

    if remaining > 0 and participating_holders:
        participating_shares = sum(h.shares for h in participating_holders)
        shares_for_participation = total_common_equivalent + participating_shares

        if shares_for_participation > 0:
            for h in participating_holders:
                holder_name = h.shareholder.name if h.shareholder else "Unknown"
                shares = h.shares
                participation_cap_val = h.participation_cap

                pro_rata_share = (shares / shares_for_participation) * remaining
                if participation_cap_val is not None:
                    max_participation = participation_cap_val * shares * (h.price_per_share or 0)
                    already_received = preferred_payouts.get(holder_name, 0)
                    max_additional = max(0, max_participation - already_received)
                    pro_rata_share = min(pro_rata_share, max_additional)

                preferred_payouts[holder_name] = preferred_payouts.get(holder_name, 0) + pro_rata_share
                for t in tranches:
                    if t["holder"] == holder_name:
                        t["payout"] = round(t["payout"] + pro_rata_share, 2)
                        t["payout_percent"] = round((t["payout"] / exit_value) * 100, 2) if exit_value > 0 else 0
                        t["method"] = "participating"
                        break

            total_participation = sum(
                (h.shares / shares_for_participation) * remaining
                for h in participating_holders
            )
            remaining -= min(total_participation, remaining)

    common_payout_per_share = (remaining / total_common_equivalent) if total_common_equivalent > 0 else 0

    for h in common_holdings:
        holder_name = h.shareholder.name if h.shareholder else "Unknown"
        shares = h.shares
        payout = shares * common_payout_per_share

        tranches.append({
            "holder": holder_name,
            "share_class": "common",
            "series": "common",
            "shares": shares,
            "payout": round(payout, 2),
            "payout_percent": round((payout / exit_value) * 100, 2) if exit_value > 0 else 0,
            "method": "pro_rata",
        })

    for g in grants:
        exercisable = max(0, g.shares_vested - g.shares_exercised)
        if exercisable > 0:
            holder_name = g.shareholder.name if g.shareholder else "Unknown"
            payout = exercisable * common_payout_per_share
            tranches.append({
                "holder": f"{holder_name} (Options)",
                "share_class": "common (options)",
                "series": "",
                "shares": exercisable,
                "payout": round(payout, 2),
                "payout_percent": round((payout / exit_value) * 100, 2) if exit_value > 0 else 0,
                "method": "pro_rata",
            })

    preferred_total = sum(preferred_payouts.values())
    common_total = common_payout_per_share * total_common_equivalent

    return {
        "exit_value": exit_value,
        "total_distributed": round(exit_value - max(0, remaining - common_total), 2),
        "tranches": tranches,
        "common_payout_per_share": round(common_payout_per_share, 4),
        "preferred_total": round(preferred_total, 2),
        "common_total": round(common_total, 2),
        "remaining": round(max(0, remaining - common_total), 2),
    }
