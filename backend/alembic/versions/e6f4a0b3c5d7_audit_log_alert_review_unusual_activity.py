"""audit log, alert review (false alarms), unusual-activity settings

Revision ID: e6f4a0b3c5d7
Revises: d5e3f9a2b4c6
Create Date: 2026-11-19 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e6f4a0b3c5d7"
down_revision: str | Sequence[str] | None = "d5e3f9a2b4c6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=True),
        sa.Column("actor_username", sa.String(length=50), nullable=True),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("target_type", sa.String(length=30), nullable=True),
        sa.Column("target_id", sa.Integer(), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_logs_created_at"), "audit_logs", ["created_at"], unique=False)
    op.create_index(op.f("ix_audit_logs_action"), "audit_logs", ["action"], unique=False)

    op.add_column("alerts", sa.Column("review_status", sa.String(length=20), nullable=True))
    op.add_column("alerts", sa.Column("reviewed_by", sa.Integer(), nullable=True))
    op.add_column("alerts", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key("alerts_reviewed_by_fkey", "alerts", "users", ["reviewed_by"], ["id"], ondelete="SET NULL")
    # Alerts already promoted to an incident were confirmed by a human.
    op.execute("UPDATE alerts SET review_status = 'confirmed' WHERE incident_id IS NOT NULL")

    op.add_column("camera_settings", sa.Column("crowd_threshold", sa.Integer(), server_default="5", nullable=False))
    op.add_column("camera_settings", sa.Column("running_speed", sa.Float(), server_default="0.6", nullable=False))
    op.add_column("camera_settings", sa.Column("abandoned_seconds", sa.Float(), server_default="30", nullable=False))
    op.add_column("camera_settings", sa.Column("fall_seconds", sa.Float(), server_default="2", nullable=False))


def downgrade() -> None:
    op.drop_column("camera_settings", "fall_seconds")
    op.drop_column("camera_settings", "abandoned_seconds")
    op.drop_column("camera_settings", "running_speed")
    op.drop_column("camera_settings", "crowd_threshold")

    op.drop_constraint("alerts_reviewed_by_fkey", "alerts", type_="foreignkey")
    op.drop_column("alerts", "reviewed_at")
    op.drop_column("alerts", "reviewed_by")
    op.drop_column("alerts", "review_status")

    op.drop_index(op.f("ix_audit_logs_action"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_created_at"), table_name="audit_logs")
    op.drop_table("audit_logs")
