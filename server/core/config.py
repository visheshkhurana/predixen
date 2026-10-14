import os
from pydantic import model_validator
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List, Optional

def parse_cors_origins(origins_str: str) -> List[str]:
    """Parse comma-separated CORS origins string into a list."""
    if not origins_str:
        return []
    return [origin.strip() for origin in origins_str.split(",") if origin.strip()]

def parse_optional_bool(env_var: str) -> Optional[bool]:
    """Parse an optional boolean from environment variable."""
    val = os.getenv(env_var, "")
    if not val:
        return None
    return val.lower() == "true"

# Built-in JWT signing key. Production must not boot with this value: anyone
# who knows it can mint admin tokens. Blank and whitespace count as unset.
DEFAULT_SESSION_SECRET = "founderconsole-secret-key-change-in-production"


def resolve_signing_secret(session_secret: Optional[str], secret_key: Optional[str]) -> str:
    """Pick the signing key. SESSION_SECRET wins when it is a real value.

    An empty SESSION_SECRET is unset, not a key. SECRET_KEY is the legacy
    env name for the same setting. The built-in default is returned only when
    neither source has a usable value, so production startup can refuse it.
    """
    session = (session_secret or "").strip()
    explicit = (secret_key or "").strip()
    if session and session != DEFAULT_SESSION_SECRET:
        return session
    if explicit and explicit != DEFAULT_SESSION_SECRET:
        return explicit
    return DEFAULT_SESSION_SECRET


def session_secret_is_usable(secret: Optional[str]) -> bool:
    if secret is None:
        return False
    stripped = secret.strip()
    return bool(stripped) and stripped != DEFAULT_SESSION_SECRET


def enforce_production_session_secret(environment: str, secret: Optional[str]) -> None:
    """Fail startup in production when SESSION_SECRET was never set."""
    if environment != "production":
        return
    if session_secret_is_usable(secret):
        return
    raise RuntimeError(
        "Refusing to start in production without a SESSION_SECRET. "
        "Set SESSION_SECRET to a strong random value; a blank value and the "
        "built-in fallback are not accepted."
    )

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./founderconsole.db")
    # Populated from the environment / .env. resolve_signing_secret copies a
    # usable SESSION_SECRET onto SECRET_KEY, which is what signs JWTs.
    SESSION_SECRET: str = ""
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))  # 8h default (was 15m — too short, bounced active users); 7-day refresh token still behind it
    MASTER_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("MASTER_TOKEN_EXPIRE_MINUTES", "30"))  # 30 min for admin

    FEATURE_INVESTOR_MODE: bool = os.getenv("FEATURE_INVESTOR_MODE", "false").lower() == "true"

    # Expose /docs, /redoc and /openapi.json. Off by default in production so the
    # full API surface isn't publicly browsable; set EXPOSE_API_DOCS=true to override.
    EXPOSE_API_DOCS: bool = os.getenv("EXPOSE_API_DOCS", "false").lower() == "true"

    ADMIN_MASTER_EMAIL: str = os.getenv("ADMIN_MASTER_EMAIL", "")
    ADMIN_MASTER_PASSWORD_HASH: str = os.getenv("ADMIN_MASTER_PASSWORD_HASH", "")

    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GITHUB_CLIENT_ID: str = os.getenv("GITHUB_CLIENT_ID", "")
    GITHUB_CLIENT_SECRET: str = os.getenv("GITHUB_CLIENT_SECRET", "")

    # Billing (Stripe). Empty STRIPE_SECRET_KEY = payments disabled (stub mode).
    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    APP_BASE_URL: str = os.getenv("APP_BASE_URL", "https://founderconsole.ai")
    # Paywall: gate premium features by plan. Users created before
    # PAYWALL_GRANDFATHER_BEFORE (ISO date) keep full access for free.
    PAYWALL_ENABLED: bool = os.getenv("PAYWALL_ENABLED", "false").lower() == "true"
    PAYWALL_GRANDFATHER_BEFORE: str = os.getenv("PAYWALL_GRANDFATHER_BEFORE", "")

    # Environment: "development" or "production"
    ENVIRONMENT: str = os.getenv("NODE_ENV", os.getenv("ENVIRONMENT", "development"))

    # CORS configuration - comma-separated list of allowed origins
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "")

    # Rate limiting configuration (requests per minute)
    RATE_LIMIT_AUTH: int = int(os.getenv("RATE_LIMIT_AUTH", "5"))
    RATE_LIMIT_ADMIN_LOGIN: int = int(os.getenv("RATE_LIMIT_ADMIN_LOGIN", "3"))  # Stricter for admin
    RATE_LIMIT_API: int = int(os.getenv("RATE_LIMIT_API", "60"))
    RATE_LIMIT_UPLOAD: int = int(os.getenv("RATE_LIMIT_UPLOAD", "10"))
    RATE_LIMIT_SIMULATION: int = int(os.getenv("RATE_LIMIT_SIMULATION", "10"))

    # Database connection pool settings
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "10"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "20"))
    DB_POOL_TIMEOUT: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))
    
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Get CORS origins as a list, with sensible defaults based on environment."""
        origins = parse_cors_origins(self.CORS_ORIGINS)
        if origins:
            return origins
        # Default origins based on environment
        if self.is_production:
            return []  # No defaults in production - must be explicitly set
        else:
            return ["http://localhost:5173", "http://localhost:5000", "http://localhost:3000", "http://0.0.0.0:5000"]
    
    @property
    def should_create_schema(self) -> bool:
        """Whether to run Base.metadata.create_all on startup."""
        val = parse_optional_bool("CREATE_SCHEMA")
        if val is not None:
            return val
        return not self.is_production  # Default: True in dev, False in prod
    
    @property
    def should_run_migrations(self) -> bool:
        """Whether to run migrations on startup."""
        val = parse_optional_bool("RUN_MIGRATIONS")
        if val is not None:
            return val
        return not self.is_production  # Default: True in dev, False in prod
    
    @property
    def should_seed_benchmarks(self) -> bool:
        """Whether to seed benchmark data on startup."""
        val = parse_optional_bool("SEED_BENCHMARKS")
        if val is not None:
            return val
        return not self.is_production  # Default: True in dev, False in prod
    
    @property
    def should_seed_demo_data(self) -> bool:
        """Whether to seed demo data on startup."""
        val = parse_optional_bool("SEED_DEMO_DATA")
        if val is not None:
            return val
        return not self.is_production  # Default: True in dev, False in prod
    
    class Config:
        env_file = ".env"
        # .env carries keys consumed outside this model (PORT/NODE_ENV for the
        # Express gateway, CREATE_SCHEMA/SEED_* read via os.getenv in the
        # properties above). Without this, copying .env.example to .env — as
        # that file instructs — fails startup with extra_forbidden.
        extra = "ignore"

    @model_validator(mode="after")
    def bind_signing_secret(self) -> "Settings":
        resolved = resolve_signing_secret(self.SESSION_SECRET, self.SECRET_KEY)
        object.__setattr__(self, "SECRET_KEY", resolved)
        return self

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()

import logging as _cfg_logging
_cfg_logger = _cfg_logging.getLogger("server.core.config")

if settings.is_production:
    # Hard fail before the soft warnings. A missing SESSION_SECRET must not
    # log "server will start" and then keep booting.
    enforce_production_session_secret(settings.ENVIRONMENT, settings.SECRET_KEY)
    _config_errors = []
    if not settings.CORS_ORIGINS:
        _config_errors.append("CORS_ORIGINS env var is not set — no cross-origin requests allowed")
    if settings.ADMIN_MASTER_EMAIL and not settings.ADMIN_MASTER_PASSWORD_HASH:
        _plain = os.getenv("ADMIN_MASTER_PASSWORD", "")
        if _plain:
            import bcrypt as _bcrypt
            _hashed = _bcrypt.hashpw(_plain.encode("utf-8"), _bcrypt.gensalt()).decode("utf-8")
            object.__setattr__(settings, "ADMIN_MASTER_PASSWORD_HASH", _hashed)
            _cfg_logger.info("Auto-hashed ADMIN_MASTER_PASSWORD into ADMIN_MASTER_PASSWORD_HASH")
        else:
            _config_errors.append("ADMIN_MASTER_EMAIL is set but ADMIN_MASTER_PASSWORD_HASH is empty")
    for _err in _config_errors:
        _cfg_logger.warning(f"PRODUCTION CONFIG: {_err}")
    if _config_errors:
        _cfg_logger.warning(f"Found {len(_config_errors)} production config issue(s) — server will start but may be insecure")
