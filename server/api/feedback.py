from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text
from server.core.db import get_db
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feedback", tags=["feedback"])


class FeedbackCreate(BaseModel):
    type: str = Field(..., pattern="^(bug|feature|general|question)$")
    message: str = Field(..., min_length=1, max_length=5000)
    page: str = Field("", max_length=500)


@router.post("")
async def submit_feedback(
    body: FeedbackCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    user_id = None
    email = None
    try:
        from server.api.auth import get_current_user
        from fastapi import HTTPException
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            from jose import jwt
            from server.core.config import settings
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            user_id = int(payload.get("sub", 0)) or None
            if user_id:
                row = db.execute(text("SELECT email FROM users WHERE id = :uid"), {"uid": user_id}).fetchone()
                if row:
                    email = row[0]
    except Exception:
        pass

    db.execute(
        text("""
            INSERT INTO beta_feedback (user_id, email, type, message, page)
            VALUES (:user_id, :email, :type, :message, :page)
        """),
        {
            "user_id": user_id,
            "email": email,
            "type": body.type,
            "message": body.message,
            "page": body.page,
        },
    )
    db.commit()
    logger.info(f"Feedback received: type={body.type}, user_id={user_id}, page={body.page}")
    return {"ok": True}


@router.get("")
async def list_feedback(db: Session = Depends(get_db)):
    rows = db.execute(
        text("SELECT id, user_id, email, type, message, page, created_at FROM beta_feedback ORDER BY created_at DESC LIMIT 100")
    ).fetchall()
    return [
        {
            "id": r[0],
            "user_id": r[1],
            "email": r[2],
            "type": r[3],
            "message": r[4],
            "page": r[5],
            "created_at": str(r[6]) if r[6] else None,
        }
        for r in rows
    ]
