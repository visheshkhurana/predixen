"""The public /health body must not echo the raw startup exception.

Narrowed port of #138's /health change. The fields the deploy probe
(server/services/deploy_landed.py) and scripts/launch_gate.sh read are kept,
including "startup_error":null on a clean start; only the exception text is
withheld.
"""

from unittest.mock import MagicMock, patch

import server.main as main


def _health(error):
    redis = MagicMock()
    redis.ping.return_value = True
    with patch.object(main, "SessionLocal", return_value=MagicMock()), patch(
        "server.core.redis_client.get_redis", return_value=redis
    ), patch.dict(main._startup_state, {"ready": True, "routers_loaded": True, "error": error}):
        return main.health()


def test_startup_exception_text_is_not_in_the_body():
    body = _health("could not connect to postgresql://admin:hunter2@10.0.0.4/prod")
    assert "hunter2" not in str(body)
    assert "postgresql" not in str(body)
    assert body["startup_error"]  # still says there was one


def test_clean_start_keeps_the_fields_the_probes_read():
    body = _health(None)
    assert body["startup_error"] is None
    assert body["status"] == "healthy"
    assert body["database"] == "connected"
    assert body["redis"] == "connected"
    assert body["routers_loaded"] is True
    assert body["ready"] is True
