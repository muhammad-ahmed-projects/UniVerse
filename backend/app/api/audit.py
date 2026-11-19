from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.user import UserRole

router = APIRouter(prefix="/audit-logs", tags=["audit"])


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    actor_id: int | None
    actor_username: str | None
    action: str
    target_type: str | None
    target_id: int | None
    details: dict | None
    ip_address: str | None


class AuditLogPage(BaseModel):
    total: int
    items: list[AuditLogOut]


@router.get("", response_model=AuditLogPage, dependencies=[Depends(require_role(UserRole.ADMIN))])
def list_audit_logs(
    category: str | None = Query(default=None, max_length=20, pattern=r"^[a-z_]+$"),
    q: str | None = Query(default=None, max_length=50),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> AuditLogPage:
    """Newest first. `category` is the part before the dot (auth, user, camera,
    monitoring, person, face, incident, alert); `q` matches the username or action."""
    query = db.query(AuditLog)
    if category:
        query = query.filter(AuditLog.action.like(f"{category}.%"))
    if q:
        like = f"%{q}%"
        query = query.filter(or_(AuditLog.actor_username.ilike(like), AuditLog.action.ilike(like)))
    total = query.count()
    rows = query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).offset(offset).limit(limit).all()
    return AuditLogPage(total=total, items=[AuditLogOut.model_validate(r) for r in rows])
