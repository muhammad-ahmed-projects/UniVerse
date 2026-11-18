"""users.password_changed_at (log out old sessions after a password change)

Revision ID: c4d2e8f1a9b3
Revises: b3c1d9e4f2a7
Create Date: 2026-11-18 19:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c4d2e8f1a9b3"
down_revision: str | Sequence[str] | None = "b3c1d9e4f2a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "password_changed_at")
