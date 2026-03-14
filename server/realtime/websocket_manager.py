import json
import logging
import asyncio
from typing import Dict, Set, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect

from server.infrastructure.pubsub import Channel

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self._connections: Dict[int, Set[WebSocket]] = {}
        self._global: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket, company_id: Optional[int] = None):
        await websocket.accept()
        if company_id:
            if company_id not in self._connections:
                self._connections[company_id] = set()
            self._connections[company_id].add(websocket)
        else:
            self._global.add(websocket)
        logger.info(f"WebSocket connected (company={company_id})")

    def disconnect(self, websocket: WebSocket, company_id: Optional[int] = None):
        if company_id and company_id in self._connections:
            self._connections[company_id].discard(websocket)
            if not self._connections[company_id]:
                del self._connections[company_id]
        self._global.discard(websocket)

    async def send_to_company(self, company_id: int, channel: str, data: Dict[str, Any]):
        message = json.dumps({"channel": channel, "data": data}, default=str)
        connections = self._connections.get(company_id, set()).copy()
        disconnected = []
        for ws in connections:
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            self.disconnect(ws, company_id)

    async def broadcast(self, channel: str, data: Dict[str, Any]):
        message = json.dumps({"channel": channel, "data": data}, default=str)
        disconnected = []
        for ws in self._global.copy():
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            self.disconnect(ws)

    @property
    def active_connections(self) -> int:
        count = len(self._global)
        for conns in self._connections.values():
            count += len(conns)
        return count


manager = ConnectionManager()


async def notify_simulation_progress(company_id: int, job_id: str, progress: int, status: str):
    await manager.send_to_company(company_id, Channel.SIMULATION_PROGRESS.value, {
        "job_id": job_id,
        "progress": progress,
        "status": status,
    })


async def notify_simulation_complete(company_id: int, job_id: str, results: Dict[str, Any]):
    await manager.send_to_company(company_id, Channel.SIMULATION_COMPLETE.value, {
        "job_id": job_id,
        "results": results,
    })


async def notify_twin_update(company_id: int, event_type: str, data: Dict[str, Any]):
    await manager.send_to_company(company_id, Channel.TWIN_UPDATE.value, {
        "event_type": event_type,
        **data,
    })


async def notify_connector_sync(company_id: int, connector: str, status: str, data: Optional[Dict] = None):
    await manager.send_to_company(company_id, Channel.CONNECTOR_SYNC.value, {
        "connector": connector,
        "status": status,
        "data": data or {},
    })
