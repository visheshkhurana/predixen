"""Deploy-landed monitor: hash + real bodies, with a control that must fail.

No live network — httpx.get is mocked for every case.
"""
from __future__ import annotations

import json
from unittest.mock import patch

from server.services.deploy_landed import (
    BODY_CONTROL_SENTINEL,
    CONTROL_ASSET_DEFAULT,
    check_deploy_landed,
    extract_index_hash,
    format_report,
)


GREEN_HASH = "eWXmctMP"

GREEN_HOME = (
    "<!DOCTYPE html><html><body>"
    '<div id="root"><div id="ssr-content">home</div></div>'
    f'<script type="module" src="/assets/index-{GREEN_HASH}.js"></script>'
    "</body></html>"
)

GREEN_PRICING = (
    "<!DOCTYPE html><html><body>"
    '<div id="root"><div id="ssr-content">Pricing</div></div>'
    f'<script type="module" src="/assets/index-{GREEN_HASH}.js"></script>'
    "</body></html>"
)

GREEN_HEALTH = {
    "status": "healthy",
    "database": "connected",
    "redis": "connected",
    "routers_loaded": True,
}


def _green_map(**overrides) -> dict[str, tuple[int, str]]:
    mapping = {
        "/": (200, GREEN_HOME),
        "/pricing": (200, GREEN_PRICING),
        "/health": (200, json.dumps(GREEN_HEALTH)),
        "/api/leads": (401, '{"detail":"Not authenticated"}'),
        "/api/events": (401, '{"detail":"Not authenticated"}'),
        CONTROL_ASSET_DEFAULT: (404, "Not Found"),
    }
    mapping.update(overrides)
    return mapping


def _handler(mapping: dict[str, tuple[int, str]]):
    def fake_get(url, *args, **kwargs):
        from urllib.parse import urlparse

        path = urlparse(url).path or "/"
        if path not in mapping:
            raise AssertionError(f"unmocked path {path!r} url={url!r}")
        status, body = mapping[path]
        return __import__("httpx").Response(
            status,
            text=body,
            request=__import__("httpx").Request("GET", url),
        )

    return fake_get


def _run(mapping: dict[str, tuple[int, str]], env: dict[str, str] | None = None):
    extra_env = {
        "APP_BASE_URL": "https://founderconsole.ai",
        **(env or {}),
    }
    # Drop hash envs unless the test set them, so leftover process env cannot
    # turn a record-only run into a mismatch.
    cleared = {}
    if "EXPECTED_INDEX_HASH" not in extra_env:
        cleared["EXPECTED_INDEX_HASH"] = ""
    if "DEPLOY_EXPECTED_INDEX_HASH" not in extra_env:
        cleared["DEPLOY_EXPECTED_INDEX_HASH"] = ""
    with patch.dict("os.environ", {**cleared, **extra_env}, clear=False):
        with patch("httpx.get", side_effect=_handler(mapping)):
            return check_deploy_landed()


def _named(report, name: str):
    matches = [r for r in report.results if r.name == name]
    assert matches, f"{name} not in {[r.name for r in report.results]}"
    return matches[0]


class TestExtractIndexHash:
    def test_quoted_src(self):
        assert extract_index_hash(GREEN_HOME) == GREEN_HASH

    def test_single_quoted_src(self):
        html = "<script src='/assets/index-abc123.js'></script>"
        assert extract_index_hash(html) == "abc123"

    def test_missing(self):
        assert extract_index_hash("<html></html>") is None


class TestGreenPath:
    def test_all_probes_ok_and_hash_recorded(self):
        report = _run(_green_map())
        assert report.status == "ok"
        assert report.index_hash == GREEN_HASH
        assert report.expected_index_hash is None
        assert _named(report, "fake-asset").ok
        assert _named(report, "fake-asset").status == 404
        assert _named(report, "body-absent").ok
        assert _named(report, "homepage-hash").ok
        assert _named(report, "health").ok
        assert _named(report, "pricing-ssr").ok
        assert _named(report, "leads-auth").ok
        assert _named(report, "events-auth").ok
        text = format_report(report)
        assert "status=ok" in text
        assert GREEN_HASH in text
        assert "recorded only" in text

    def test_leads_401_is_ok(self):
        report = _run(_green_map(**{"/api/leads": (401, '{"detail":"Not authenticated"}')}))
        assert report.status == "ok"
        assert _named(report, "leads-auth").ok
        assert _named(report, "leads-auth").status == 401


class TestControlMustFail:
    def test_fake_asset_200_is_control_failed_never_green(self):
        report = _run(
            _green_map(
                **{CONTROL_ASSET_DEFAULT: (200, GREEN_HOME)},
            )
        )
        assert report.status == "control-failed"
        assert report.status != "ok"
        control = _named(report, "fake-asset")
        assert not control.ok
        assert control.status == 200
        assert "meaningless" in control.detail
        # Other probes can look green; the headline must still be control-failed.
        assert _named(report, "health").ok
        assert _named(report, "leads-auth").ok
        text = format_report(report)
        assert "control-failed" in text

    def test_body_sentinel_present_is_control_failed(self):
        poisoned = GREEN_HOME.replace("</body>", f"{BODY_CONTROL_SENTINEL}</body>")
        report = _run(_green_map(**{"/": (200, poisoned)}))
        assert report.status == "control-failed"
        assert not _named(report, "body-absent").ok


class TestBodyFailClosed:
    def test_missing_ssr_content_failed(self):
        spa_shell = (
            "<!DOCTYPE html><html><body><div id='root'></div>"
            f'<script src="/assets/index-{GREEN_HASH}.js"></script></body></html>'
        )
        report = _run(_green_map(**{"/pricing": (200, spa_shell)}))
        assert report.status == "failed"
        pricing = _named(report, "pricing-ssr")
        assert not pricing.ok
        assert pricing.status == 200
        assert "missing" in pricing.detail
        assert _named(report, "fake-asset").ok

    def test_leads_404_failed(self):
        report = _run(_green_map(**{"/api/leads": (404, '{"detail":"Not Found"}')}))
        assert report.status == "failed"
        leads = _named(report, "leads-auth")
        assert not leads.ok
        assert leads.status == 404
        assert "expected 401" in leads.detail

    def test_health_missing_redis_failed(self):
        payload = dict(GREEN_HEALTH)
        payload["redis"] = "unavailable"
        report = _run(_green_map(**{"/health": (200, json.dumps(payload))}))
        assert report.status == "failed"
        health = _named(report, "health")
        assert not health.ok
        assert "redis" in health.detail


class TestExpectedHash:
    def test_mismatch_failed(self):
        report = _run(_green_map(), env={"DEPLOY_EXPECTED_INDEX_HASH": "otherhash"})
        assert report.status == "failed"
        assert report.index_hash == GREEN_HASH
        assert report.expected_index_hash == "otherhash"
        hashed = _named(report, "homepage-hash")
        assert not hashed.ok
        assert "MISMATCH" in format_report(report) or "otherhash" in hashed.detail

    def test_expected_index_hash_alias(self):
        report = _run(_green_map(), env={"EXPECTED_INDEX_HASH": "nope"})
        assert report.status == "failed"
        assert report.expected_index_hash == "nope"

    def test_unset_recorded_not_failed(self):
        report = _run(_green_map())
        assert report.status == "ok"
        assert report.index_hash == GREEN_HASH
        assert report.expected_index_hash is None
        hashed = _named(report, "homepage-hash")
        assert hashed.ok
        assert "recorded" in hashed.detail
        assert "no expected hash" in hashed.detail

    def test_matching_expected_hash_ok(self):
        report = _run(
            _green_map(),
            env={"DEPLOY_EXPECTED_INDEX_HASH": f"index-{GREEN_HASH}.js"},
        )
        assert report.status == "ok"
        assert report.expected_index_hash == GREEN_HASH
        assert _named(report, "homepage-hash").ok


class TestExtraBodyProbes:
    def test_env_appends_named_body_probe(self):
        features = '<div id="ssr-content">features</div>'
        mapping = _green_map(**{"/features": (200, features)})
        report = _run(
            mapping,
            env={"DEPLOY_LANDED_EXTRA_BODY_PROBES": '/features::id="ssr-content"'},
        )
        assert report.status == "ok"
        extra = _named(report, "body:/features")
        assert extra.ok

    def test_env_body_probe_fails_closed(self):
        mapping = _green_map(**{"/features": (200, "<html>no ssr</html>")})
        report = _run(
            mapping,
            env={"DEPLOY_LANDED_EXTRA_BODY_PROBES": '/features::id="ssr-content"'},
        )
        assert report.status == "failed"
        assert not _named(report, "body:/features").ok


class TestKillSwitch:
    def test_enabled_false_skips_loop(self):
        import asyncio
        from server.services.deploy_landed import run_deploy_landed_loop

        with patch.dict("os.environ", {"DEPLOY_LANDED_ENABLED": "false"}):
            asyncio.run(run_deploy_landed_loop())
