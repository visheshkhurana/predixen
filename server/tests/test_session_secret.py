"""Production must refuse to boot when SESSION_SECRET is missing or the built-in default."""

from server.core.config import (
    DEFAULT_SESSION_SECRET,
    Settings,
    enforce_production_session_secret,
    resolve_signing_secret,
    session_secret_is_usable,
)


def test_production_refuses_default_blank_and_missing_secret():
    for secret in (DEFAULT_SESSION_SECRET, "", "   ", None):
        try:
            enforce_production_session_secret("production", secret)
        except RuntimeError as exc:
            assert "SESSION_SECRET" in str(exc)
        else:
            raise AssertionError(f"production startup accepted {secret!r}")


def test_production_accepts_a_real_secret():
    enforce_production_session_secret("production", "a-real-random-session-secret")


def test_development_allows_the_built_in_fallback():
    enforce_production_session_secret("development", DEFAULT_SESSION_SECRET)
    enforce_production_session_secret("development", None)
    enforce_production_session_secret("development", "")


def test_blank_secret_is_not_usable():
    assert session_secret_is_usable(None) is False
    assert session_secret_is_usable("") is False
    assert session_secret_is_usable("   ") is False
    assert session_secret_is_usable(DEFAULT_SESSION_SECRET) is False
    assert session_secret_is_usable("not-the-default") is True


def test_resolve_prefers_session_secret_over_legacy_key():
    assert resolve_signing_secret("from-session", "from-key") == "from-session"


def test_resolve_uses_legacy_key_when_session_secret_is_blank_or_default():
    assert resolve_signing_secret("", "from-key") == "from-key"
    assert resolve_signing_secret("   ", "from-key") == "from-key"
    assert resolve_signing_secret(DEFAULT_SESSION_SECRET, "from-key") == "from-key"


def test_resolve_blank_sources_keep_the_known_default():
    assert resolve_signing_secret("", "") == DEFAULT_SESSION_SECRET
    assert resolve_signing_secret(None, None) == DEFAULT_SESSION_SECRET


def test_settings_binds_session_secret_onto_signing_key():
    settings = Settings(SESSION_SECRET="from-session", SECRET_KEY="from-key")
    assert settings.SECRET_KEY == "from-session"

    blank = Settings(SESSION_SECRET="  ", SECRET_KEY="from-key")
    assert blank.SECRET_KEY == "from-key"

    unset = Settings(SESSION_SECRET="", SECRET_KEY="")
    assert unset.SECRET_KEY == DEFAULT_SESSION_SECRET
