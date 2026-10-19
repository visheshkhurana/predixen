"""add source and synced_at to financial_records

Revision ID: b7d3e1a04c21
Revises:
Create Date: 2026-10-12

Adds nullable sync provenance on financial_records. Existing rows stay null,
which the provenance helper treats as unlabeled. Downgrade drops only these
columns.

This revision alters an existing financial_records table. It does not create
that table and it is not run from web startup.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b7d3e1a04c21"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_PROVENANCE_COLUMNS = (
    ("source", sa.String(length=64)),
    ("synced_at", sa.String(length=40)),
    ("synced_fields", sa.JSON()),
)


def _existing_columns(table: str) -> set[str]:
    bind = op.get_bind()
    return {col["name"] for col in sa.inspect(bind).get_columns(table)}


def upgrade() -> None:
    existing = _existing_columns("financial_records")
    with op.batch_alter_table("financial_records") as batch:
        for name, type_ in _PROVENANCE_COLUMNS:
            if name not in existing:
                batch.add_column(sa.Column(name, type_, nullable=True))


def downgrade() -> None:
    existing = _existing_columns("financial_records")
    with op.batch_alter_table("financial_records") as batch:
        for name, _type in reversed(_PROVENANCE_COLUMNS):
            if name in existing:
                batch.drop_column(name)
