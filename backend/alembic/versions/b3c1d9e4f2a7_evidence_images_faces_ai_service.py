"""evidence images, face samples, sightings, ai_service role

- alert_images: evidence snapshots per alert (replaces the never-used
  alerts.evidence_path column).
- face_embeddings.image_file: cropped face thumbnail for each sample.
- people.last_seen_at / last_seen_camera_id: latest face-recognition match.
- camera_settings.face_match_threshold: configurable similarity threshold.
- user_role gains AI_SERVICE for the AI scripts' service account.

Revision ID: b3c1d9e4f2a7
Revises: a7a79d74c895
Create Date: 2026-11-18 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b3c1d9e4f2a7"
down_revision: str | Sequence[str] | None = "a7a79d74c895"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # PostgreSQL enum labels are the Python enum *names* (see the initial migration).
    op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'AI_SERVICE'")

    op.create_table(
        "alert_images",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("alert_id", sa.Integer(), nullable=False),
        sa.Column("file_name", sa.String(length=64), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["alert_id"], ["alerts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_alert_images_alert_id"), "alert_images", ["alert_id"], unique=False)
    op.drop_column("alerts", "evidence_path")

    op.add_column("face_embeddings", sa.Column("image_file", sa.String(length=64), nullable=True))

    op.add_column("people", sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("people", sa.Column("last_seen_camera_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "people_last_seen_camera_id_fkey", "people", "cameras", ["last_seen_camera_id"], ["id"], ondelete="SET NULL"
    )

    # server_default fills existing rows; the ORM default covers new ones.
    op.add_column(
        "camera_settings",
        sa.Column("face_match_threshold", sa.Float(), server_default=sa.text("0.45"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("camera_settings", "face_match_threshold")

    op.drop_constraint("people_last_seen_camera_id_fkey", "people", type_="foreignkey")
    op.drop_column("people", "last_seen_camera_id")
    op.drop_column("people", "last_seen_at")

    op.drop_column("face_embeddings", "image_file")

    op.add_column("alerts", sa.Column("evidence_path", sa.String(length=500), nullable=True))
    op.drop_index(op.f("ix_alert_images_alert_id"), table_name="alert_images")
    op.drop_table("alert_images")

    # PostgreSQL can't drop an enum label, so rebuild the type without it.
    op.execute("DELETE FROM users WHERE role = 'AI_SERVICE'")
    op.execute("ALTER TYPE user_role RENAME TO user_role_old")
    op.execute("CREATE TYPE user_role AS ENUM ('ADMIN', 'SECURITY_OPERATOR')")
    op.execute("ALTER TABLE users ALTER COLUMN role TYPE user_role USING role::text::user_role")
    op.execute("DROP TYPE user_role_old")
