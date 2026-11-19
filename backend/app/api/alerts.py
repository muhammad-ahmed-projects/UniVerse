from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.alert import Alert, AlertImage
from app.models.camera import Camera
from app.models.user import User
from app.schemas.alert import (
    AlertCreate,
    AlertImageOut,
    AlertOut,
    AlertReview,
    ReviewCounts,
    ReviewStats,
    ReviewStatsRow,
)
from app.services import images, media_store
from app.services.audit import Auditor, get_auditor
from app.services.ws_manager import manager

router = APIRouter(prefix="/alerts", tags=["alerts"])

# An alert's evidence is a short burst (the AI scripts send 3 frames by
# default); the cap stops a misbehaving client from filling the disk.
MAX_IMAGES_PER_ALERT = 10


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


def _counts(confirmed: int, false_alarm: int, unreviewed: int) -> dict:
    reviewed = confirmed + false_alarm
    return {
        "total": reviewed + unreviewed,
        "confirmed": confirmed,
        "false_alarm": false_alarm,
        "unreviewed": unreviewed,
        "precision": round(confirmed / reviewed, 3) if reviewed else None,
        "false_alarm_rate": round(false_alarm / reviewed, 3) if reviewed else None,
    }


# Declared before /{alert_id} so "review-stats" isn't parsed as an alert id.
@router.get("/review-stats", response_model=ReviewStats, dependencies=[Depends(get_current_user)])
def review_stats(db: Session = Depends(get_db)) -> ReviewStats:
    """How many alerts operators confirmed vs marked as false alarms, per alert
    type: the measured precision / false-alarm rate for the evaluation report."""
    rows = (
        db.query(
            Alert.alert_type,
            func.count().filter(Alert.review_status == "confirmed"),
            func.count().filter(Alert.review_status == "false_alarm"),
            func.count().filter(Alert.review_status.is_(None)),
        )
        .group_by(Alert.alert_type)
        .order_by(Alert.alert_type)
        .all()
    )
    by_type = [ReviewStatsRow(alert_type=t, **_counts(c, f, u)) for t, c, f, u in rows]
    overall = _counts(
        sum(r.confirmed for r in by_type), sum(r.false_alarm for r in by_type), sum(r.unreviewed for r in by_type)
    )
    return ReviewStats(overall=ReviewCounts(**overall), by_type=by_type)


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


@router.patch("/{alert_id}/review", response_model=AlertOut)
def review_alert(
    alert_id: int,
    payload: AlertReview,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
    audit: Auditor = Depends(get_auditor),
) -> Alert:
    """Operator verdict on a detection: a real event or a false alarm."""
    alert = db.query(Alert).filter(Alert.id == alert_id).with_for_update().first()
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    if alert.incident_id is not None and payload.review_status != "confirmed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This alert became an incident, so it was confirmed. Resolve the incident instead.",
        )
    alert.review_status = payload.review_status
    alert.reviewed_by = actor.id if payload.review_status else None
    alert.reviewed_at = datetime.now(UTC) if payload.review_status else None
    audit.log(
        actor, "alert.review", "alert", alert.id, verdict=payload.review_status or "cleared", type=alert.alert_type
    )
    db.commit()
    db.refresh(alert)
    background_tasks.add_task(
        manager.broadcast,
        {"type": "alert_review", "alert_id": alert.id, "review_status": alert.review_status},
    )
    return alert


@router.post(
    "/{alert_id}/images",
    response_model=AlertImageOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(get_current_user)],
)
def upload_alert_image(
    alert_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> AlertImage:
    """Attach an evidence snapshot to an alert (sent by the AI scripts right
    after they raise the alert)."""
    # Row lock so concurrent uploads can't race past MAX_IMAGES_PER_ALERT.
    alert = db.query(Alert).filter(Alert.id == alert_id).with_for_update().first()
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    if len(alert.images) >= MAX_IMAGES_PER_ALERT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An alert can have at most {MAX_IMAGES_PER_ALERT} images",
        )

    jpeg = images.encode_jpeg(images.decode(images.read_upload(file)))
    file_name = media_store.save("evidence", jpeg)
    image = AlertImage(alert_id=alert.id, file_name=file_name)
    db.add(image)
    try:
        db.commit()
    except Exception:
        media_store.delete("evidence", file_name)
        raise
    db.refresh(image)

    background_tasks.add_task(
        manager.broadcast,
        {
            "type": "alert_image",
            "alert_id": alert.id,
            "incident_id": alert.incident_id,
            "image": AlertImageOut.model_validate(image).model_dump(mode="json"),
        },
    )
    return image


@router.get(
    "/{alert_id}/images/{image_id}",
    response_class=FileResponse,
    dependencies=[Depends(get_current_user)],
)
def get_alert_image(alert_id: int, image_id: int, db: Session = Depends(get_db)) -> FileResponse:
    image = db.get(AlertImage, image_id)
    path = media_store.path_for("evidence", image.file_name) if image and image.alert_id == alert_id else None
    if path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    # Evidence never changes once stored, so the browser may cache it.
    return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=86400"})
