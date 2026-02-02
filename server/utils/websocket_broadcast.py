"""WebSocket broadcast utility for Python backend.

This module provides helper functions to broadcast updates through
the Node.js WebSocket server.
"""
import httpx
import os
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

NODE_SERVER_URL = os.environ.get("NODE_SERVER_URL", "http://localhost:5000")

async def broadcast_metric_update(
    company_id: int, 
    metrics: Dict[str, Any], 
    source: str = "python"
) -> bool:
    """Broadcast metric updates to connected WebSocket clients."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{NODE_SERVER_URL}/internal/broadcast/metrics",
                json={
                    "companyId": company_id,
                    "metrics": metrics,
                    "source": source
                },
                timeout=5.0
            )
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Broadcast metric update to {result.get('clients', 0)} clients")
                return True
            else:
                logger.warning(f"Broadcast failed: {response.status_code}")
                return False
    except Exception as e:
        logger.warning(f"Failed to broadcast metric update: {e}")
        return False


async def broadcast_simulation_update(
    scenario_id: int,
    status: str,
    progress: Optional[float] = None,
    results: Optional[Dict[str, Any]] = None
) -> bool:
    """Broadcast simulation status updates to connected WebSocket clients."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{NODE_SERVER_URL}/internal/broadcast/simulation",
                json={
                    "scenarioId": scenario_id,
                    "status": status,
                    "progress": progress,
                    "results": results
                },
                timeout=5.0
            )
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Broadcast simulation update to {result.get('clients', 0)} clients")
                return True
            else:
                logger.warning(f"Broadcast failed: {response.status_code}")
                return False
    except Exception as e:
        logger.warning(f"Failed to broadcast simulation update: {e}")
        return False


async def broadcast_truth_scan_update(
    company_id: int,
    metrics: Optional[Dict[str, Any]] = None,
    status: str = "updated"
) -> bool:
    """Broadcast truth scan updates to connected WebSocket clients."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{NODE_SERVER_URL}/internal/broadcast/truth-scan",
                json={
                    "companyId": company_id,
                    "metrics": metrics or {},
                    "status": status
                },
                timeout=5.0
            )
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Broadcast truth scan update to {result.get('clients', 0)} clients")
                return True
            else:
                logger.warning(f"Broadcast failed: {response.status_code}")
                return False
    except Exception as e:
        logger.warning(f"Failed to broadcast truth scan update: {e}")
        return False


def broadcast_metric_update_sync(
    company_id: int, 
    metrics: Dict[str, Any], 
    source: str = "python"
) -> bool:
    """Synchronous version of broadcast_metric_update."""
    try:
        with httpx.Client() as client:
            response = client.post(
                f"{NODE_SERVER_URL}/internal/broadcast/metrics",
                json={
                    "companyId": company_id,
                    "metrics": metrics,
                    "source": source
                },
                timeout=5.0
            )
            return response.status_code == 200
    except Exception as e:
        logger.warning(f"Failed to broadcast metric update (sync): {e}")
        return False


def broadcast_truth_scan_update_sync(
    company_id: int,
    metrics: Optional[Dict[str, Any]] = None,
    status: str = "updated"
) -> bool:
    """Synchronous version of broadcast_truth_scan_update."""
    try:
        with httpx.Client() as client:
            response = client.post(
                f"{NODE_SERVER_URL}/internal/broadcast/truth-scan",
                json={
                    "companyId": company_id,
                    "metrics": metrics or {},
                    "status": status
                },
                timeout=5.0
            )
            return response.status_code == 200
    except Exception as e:
        logger.warning(f"Failed to broadcast truth scan update (sync): {e}")
        return False
