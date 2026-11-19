"""Recording audit-log entries from route handlers.

Usage (the entry joins the request's DB transaction and is committed with
the change it describes, so a failed change leaves no misleading entry):

    def delete_camera(..., audit: Auditor = Depends(get_auditor)):
        audit.log(current_user, "camera.delete", "camera", camera.id, name=camera.name)
        db.delete(camera)
        db.commit()

For events with nothing else to commit (a failed login), use commit=True.
"""

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.user import User


class Auditor:
    def __init__(self, db: Session, ip_address: str | None) -> None:
        self.db = db
        self.ip_address = ip_address

    def log(
        self,
        actor: User | None,
        action: str,
        target_type: str | None = None,
        target_id: int | None = None,
        commit: bool = False,
        actor_username: str | None = None,
        **details: object,
    ) -> None:
        self.db.add(
            AuditLog(
                actor_id=actor.id if actor else None,
                actor_username=actor.username if actor else actor_username,
                action=action,
                target_type=target_type,
                target_id=target_id,
                details={k: v for k, v in details.items() if v is not None} or None,
                ip_address=self.ip_address,
            )
        )
        if commit:
            self.db.commit()


def get_auditor(request: Request, db: Session = Depends(get_db)) -> Auditor:
    return Auditor(db, request.client.host if request.client else None)
