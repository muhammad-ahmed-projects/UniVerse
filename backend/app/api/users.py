"""Admin user management: list, add, edit role/email/active, reset password, delete.

Guards that keep the system usable and the audit trail intact:
- an admin can't demote, deactivate or delete their own account;
- the last active admin can't be demoted, deactivated or deleted;
- an account that acknowledged/resolved incidents can't be deleted (the
  incident history would lose who reviewed it); deactivate it instead.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.core.security import hash_password
from app.db.session import get_db
from app.models.incident import Incident
from app.models.user import User, UserRole
from app.schemas.auth import PasswordReset, UserOut, UserRegister, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])
admin = require_role(UserRole.ADMIN)


def _get_user_or_404(user_id: int, db: Session) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def _other_active_admins(db: Session, user_id: int) -> int:
    return db.query(User).filter(User.role == UserRole.ADMIN, User.is_active.is_(True), User.id != user_id).count()


def _commit_or_conflict(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Username or email is already in use"
        ) from None


@router.get("", response_model=list[UserOut], dependencies=[Depends(admin)])
def list_users(db: Session = Depends(get_db)) -> list[User]:
    return db.query(User).order_by(User.id).all()


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(admin)])
def create_user(payload: UserRegister, db: Session = Depends(get_db)) -> User:
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")
    user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    _commit_or_conflict(db)
    db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(admin),
) -> User:
    user = _get_user_or_404(user_id, db)
    changes = payload.model_dump(exclude_unset=True)
    # role/is_active can't be null; email may be cleared with null.
    changes = {k: v for k, v in changes.items() if v is not None or k == "email"}
    new_role = changes.get("role", user.role)
    new_active = changes.get("is_active", user.is_active)

    if user.id == current.id and (new_role != user.role or not new_active):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You can't change your own role or deactivate your own account",
        )
    was_active_admin = user.role == UserRole.ADMIN and user.is_active
    stays_active_admin = new_role == UserRole.ADMIN and new_active
    if was_active_admin and not stays_active_admin and _other_active_admins(db, user.id) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="There must always be at least one active admin"
        )
    for field, value in changes.items():
        setattr(user, field, value)
    _commit_or_conflict(db)
    db.refresh(user)
    return user


@router.post("/{user_id}/password", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(admin)])
def reset_password(user_id: int, payload: PasswordReset, db: Session = Depends(get_db)) -> None:
    """Set a new password for an account; every existing session of it is logged out."""
    user = _get_user_or_404(user_id, db)
    user.hashed_password = hash_password(payload.new_password)
    user.password_changed_at = datetime.now(UTC)
    db.commit()


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: Session = Depends(get_db), current: User = Depends(admin)) -> None:
    user = _get_user_or_404(user_id, db)
    if user.id == current.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You can't delete your own account")
    if user.role == UserRole.ADMIN and user.is_active and _other_active_admins(db, user.id) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="There must always be at least one active admin"
        )
    reviewed = (
        db.query(Incident).filter(or_(Incident.acknowledged_by == user.id, Incident.resolved_by == user.id)).first()
    )
    if reviewed is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This account has reviewed incidents, so deleting it would erase who reviewed them. "
            "Deactivate it instead.",
        )
    db.delete(user)
    db.commit()
