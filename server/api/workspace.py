from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
import secrets

from server.core.db import get_db
from server.core.security import get_current_user
from server.models.user import User
from server.models.company import Company
from server.models.workspace import WorkspaceMember, WorkspaceInvite, NotificationPreference

router = APIRouter(prefix="/workspace", tags=["workspace"])


class MemberResponse(BaseModel):
    id: int
    user_id: int
    email: str
    role: str
    status: str
    invited_at: str
    joined_at: Optional[str] = None


class InviteResponse(BaseModel):
    id: int
    email: str
    role: str
    status: str
    invited_at: str
    expires_at: Optional[str] = None


class InviteMemberRequest(BaseModel):
    email: EmailStr
    role: str = "viewer"


class UpdateRoleRequest(BaseModel):
    role: str


class NotificationSettingsRequest(BaseModel):
    email_enabled: bool = True
    email_address: Optional[str] = None
    alert_types: dict = {}
    thresholds: dict = {}
    frequency: str = "immediate"


class NotificationSettingsResponse(BaseModel):
    email_enabled: bool
    email_address: Optional[str]
    alert_types: dict
    thresholds: dict
    frequency: str


def require_workspace_access(company_id: int, user: User, db: Session, min_role: str = "viewer") -> WorkspaceMember:
    """Check if user has workspace access and required role"""
    # Check if user owns the company
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    if company.user_id == user.id:
        # Owner always has access
        return WorkspaceMember(
            id=0,
            company_id=company_id,
            user_id=user.id,
            role="owner",
            status="active"
        )
    
    # Check workspace membership
    member = db.query(WorkspaceMember).filter(
        WorkspaceMember.company_id == company_id,
        WorkspaceMember.user_id == user.id,
        WorkspaceMember.status == "active"
    ).first()
    
    if not member:
        raise HTTPException(status_code=403, detail="No access to this workspace")
    
    role_hierarchy = {"owner": 4, "admin": 3, "editor": 2, "viewer": 1}
    if role_hierarchy.get(member.role, 0) < role_hierarchy.get(min_role, 0):
        raise HTTPException(status_code=403, detail=f"Requires {min_role} role or higher")
    
    return member


@router.get("/companies/{company_id}/members", response_model=List[MemberResponse])
def list_members(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all workspace members for a company"""
    require_workspace_access(company_id, current_user, db)
    
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Get owner
    owner = db.query(User).filter(User.id == company.user_id).first()
    members_list = []
    
    if owner:
        members_list.append(MemberResponse(
            id=0,
            user_id=owner.id,
            email=owner.email,
            role="owner",
            status="active",
            invited_at=company.created_at.isoformat(),
            joined_at=company.created_at.isoformat()
        ))
    
    # Get other members
    members = db.query(WorkspaceMember).filter(
        WorkspaceMember.company_id == company_id
    ).all()
    
    for member in members:
        user = db.query(User).filter(User.id == member.user_id).first()
        if user:
            members_list.append(MemberResponse(
                id=member.id,
                user_id=member.user_id,
                email=user.email,
                role=member.role,
                status=member.status,
                invited_at=member.invited_at.isoformat(),
                joined_at=member.joined_at.isoformat() if member.joined_at else None
            ))
    
    return members_list


@router.get("/companies/{company_id}/invites", response_model=List[InviteResponse])
def list_invites(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List pending invitations"""
    require_workspace_access(company_id, current_user, db, min_role="admin")
    
    invites = db.query(WorkspaceInvite).filter(
        WorkspaceInvite.company_id == company_id,
        WorkspaceInvite.status == "pending"
    ).all()
    
    return [
        InviteResponse(
            id=invite.id,
            email=invite.email,
            role=invite.role,
            status=invite.status,
            invited_at=invite.invited_at.isoformat(),
            expires_at=invite.expires_at.isoformat() if invite.expires_at else None
        )
        for invite in invites
    ]


@router.post("/companies/{company_id}/invite")
def invite_member(
    company_id: int,
    request: InviteMemberRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Invite a new member to the workspace"""
    require_workspace_access(company_id, current_user, db, min_role="admin")
    
    # Check if already a member
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        existing_member = db.query(WorkspaceMember).filter(
            WorkspaceMember.company_id == company_id,
            WorkspaceMember.user_id == existing_user.id
        ).first()
        if existing_member:
            raise HTTPException(status_code=400, detail="User is already a member")
    
    # Check for pending invite
    existing_invite = db.query(WorkspaceInvite).filter(
        WorkspaceInvite.company_id == company_id,
        WorkspaceInvite.email == request.email,
        WorkspaceInvite.status == "pending"
    ).first()
    if existing_invite:
        raise HTTPException(status_code=400, detail="Invitation already pending")
    
    # Create invite
    invite = WorkspaceInvite(
        company_id=company_id,
        email=request.email,
        role=request.role,
        invited_by=current_user.id,
        token=secrets.token_urlsafe(32),
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    db.add(invite)
    db.commit()
    
    # TODO: Send email notification
    
    return {"status": "invited", "invite_id": invite.id}


@router.patch("/members/{member_id}/role")
def update_member_role(
    member_id: int,
    request: UpdateRoleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a member's role"""
    member = db.query(WorkspaceMember).filter(WorkspaceMember.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    require_workspace_access(member.company_id, current_user, db, min_role="admin")
    
    if request.role not in ["admin", "editor", "viewer"]:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    member.role = request.role
    db.commit()
    
    return {"status": "updated", "role": member.role}


@router.delete("/members/{member_id}")
def remove_member(
    member_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove a member from the workspace"""
    member = db.query(WorkspaceMember).filter(WorkspaceMember.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    require_workspace_access(member.company_id, current_user, db, min_role="admin")
    
    db.delete(member)
    db.commit()
    
    return {"status": "removed"}


@router.delete("/invites/{invite_id}")
def revoke_invite(
    invite_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Revoke a pending invitation"""
    invite = db.query(WorkspaceInvite).filter(WorkspaceInvite.id == invite_id).first()
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found")
    
    require_workspace_access(invite.company_id, current_user, db, min_role="admin")
    
    invite.status = "revoked"
    db.commit()
    
    return {"status": "revoked"}


@router.post("/invites/{invite_id}/resend")
def resend_invite(
    invite_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Resend an invitation email"""
    invite = db.query(WorkspaceInvite).filter(WorkspaceInvite.id == invite_id).first()
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found")
    
    require_workspace_access(invite.company_id, current_user, db, min_role="admin")
    
    # Refresh expiration
    invite.expires_at = datetime.utcnow() + timedelta(days=7)
    invite.token = secrets.token_urlsafe(32)
    db.commit()
    
    # TODO: Send email notification
    
    return {"status": "resent"}


# Notification preferences endpoints

@router.get("/notifications/preferences", response_model=NotificationSettingsResponse)
def get_notification_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's notification preferences"""
    prefs = db.query(NotificationPreference).filter(
        NotificationPreference.user_id == current_user.id
    ).first()
    
    if not prefs:
        # Return defaults
        return NotificationSettingsResponse(
            email_enabled=True,
            email_address=current_user.email,
            alert_types={
                "runway_warning": True,
                "growth_decline": True,
                "churn_spike": True,
                "cash_low": True,
                "scenario_complete": False,
                "team_activity": False
            },
            thresholds={
                "runway_months": 12,
                "growth_decline_pct": 10,
                "churn_increase_pct": 20,
                "cash_low_months": 6
            },
            frequency="immediate"
        )
    
    return NotificationSettingsResponse(
        email_enabled=prefs.email_enabled,
        email_address=prefs.email_address or current_user.email,
        alert_types=prefs.alert_types or {},
        thresholds=prefs.thresholds or {},
        frequency=prefs.frequency
    )


@router.put("/notifications/preferences")
def update_notification_preferences(
    request: NotificationSettingsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update user's notification preferences"""
    prefs = db.query(NotificationPreference).filter(
        NotificationPreference.user_id == current_user.id
    ).first()
    
    if not prefs:
        prefs = NotificationPreference(user_id=current_user.id)
        db.add(prefs)
    
    prefs.email_enabled = request.email_enabled
    prefs.email_address = request.email_address
    prefs.alert_types = request.alert_types
    prefs.thresholds = request.thresholds
    prefs.frequency = request.frequency
    
    db.commit()
    
    return {"status": "updated"}
