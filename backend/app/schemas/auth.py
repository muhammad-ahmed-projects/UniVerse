import re
from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole

# Same rules as the dashboard's checklist (frontend/src/services/users.ts).
PASSWORD_RULES: list[tuple[str, str]] = [
    (r"[A-Z]", "an uppercase letter (A-Z)"),
    (r"[a-z]", "a lowercase letter (a-z)"),
    (r"[0-9]", "a number (0-9)"),
    (r"[^A-Za-z0-9]", "a special character (e.g. ! @ # $)"),
]


def _check_strength(value: str) -> str:
    missing = [label for pattern, label in PASSWORD_RULES if not re.search(pattern, value)]
    if missing:
        raise ValueError("Password needs " + ", ".join(missing))
    return value


# Applies whenever a password is set (create, sign-up, reset, change); signing
# in with an older password is unaffected. bcrypt uses only the first 72 bytes.
Password = Annotated[str, Field(min_length=8, max_length=72), AfterValidator(_check_strength)]


Username = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$")


class UserRegister(BaseModel):
    username: str = Username
    email: EmailStr | None = None
    password: Password
    role: UserRole = UserRole.SECURITY_OPERATOR


class SignupRequest(BaseModel):
    """Public "Create account": the role is chosen by the admin who approves it."""

    username: str = Username
    email: EmailStr | None = None
    password: Password


class ForgotPassword(BaseModel):
    username: str = Field(min_length=1, max_length=50)


class ApproveRequest(BaseModel):
    role: UserRole = UserRole.SECURITY_OPERATOR


class AccountRequestCounts(BaseModel):
    signups: int
    password_resets: int


class Message(BaseModel):
    detail: str


class UserUpdate(BaseModel):
    """Admin edit of another account. Omitted fields stay as they are."""

    email: EmailStr | None = None
    role: UserRole | None = None
    is_active: bool | None = None


class PasswordReset(BaseModel):
    new_password: Password


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=72)
    new_password: Password


class UserLogin(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str | None
    role: UserRole
    is_active: bool
    created_at: datetime
    is_pending: bool
    password_reset_requested_at: datetime | None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
