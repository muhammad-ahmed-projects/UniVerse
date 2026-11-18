import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    SECURITY_OPERATOR = "security_operator"
    # Service account for the AI scripts: the only non-admin role that may read
    # face embeddings (biometric data) and report face sightings.
    AI_SERVICE = "ai_service"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Tokens issued before this moment are rejected, so changing or resetting a
    # password logs out every existing session of that account.
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def token_is_current(self, issued_at: float | None) -> bool:
        if self.password_changed_at is None:
            return True
        return isinstance(issued_at, int | float) and issued_at >= self.password_changed_at.timestamp()
