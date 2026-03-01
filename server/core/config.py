import os
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

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./founderconsole.db")
    SECRET_KEY: str = os.getenv("SESSION_SECRET", "founderconsole-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))  # 15 min default, refresh token extends session
    MASTER_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("MASTER_TOKEN_EXPIRE_MINUTES", "30"))  # 30 min for admin

    FEATURE_INVESTOR_MODE: bool = os.getenv("FEATURE_INVESTOR_MODE", "false").lower() == "true"

    ADMIN_MASTER_EMAIL: str = os.getenv("ADMIN_MASTER_EMAIL", "")
    ADMIN_MASTER_PASSWORD_HASH: str = os.getenv("ADMIN_MASTER_PASSWORD_HASH", "")

    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GITHUB_CLIENT_ID: str = os.getenv("GITHUB_CLIENT_ID", "")
    GITHUB_CLIENT_SECRET: str = os.getenv("GITHUB_CLIENT_SECRET", "")

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

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()

import logging as _cfg_logging
_cfg_logger = _cfg_logging.getLogger("server.core.config")

if settings.is_production:
    _config_errors = []
    if settings.SECRET_KEY == "founderconsole-secret-key-change-in-production":
        _config_errors.append("SESSION_SECRET env var is not set — using default key is insecure")
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
