from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.alert import Alert
from app.models.camera import Camera
from app.models.incident import Incident
from app.models.user import User
from app.schemas.incident import IncidentCreate, IncidentOut, IncidentStatus
from app.services.ws_manager import manager

router = APIRouter(prefix="/incidents", tags=["incidents"])


def _get_incident_or_404(incident_id: int, db: Session, lock: bool = False) -> Incident:
    # lock=True takes a row lock so concurrent acknowledge/resolve calls are serialized
    # and the status check below can't be raced.
    q = db.query(Incident).filter(Incident.id == incident_id)
    incident = (q.with_for_update() if lock else q).first()
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    return incident


@router.get("", response_model=list[IncidentOut], dependencies=[Depends(get_current_user)])
def list_incidents(
    status_filter: IncidentStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[Incident]:
    q = db.query(Incident)
    if status_filter is not None:
        q = q.filter(Incident.status == status_filter)
    return q.order_by(Incident.created_at.desc(), Incident.id.desc()).offset(offset).limit(limit).all()


@router.get("/{incident_id}", response_model=IncidentOut, dependencies=[Depends(get_current_user)])
def get_incident(incident_id: int, db: Session = Depends(get_db)) -> Incident:
    return _get_incident_or_404(incident_id, db)


@router.post(
    "",
    response_model=IncidentOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(get_current_user)],
)
def create_incident(
    payload: IncidentCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> Incident:
    """Promote an AI alert to a human-reviewed incident. Per the proposal's
    privacy requirement, this is an explicit human action -- alerts never
    auto-promote themselves.
    """
    if db.get(Camera, payload.camera_id) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="camera_id does not exist")

    source_alert = None
    if payload.source_alert_id is not None:
        # Row lock so two operators promoting the same alert at once can't both succeed.
        source_alert = db.query(Alert).filter(Alert.id == payload.source_alert_id).with_for_update().first()
        if source_alert is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="source_alert_id does not exist")
        if source_alert.incident_id is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This alert is already linked to an incident",
            )
        if source_alert.camera_id != payload.camera_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="source_alert_id belongs to a different camera",
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

    background_tasks.add_task(
        manager.broadcast, {"type": "incident_update", "id": incident.id, "status": incident.status}
    )
    return incident


@router.patch("/{incident_id}/acknowledge", response_model=IncidentOut)
def acknowledge_incident(
    incident_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Incident:
    incident = _get_incident_or_404(incident_id, db, lock=True)
    if incident.status != "open":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incident is not open")

    incident.status = "acknowledged"
    incident.acknowledged_by = current_user.id
    incident.acknowledged_at = datetime.now(UTC)
    db.commit()
    db.refresh(incident)

    background_tasks.add_task(
        manager.broadcast, {"type": "incident_update", "id": incident.id, "status": incident.status}
    )
    return incident


@router.patch("/{incident_id}/resolve", response_model=IncidentOut)
def resolve_incident(
    incident_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Incident:
    incident = _get_incident_or_404(incident_id, db, lock=True)
    if incident.status == "resolved":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incident is already resolved")
    if incident.status != "acknowledged":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incident must be acknowledged before it can be resolved",
        )

    incident.status = "resolved"
    incident.resolved_by = current_user.id
    incident.resolved_at = datetime.now(UTC)
    db.commit()
    db.refresh(incident)

    background_tasks.add_task(
        manager.broadcast, {"type": "incident_update", "id": incident.id, "status": incident.status}
    )
    return incident
