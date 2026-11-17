from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.alert import Alert
from app.models.camera import Camera
from app.schemas.alert import AlertCreate, AlertOut
from app.services.ws_manager import manager

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertOut], dependencies=[Depends(get_current_user)])
def list_alerts(
    camera_id: int | None = Query(default=None, gt=0),
    unresolved_only: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[Alert]:
    q = db.query(Alert)
    if camera_id is not None:
        q = q.filter(Alert.camera_id == camera_id)
    if unresolved_only:
        q = q.filter(Alert.incident_id.is_(None))
    return q.order_by(Alert.triggered_at.desc(), Alert.id.desc()).offset(offset).limit(limit).all()


@router.get("/{alert_id}", response_model=AlertOut, dependencies=[Depends(get_current_user)])
def get_alert(alert_id: int, db: Session = Depends(get_db)) -> Alert:
    alert = db.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    return alert


@router.post(
    "",
    response_model=AlertOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(get_current_user)],
)
def create_alert(
    payload: AlertCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> Alert:
    if db.get(Camera, payload.camera_id) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="camera_id does not exist")

    alert = Alert(**payload.model_dump())
    db.add(alert)
    db.commit()
    db.refresh(alert)

    background_tasks.add_task(
        manager.broadcast,
        {
            "type": "alert",
            "id": alert.id,
            "camera_id": alert.camera_id,
            "alert_type": alert.alert_type,
            "priority": alert.priority,
            "message": alert.message,
            "triggered_at": alert.triggered_at.isoformat(),
        },
    )
    return alert
