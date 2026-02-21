from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from server.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Build engine kwargs with connection pooling
engine_kwargs = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
}

# SQLite doesn't support pool_size/max_overflow
if not settings.DATABASE_URL.startswith("sqlite"):
    engine_kwargs.update({
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        "pool_timeout": settings.DB_POOL_TIMEOUT,
    })
    logger.info(
        f"DB pool config: size={settings.DB_POOL_SIZE}, "
        f"max_overflow={settings.DB_MAX_OVERFLOW}, "
        f"timeout={settings.DB_POOL_TIMEOUT}"
    )

engine = create_engine(settings.DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
