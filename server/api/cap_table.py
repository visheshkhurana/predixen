"""
Cap Table Management API - Carta-like equity management system.
Shareholders, equity holdings, option grants, vesting, transactions, 409A valuations.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from uuid import UUID

from server.core.db import get_db
from server.core.security import get_current_user
from server.core.company_access import get_user_company
from server.models.user import User
from server.models.cap_table import (
    Shareholder, EquityHolding, OptionGrant,
    EquityTransaction, Valuation409A,
    ShareClass, GrantType, GrantStatus, TransactionType, VestingType,
)

router = APIRouter(prefix="/companies/{company_id}/cap-table", tags=["cap-table"])


class ShareholderCreate(BaseModel):
    name: str
    email: Optional[str] = None
    type: str = "founder"
    relationship_type: Optional[str] = None
    notes: Optional[str] = None


class ShareholderUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    type: Optional[str] = None
    relationship_type: Optional[str] = None
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

    existing = db.query(Shareholder).filter(
        Shareholder.company_id == company_id,
        Shareholder.name == data.name
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Shareholder with this name already exists")

    sh = Shareholder(
        company_id=company_id,
        name=data.name,
        email=data.email,
        type=data.type,
        relationship_type=data.relationship_type,
        notes=data.notes
    )
    db.add(sh)
    db.commit()
    db.refresh(sh)
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

    for field in ["name", "email", "type", "relationship_type", "notes", "is_active"]:
        val = getattr(data, field)
        if val is not None:
            setattr(sh, field, val)

    sh.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(sh)
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
    return grant.to_dict()


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
