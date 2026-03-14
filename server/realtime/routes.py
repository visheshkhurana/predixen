import logging
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional

from server.realtime.websocket_manager import manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


async def _authenticate_ws(websocket: WebSocket) -> Optional[dict]:
    try:
        from server.core.db import SessionLocal
        from server.api.auth import get_current_user_from_token

        cookies = websocket.cookies
        token = cookies.get("access_token")
        if not token:
            query_params = websocket.query_params
            token = query_params.get("token")
        if not token:
            return None

        db = SessionLocal()
        try:
            user = get_current_user_from_token(token, db)
            if user:
                return {"id": user.id, "email": user.email}
        finally:
            db.close()
    except Exception as e:
        logger.debug(f"WebSocket auth failed: {e}")
    return None


async def _user_owns_company(user_id: int, company_id: int) -> bool:
    try:
        from server.core.db import SessionLocal
        from server.core.models import Company, UserCompanyRole

        db = SessionLocal()
        try:
            owns = db.query(Company).filter(
                Company.id == company_id,
                Company.user_id == user_id
            ).first()
            if owns:
                return True

            role = db.query(UserCompanyRole).filter(
                UserCompanyRole.company_id == company_id,
                UserCompanyRole.user_id == user_id
            ).first()
            return role is not None
        finally:
            db.close()
    except Exception as e:
        logger.debug(f"Company access check failed: {e}")
        return False


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    company_id: Optional[int] = Query(None),
):
    user = await _authenticate_ws(websocket)
    if not user:
        await websocket.close(code=4001, reason="Authentication required")
        return

    if company_id:
        has_access = await _user_owns_company(user["id"], company_id)
        if not has_access:
            await websocket.close(code=4003, reason="Access denied to company")
            return

    await manager.connect(websocket, company_id)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket, company_id)
    except Exception as e:
        logger.debug(f"WebSocket error: {e}")
        manager.disconnect(websocket, company_id)


@router.get("/ws/status")
def websocket_status():
    return {
        "active_connections": manager.active_connections,
    }
