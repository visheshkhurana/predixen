import time
import logging
import json
import functools
from typing import Optional, Any
from contextlib import contextmanager

logger = logging.getLogger("observability")

_metrics_store: dict[str, list] = {}


def structured_log(
    level: str,
    event: str,
    **kwargs: Any,
):
    log_data = {
        "event": event,
        "timestamp": time.time(),
        **kwargs,
    }
    getattr(logger, level, logger.info)(json.dumps(log_data, default=str))


@contextmanager
def track_duration(operation: str, **extra):
    start = time.time()
    error_occurred = False
    try:
        yield
    except Exception as e:
        error_occurred = True
        duration_ms = round((time.time() - start) * 1000, 1)
        structured_log("error", f"{operation}.error", duration_ms=duration_ms, error=str(e), **extra)
        raise
    finally:
        if not error_occurred:
            duration_ms = round((time.time() - start) * 1000, 1)
            structured_log("info", f"{operation}.complete", duration_ms=duration_ms, **extra)
            _record_metric(operation, duration_ms)


def track_operation(operation: str):
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            with track_duration(operation, function=func.__name__):
                return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            with track_duration(operation, function=func.__name__):
                return func(*args, **kwargs)

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator


def _record_metric(name: str, value: float, max_history: int = 100):
    if name not in _metrics_store:
        _metrics_store[name] = []
    _metrics_store[name].append({"value": value, "ts": time.time()})
    if len(_metrics_store[name]) > max_history:
        _metrics_store[name] = _metrics_store[name][-max_history:]


def get_metrics_summary() -> dict:
    summary = {}
    for name, values in _metrics_store.items():
        if not values:
            continue
        vals = [v["value"] for v in values]
        summary[name] = {
            "count": len(vals),
            "avg_ms": round(sum(vals) / len(vals), 1),
            "min_ms": round(min(vals), 1),
            "max_ms": round(max(vals), 1),
            "p50_ms": round(sorted(vals)[len(vals) // 2], 1),
            "last_ms": round(vals[-1], 1),
        }
    return summary


def track_simulation(company_id: int, scenario_id: Optional[int] = None):
    return track_duration("simulation.run", company_id=company_id, scenario_id=scenario_id)


def track_ai_request(model: str, task_type: str):
    return track_duration("ai.request", model=model, task_type=task_type)


def track_connector_sync(connector_type: str, company_id: int):
    return track_duration("connector.sync", connector_type=connector_type, company_id=company_id)


def track_api_request(endpoint: str, method: str):
    return track_duration("api.request", endpoint=endpoint, method=method)
