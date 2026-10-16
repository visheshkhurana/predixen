"""The public /health body carries only what the deploy probe and banner read."""

from unittest.mock import MagicMock, patch

import server.main as main


def test_health_body_has_no_internal_details():
    redis = MagicMock()
    redis.ping.return_value = True
    with patch.object(main, "SessionLocal", return_value=MagicMock()), patch(
        "server.core.redis_client.get_redis", return_value=redis
    ), patch.dict(main._startup_state, {"ready": True, "routers_loaded": True, "error": "boom secret"}):
        body = main.health()

    assert set(body) <= {"status", "ready", "routers_loaded", "database", "redis"}
    assert body["status"] == "healthy"
    # fields services/deploy_landed.py asserts on are still present
    assert body["database"] == "connected"
    assert body["redis"] == "connected"
    assert body["routers_loaded"] is True
    assert "boom secret" not in str(body)
