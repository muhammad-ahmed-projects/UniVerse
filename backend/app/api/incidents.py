from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.alert import Alert
from app.models.camera import Camera
from app.models.incident import Incident
from app.models.user import User
from app.schemas.alert import ALLOWED_PRIORITIES
from app.schemas.incident import IncidentCreate, IncidentOut

router = APIRouter(prefix="/incidents", tags=["incidents"])


def _get_incident_or_404(incident_id: int, db: Session) -> Incident:
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    return incident


@router.get("", response_model=list[IncidentOut], dependencies=[Depends(get_current_user)])
def list_incidents(
    status_filter: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
) -> list[Incident]:
    q = db.query(Incident)
    if status_filter is not None:
        q = q.filter(Incident.status == status_filter)
    return q.order_by(Incident.created_at.desc()).all()


@router.get("/{incident_id}", response_model=IncidentOut, dependencies=[Depends(get_current_user)])
def get_incident(incident_id: int, db: Session = Depends(get_db)) -> Incident:
    return _get_incident_or_404(incident_id, db)


@router.post(
    "", response_model=IncidentOut, status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(get_current_user)],
)
def create_incident(payload: IncidentCreate, db: Session = Depends(get_db)) -> Incident:
    """Promote an AI alert to a human-reviewed incident. Per the proposal's
    privacy requirement, this is an explicit human action -- alerts never
    auto-promote themselves.
    """
    if db.get(Camera, payload.camera_id) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="camera_id does not exist")
    if payload.priority not in ALLOWED_PRIORITIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"priority must be one of {sorted(ALLOWED_PRIORITIES)}",
        )

    source_alert = None
    if payload.source_alert_id is not None:
        source_alert = db.get(Alert, payload.source_alert_id)
        if source_alert is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="source_alert_id does not exist")
        if source_alert.incident_id is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This alert is already linked to an incident",
            )

    incident = Incident(
        camera_id=payload.camera_id,
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
    )
    db.add(incident)
    db.flush()  # assign incident.id before linking the alert

    if source_alert is not None:
        source_alert.incident_id = incident.id

    db.commit()
    db.refresh(incident)
    return incident


@router.patch("/{incident_id}/acknowledge", response_model=IncidentOut)
def acknowledge_incident(
    incident_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
) -> Incident:
    incident = _get_incident_or_404(incident_id, db)
    if incident.status != "open":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incident is not open")

    incident.status = "acknowledged"
    incident.acknowledged_by = current_user.id
    incident.acknowledged_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(incident)
    return incident


@router.patch("/{incident_id}/resolve", response_model=IncidentOut)
def resolve_incident(
    incident_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
) -> Incident:
    incident = _get_incident_or_404(incident_id, db)
    if incident.status == "resolved":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incident is already resolved")

    incident.status = "resolved"
    incident.resolved_by = current_user.id
    incident.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(incident)
    return incident
