"""Request URLs (which can carry provider tokens) must not reach the logs."""

import logging


def test_httpx_request_lines_are_not_logged():
    import server.main  # noqa: F401  (sets logger levels at import)

    for name in ("httpx", "httpcore"):
        assert logging.getLogger(name).getEffectiveLevel() >= logging.WARNING
