"""Startup migration for the leads consent columns added in #176.

The upgrade is the four ADD COLUMN IF NOT EXISTS statements. Existing rows
keep the column default (consent false) and NULL for the other three. A
second run, and a run after the columns were added by hand, leave those
values alone. Downgrade drops the four columns IF EXISTS and can run twice.
"""

from sqlalchemy import create_engine, inspect, text

from server.core.migrations import (
    LEAD_CONSENT_DOWNGRADE_SQL,
    LEAD_CONSENT_UPGRADE_SQL,
    downgrade_lead_consent_columns,
    ensure_lead_consent_columns,
)


def _consent_row(engine, email: str):
    with engine.connect() as conn:
        return conn.execute(
            text(
                "SELECT consent, consent_at, source_page, consent_status "
                "FROM leads WHERE email = :email"
            ),
            {"email": email},
        ).one()


def test_lead_consent_migration_is_idempotent_and_leaves_existing_rows_unconsented():
    assert LEAD_CONSENT_UPGRADE_SQL == (
        "ALTER TABLE leads ADD COLUMN IF NOT EXISTS consent BOOLEAN NOT NULL DEFAULT FALSE;",
        "ALTER TABLE leads ADD COLUMN IF NOT EXISTS consent_at TIMESTAMP;",
        "ALTER TABLE leads ADD COLUMN IF NOT EXISTS source_page VARCHAR(200);",
        "ALTER TABLE leads ADD COLUMN IF NOT EXISTS consent_status VARCHAR(20);",
    )
    assert LEAD_CONSENT_DOWNGRADE_SQL == (
        "ALTER TABLE leads DROP COLUMN IF EXISTS consent;",
        "ALTER TABLE leads DROP COLUMN IF EXISTS consent_at;",
        "ALTER TABLE leads DROP COLUMN IF EXISTS source_page;",
        "ALTER TABLE leads DROP COLUMN IF EXISTS consent_status;",
    )
    joined = "\n".join(LEAD_CONSENT_UPGRADE_SQL + LEAD_CONSENT_DOWNGRADE_SQL).upper()
    assert "UPDATE" not in joined
    assert "CONFIRMED" not in joined

    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE leads (id INTEGER PRIMARY KEY, email VARCHAR)"))
        conn.execute(text("INSERT INTO leads (email) VALUES ('existing@example.com')"))

    ensure_lead_consent_columns(engine)
    ensure_lead_consent_columns(engine)

    row = _consent_row(engine, "existing@example.com")
    assert row.consent in (False, 0)
    assert row.consent_at is None
    assert row.source_page is None
    assert row.consent_status is None

    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO leads (email, consent, consent_at, source_page, consent_status) "
                "VALUES ('later@example.com', 1, '2020-01-01', '/keep', 'confirmed')"
            )
        )
    ensure_lead_consent_columns(engine)
    untouched = _consent_row(engine, "existing@example.com")
    assert untouched.consent in (False, 0)
    assert untouched.consent_at is None
    assert untouched.source_page is None
    assert untouched.consent_status is None
    kept = _consent_row(engine, "later@example.com")
    assert kept.consent in (True, 1)
    assert kept.consent_status == "confirmed"
    assert kept.source_page == "/keep"
    assert kept.consent_at is not None

    downgrade_lead_consent_columns(engine)
    downgrade_lead_consent_columns(engine)
    cols = {col["name"] for col in inspect(engine).get_columns("leads")}
    assert {"consent", "consent_at", "source_page", "consent_status"}.isdisjoint(cols)

    ensure_lead_consent_columns(engine)
    restored = _consent_row(engine, "existing@example.com")
    assert restored.consent in (False, 0)
    assert restored.consent_at is None
    assert restored.source_page is None
    assert restored.consent_status is None

    preset = create_engine("sqlite://")
    with preset.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE leads (
                    id INTEGER PRIMARY KEY,
                    email VARCHAR,
                    consent BOOLEAN NOT NULL DEFAULT FALSE,
                    consent_at TIMESTAMP,
                    source_page VARCHAR(200),
                    consent_status VARCHAR(20)
                )
                """
            )
        )
        conn.execute(text("INSERT INTO leads (email) VALUES ('manual@example.com')"))
    ensure_lead_consent_columns(preset)
    ensure_lead_consent_columns(preset)
    manual = _consent_row(preset, "manual@example.com")
    assert manual.consent in (False, 0)
    assert manual.consent_at is None
    assert manual.source_page is None
    assert manual.consent_status is None
