"""Startup migration for leads campaign columns.

The upgrade is three nullable ADD COLUMN IF NOT EXISTS statements. Existing
rows stay NULL. A second run does not clear a value written after the first.
No UPDATE, no default, no IP column. Production leaves RUN_MIGRATIONS off,
so `_run_deferred_startup` calls this in its own try block.
"""

from sqlalchemy import create_engine, inspect, text

from server.core.migrations import LEAD_UTM_UPGRADE_SQL, ensure_lead_utm_columns


def _utm_row(engine, email: str):
    with engine.connect() as conn:
        return conn.execute(
            text(
                "SELECT utm_source, utm_medium, utm_campaign FROM leads WHERE email = :email"
            ),
            {"email": email},
        ).one()


def test_lead_utm_sql_is_nullable_and_does_not_backfill():
    assert LEAD_UTM_UPGRADE_SQL == (
        "ALTER TABLE leads ADD COLUMN IF NOT EXISTS utm_source VARCHAR(200);",
        "ALTER TABLE leads ADD COLUMN IF NOT EXISTS utm_medium VARCHAR(200);",
        "ALTER TABLE leads ADD COLUMN IF NOT EXISTS utm_campaign VARCHAR(200);",
    )
    joined = "\n".join(LEAD_UTM_UPGRADE_SQL).upper()
    assert "UPDATE" not in joined
    assert "NOT NULL" not in joined
    assert "DEFAULT" not in joined
    assert "IP" not in joined


def test_lead_utm_migration_is_idempotent_and_leaves_existing_rows_null():
    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE leads (id INTEGER PRIMARY KEY, email VARCHAR)"))
        conn.execute(text("INSERT INTO leads (email) VALUES ('existing@example.com')"))

    ensure_lead_utm_columns(engine)
    ensure_lead_utm_columns(engine)

    cols = {col["name"]: col for col in inspect(engine).get_columns("leads")}
    for name in ("utm_source", "utm_medium", "utm_campaign"):
        assert name in cols
        assert cols[name]["nullable"] is True
    assert "fbclid" not in cols
    assert "gclid" not in cols
    assert "ip_address" not in cols

    row = _utm_row(engine, "existing@example.com")
    assert row.utm_source is None
    assert row.utm_medium is None
    assert row.utm_campaign is None

    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE leads SET utm_source = 'google', utm_medium = 'cpc', "
                "utm_campaign = 'spring' WHERE email = 'existing@example.com'"
            )
        )
    ensure_lead_utm_columns(engine)
    kept = _utm_row(engine, "existing@example.com")
    assert kept.utm_source == "google"
    assert kept.utm_medium == "cpc"
    assert kept.utm_campaign == "spring"


def test_lead_utm_migration_skips_a_missing_table():
    engine = create_engine("sqlite://")
    ensure_lead_utm_columns(engine)
    ensure_lead_utm_columns(engine)
    assert inspect(engine).get_table_names() == []


def test_startup_calls_ensure_lead_utm_columns_when_migrations_disabled(monkeypatch):
    """The ADD COLUMN is not behind RUN_MIGRATIONS. It has its own try and warning."""
    import ast
    import asyncio
    import logging
    from pathlib import Path
    from unittest.mock import MagicMock

    main_path = Path(__file__).resolve().parents[1] / "main.py"
    main_src = main_path.read_text()
    start = main_src.index("async def _run_deferred_startup")
    flag = main_src.index("if settings.should_run_migrations", start)
    call = main_src.index("ensure_lead_utm_columns(engine)", start)
    assert start < call < flag
    assert (
        '''try:
            from server.core.migrations import ensure_lead_utm_columns
            ensure_lead_utm_columns(engine)
            logger.info("Ensured lead utm columns exist")
        except Exception as e:
            logger.warning(f"Could not ensure lead utm columns: {e}")'''
        in main_src
    )

    monkeypatch.setenv("RUN_MIGRATIONS", "false")
    monkeypatch.setenv("CREATE_SCHEMA", "false")
    monkeypatch.setenv("SEED_BENCHMARKS", "false")
    monkeypatch.setenv("SEED_DEMO_DATA", "false")

    from server.core.config import settings
    import server.core.migrations as migrations

    assert settings.should_run_migrations is False

    calls = []

    def _record(engine):
        calls.append(("utm", engine))

    def _consent(engine):
        calls.append(("consent", engine))

    def _migrations_must_not_run(engine):
        raise AssertionError("run_migrations ran while should_run_migrations is false")

    monkeypatch.setattr(migrations, "ensure_lead_utm_columns", _record)
    monkeypatch.setattr(migrations, "ensure_lead_consent_columns", _consent)
    monkeypatch.setattr(migrations, "run_migrations", _migrations_must_not_run)

    def _drop_task(coro, *args, **kwargs):
        coro.close()
        return MagicMock()

    monkeypatch.setattr(asyncio, "create_task", _drop_task)

    module = ast.parse(main_src)
    startup = next(
        node
        for node in module.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "_run_deferred_startup"
    )
    isolated = ast.Module(body=[startup], type_ignores=[])
    ast.fix_missing_locations(isolated)
    namespace = {
        "settings": settings,
        "logger": logging.getLogger("test.startup.utm"),
        "engine": object(),
        "Base": object(),
        "SessionLocal": lambda: MagicMock(),
        "_startup_state": {"ready": False, "error": None},
    }
    exec(compile(isolated, str(main_path), "exec"), namespace)

    asyncio.run(namespace["_run_deferred_startup"]())

    assert namespace["_startup_state"]["error"] is None
    assert ("utm", namespace["engine"]) in calls
    assert ("consent", namespace["engine"]) in calls
