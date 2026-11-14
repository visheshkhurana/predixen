from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import OperationalError, DisconnectionError
from server.core.config import settings
import logging
import time

logger = logging.getLogger(__name__)

def pin_postgres_driver(url: str) -> str:
    """Spell out psycopg2 in a bare ``postgres://`` / ``postgresql://`` URL.

    SQLAlchemy 2.1 changed the default driver for ``postgresql://`` from
    psycopg2 to psycopg (v3). Only psycopg2-binary is installed, so without
    this the app cannot connect to the Railway database after the upgrade.
    ``postgres://`` (Heroku/Railway style) is accepted for the same reason.
    URLs that already name a driver are left alone.
    """
    for bare in ("postgresql://", "postgres://"):
        if url.startswith(bare):
            return "postgresql+psycopg2://" + url[len(bare):]
    return url


DATABASE_URL = pin_postgres_driver(settings.DATABASE_URL)

engine_kwargs = {
    "pool_pre_ping": True,
    "pool_recycle": 1800,
}

if not DATABASE_URL.startswith("sqlite"):
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

engine = create_engine(DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
