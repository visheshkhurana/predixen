import json
import logging
import threading
from typing import Callable, Dict, Any, Optional, Set
from enum import Enum

from server.core.redis_client import get_redis

logger = logging.getLogger(__name__)

PREFIX = "fc:pubsub:"


class Channel(str, Enum):
    SIMULATION_PROGRESS = "simulation:progress"
    SIMULATION_COMPLETE = "simulation:complete"
    TWIN_UPDATE = "twin:update"
    ALERT_TRIGGERED = "alert:triggered"
    CONNECTOR_SYNC = "connector:sync"
    SYSTEM = "system"


_subscribers: Dict[str, Set[Callable]] = {}
_listener_thread: Optional[threading.Thread] = None
_running = False


def publish(channel: Channel, data: Dict[str, Any], company_id: Optional[int] = None):
    try:
        r = get_redis()
        message = json.dumps({
            "channel": channel.value,
            "company_id": company_id,
            "data": data,
        }, default=str)
        r.publish(PREFIX + channel.value, message)
    except Exception as e:
        logger.debug(f"Pub/sub publish failed: {e}")


def subscribe(channel: Channel, callback: Callable):
    key = PREFIX + channel.value
    if key not in _subscribers:
        _subscribers[key] = set()
    _subscribers[key].add(callback)


def _listener_loop():
    global _running
    try:
        r = get_redis()
        if hasattr(r, 'pubsub'):
            ps = r.pubsub()
            channels = list(_subscribers.keys())
            if channels:
                ps.subscribe(*channels)
                for message in ps.listen():
                    if not _running:
                        break
                    if message["type"] == "message":
                        channel = message["channel"]
                        if isinstance(channel, bytes):
                            channel = channel.decode()
                        callbacks = _subscribers.get(channel, set())
                        for cb in callbacks:
                            try:
                                data = json.loads(message["data"])
                                cb(data)
                            except Exception as e:
                                logger.error(f"Pub/sub callback error: {e}")
    except Exception as e:
        logger.warning(f"Pub/sub listener error: {e}")
    finally:
        _running = False


def start_listener():
    global _listener_thread, _running
    if _running:
        return
    _running = True
    _listener_thread = threading.Thread(target=_listener_loop, daemon=True, name="pubsub-listener")
    _listener_thread.start()
    logger.info("Pub/sub listener started")


def stop_listener():
    global _running
    _running = False
