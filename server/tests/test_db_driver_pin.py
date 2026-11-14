"""SQLAlchemy 2.1 maps a bare postgresql:// URL to psycopg (v3), which is not
installed. db.py must keep pointing such URLs at psycopg2."""
import pytest
from sqlalchemy.engine import make_url

from server.core.db import pin_postgres_driver


@pytest.mark.parametrize("url", [
    "postgresql://u:p@host:5432/db",
    "postgres://u:p@host:5432/db",
])
def test_bare_postgres_urls_use_psycopg2(url):
    pinned = pin_postgres_driver(url)
    assert make_url(pinned).drivername == "postgresql+psycopg2"
    assert pinned.endswith("u:p@host:5432/db")


@pytest.mark.parametrize("url", [
    "postgresql+psycopg2://u:p@host/db",
    "postgresql+psycopg://u:p@host/db",
    "sqlite:///./founderconsole.db",
])
def test_explicit_drivers_and_sqlite_are_untouched(url):
    assert pin_postgres_driver(url) == url


def test_the_installed_driver_is_the_one_we_pin():
    import psycopg2  # noqa: F401  (psycopg2-binary must stay a dependency)

    from sqlalchemy import create_engine
    engine = create_engine(pin_postgres_driver("postgresql://u:p@localhost/db"))
    assert engine.dialect.driver == "psycopg2"
