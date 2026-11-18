from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.auth import (
    ForgotPassword,
    Message,
    PasswordChange,
    SignupRequest,
    Token,
    UserOut,
    UserRegister,
)
from app.services.ws_manager import manager

router = APIRouter(prefix="/auth", tags=["auth"])

# Open account requests allowed at once before /auth/signup refuses more.
MAX_PENDING_SIGNUPS = 20


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(
    payload: UserRegister,
    db: Session = Depends(get_db),
    # Only an existing admin can create new accounts -- no open self-registration.
    _current_admin: User = Depends(require_role(UserRole.ADMIN)),
) -> User:
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")

    user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> Token:
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Checked only after the password, so these states aren't revealed to someone guessing.
    if user.is_pending:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is waiting for an admin to approve it. Try again once they have.",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

    access_token = create_access_token(subject=user.username, role=user.role.value)
    return Token(access_token=access_token)


@router.post("/signup", response_model=Message, status_code=status.HTTP_202_ACCEPTED)
def signup(payload: SignupRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)) -> Message:
    """Public "Create account". The account is pending (can't sign in) until an
    admin approves it on the Users page and picks its role."""
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="That username is already taken")
    # A public endpoint that creates rows: cap the queue so it can't be flooded.
    if db.query(User).filter(User.is_pending.is_(True)).count() >= MAX_PENDING_SIGNUPS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many account requests are waiting already. Ask an admin to review them.",
        )
    db.add(
        User(
            username=payload.username,
            email=payload.email,
            hashed_password=hash_password(payload.password),
            role=UserRole.SECURITY_OPERATOR,
            is_active=False,
            is_pending=True,
        )
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="That username or email is already in use"
        ) from None
    background_tasks.add_task(manager.broadcast, {"type": "account_request", "kind": "signup"})
    return Message(detail="Request sent. You can sign in once an admin approves your account.")


@router.post("/forgot-password", response_model=Message, status_code=status.HTTP_202_ACCEPTED)
def forgot_password(
    payload: ForgotPassword, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
) -> Message:
    """Ask an admin to reset your password (no email server: the admin sets a
    new one on the Users page and tells you). The reply is the same whether
    or not the username exists, so it can't be used to discover accounts."""
    user = db.query(User).filter(User.username == payload.username).first()
    if user is not None and user.is_active and not user.is_pending and user.password_reset_requested_at is None:
        user.password_reset_requested_at = datetime.now(UTC)
        db.commit()
        background_tasks.add_task(manager.broadcast, {"type": "account_request", "kind": "password_reset"})
    return Message(
        detail="If that account exists, an admin has been asked to reset its password. They will give you the new one."
    )


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.post("/change-password", response_model=Token)
def change_password(
    payload: PasswordChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Token:
    """Change your own password. Other sessions of the account are logged out;
    this one continues with the returned token."""
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    if verify_password(payload.new_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="The new password must differ from the current one"
        )
    current_user.hashed_password = hash_password(payload.new_password)
    current_user.password_changed_at = datetime.now(UTC)
    db.commit()
    return Token(access_token=create_access_token(subject=current_user.username, role=current_user.role.value))
