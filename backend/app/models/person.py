from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Person(Base):
    """A registered individual authorized for face-recognition matching.

    Embeddings live in a separate table since a person may register
    multiple samples (one row per photo; the recognizer matches against
    the best-scoring sample) without widening this table.
    """

    __tablename__ = "people"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Most recent face-recognition match, reported by face_recognition.py.
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_camera_id: Mapped[int | None] = mapped_column(
        ForeignKey("cameras.id", ondelete="SET NULL"), nullable=True
    )

    faces: Mapped[list["FaceEmbedding"]] = relationship(
        back_populates="person",
        lazy="selectin",
        order_by="FaceEmbedding.id",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    @property
    def face_count(self) -> int:
        return len(self.faces)


class FaceEmbedding(Base):
    __tablename__ = "face_embeddings"

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id", ondelete="CASCADE"), nullable=False)
    # ArcFace embedding vector, stored as a JSON array of floats (512-dim for buffalo_l).
    embedding: Mapped[list[float]] = mapped_column(JSON, nullable=False)
    # Cropped face thumbnail under MEDIA_DIR/faces/, so admins can see which photos were registered.
    image_file: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    person: Mapped[Person] = relationship(back_populates="faces")
