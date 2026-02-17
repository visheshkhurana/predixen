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
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    FEATURE_INVESTOR_MODE: bool = os.getenv("FEATURE_INVESTOR_MODE", "false").lower() == "true"
    
    ADMIN_MASTER_EMAIL: str = os.getenv("ADMIN_MASTER_EMAIL", "")
    ADMIN_MASTER_PASSWORD: str = os.getenv("ADMIN_MASTER_PASSWORD", "")
    
    # Environment: "development" or "production"
    ENVIRONMENT: str = os.getenv("NODE_ENV", os.getenv("ENVIRONMENT", "development"))
    
    # CORS configuration - comma-separated list of allowed origins
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "")
    
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
