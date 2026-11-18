from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.camera import Camera, CameraStatus
from app.models.camera_settings import CameraSettings
from app.models.user import UserRole
from app.schemas.camera import CameraCreate, CameraHeartbeat, CameraOut, CameraUpdate
from app.schemas.camera_settings import CameraSettingsOut, CameraSettingsUpdate
from app.services.frame_store import frame_store
from app.services.ws_manager import manager

router = APIRouter(prefix="/cameras", tags=["cameras"])

# A downscaled live-view JPEG is ~30-80 KB; 1 MB leaves room for a large
# frame without letting a client push arbitrary amounts into memory.
MAX_FRAME_BYTES = 1024 * 1024
JPEG_MAGIC = b"\xff\xd8\xff"


def _get_camera_or_404(camera_id: int, db: Session) -> Camera:
    camera = db.get(Camera, camera_id)
    if camera is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found")
    return camera


@router.get("", response_model=list[CameraOut], dependencies=[Depends(get_current_user)])
def list_cameras(db: Session = Depends(get_db)) -> list[Camera]:
    return db.query(Camera).order_by(Camera.id).all()


@router.get("/{camera_id}", response_model=CameraOut, dependencies=[Depends(get_current_user)])
def get_camera(camera_id: int, db: Session = Depends(get_db)) -> Camera:
    return _get_camera_or_404(camera_id, db)


@router.post(
    "",
    response_model=CameraOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
def create_camera(payload: CameraCreate, db: Session = Depends(get_db)) -> Camera:
    camera = Camera(name=payload.name, location=payload.location, stream_source=payload.stream_source)
    db.add(camera)
    db.commit()
    db.refresh(camera)
    return camera


@router.put(
    "/{camera_id}",
    response_model=CameraOut,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
def update_camera(
    camera_id: int,
    payload: CameraUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> Camera:
    camera = _get_camera_or_404(camera_id, db)
    changes = payload.model_dump(exclude_unset=True)
    status_changed = "status" in changes and changes["status"] != camera.status
    for field, value in changes.items():
        setattr(camera, field, value)
    db.commit()
    db.refresh(camera)

    if status_changed:
        background_tasks.add_task(manager.broadcast, _status_message(camera))
    return camera


@router.post(
    "/{camera_id}/heartbeat",
    response_model=CameraOut,
    dependencies=[Depends(get_current_user)],
)
def camera_heartbeat(
    camera_id: int,
    payload: CameraHeartbeat,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> Camera:
    """Status report from a camera-health process (any authenticated user, so
    a security_operator service login can run it). Broadcasts only on change.
    """
    camera = _get_camera_or_404(camera_id, db)
    new_status = CameraStatus(payload.status)
    status_changed = camera.status != new_status
    camera.status = new_status
    if new_status == CameraStatus.ONLINE:
        camera.last_seen_at = datetime.now(UTC)
    db.commit()
    db.refresh(camera)

    if status_changed:
        background_tasks.add_task(manager.broadcast, _status_message(camera))
    return camera


def _status_message(camera: Camera) -> dict:
    return {"type": "camera_status", "camera_id": camera.id, "status": camera.status.value}


def _existing_camera_id(camera_id: int, db: Session = Depends(get_db)) -> int:
    """Sync dependency (runs in the threadpool) so the async frame route below
    never does blocking DB work on the event loop."""
    _get_camera_or_404(camera_id, db)
    return camera_id


@router.post(
    "/{camera_id}/frame",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_current_user)],
)
async def publish_frame(
    request: Request,
    camera_id_checked: int = Depends(_existing_camera_id),
    source: str = Query(default="script", pattern=r"^[a-z0-9_]{1,40}$"),
    priority: int = Query(default=1, ge=0, le=9),
) -> Response:
    """Live-view frame from an AI script: the raw JPEG is the request body
    (Content-Type: image/jpeg). Dashboards receive it over /ws/stream.
    `priority`: detection scripts send 1, the health monitor 0 (see FrameStore.publish)."""
    if request.headers.get("content-type", "").split(";")[0].strip() != "image/jpeg":
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Send the frame as image/jpeg")

    body = bytearray()
    async for chunk in request.stream():
        body += chunk
        if len(body) > MAX_FRAME_BYTES:
            raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="Frame is larger than 1 MB")
    if not body.startswith(JPEG_MAGIC):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Body is not a JPEG image")

    if not frame_store.publish(camera_id_checked, bytes(body), source, priority):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Another script is already streaming camera {camera_id_checked}",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/{camera_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
def delete_camera(camera_id: int, db: Session = Depends(get_db)) -> None:
    camera = _get_camera_or_404(camera_id, db)
    db.delete(camera)
    db.commit()


@router.get(
    "/{camera_id}/settings",
    response_model=CameraSettingsOut,
    dependencies=[Depends(get_current_user)],
)
def get_camera_settings(camera_id: int, db: Session = Depends(get_db)) -> CameraSettings:
    _get_camera_or_404(camera_id, db)
    settings = db.query(CameraSettings).filter(CameraSettings.camera_id == camera_id).first()
    if settings is None:
        # Defaults, created on first read so the UI always has a row to edit.
        # Two first reads can race (e.g. dashboard + an AI script starting); the
        # unique camera_id constraint makes the loser fall back to the winner's row.
        settings = CameraSettings(camera_id=camera_id)
        db.add(settings)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            settings = db.query(CameraSettings).filter(CameraSettings.camera_id == camera_id).one()
        else:
            db.refresh(settings)
    return settings


@router.put(
    "/{camera_id}/settings",
    response_model=CameraSettingsOut,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
def update_camera_settings(
    camera_id: int,
    payload: CameraSettingsUpdate,
    db: Session = Depends(get_db),
) -> CameraSettings:
    _get_camera_or_404(camera_id, db)
    settings = db.query(CameraSettings).filter(CameraSettings.camera_id == camera_id).first()
    if settings is None:
        settings = CameraSettings(camera_id=camera_id)
        db.add(settings)
    for field, value in payload.model_dump().items():
        setattr(settings, field, value)
    db.commit()
    db.refresh(settings)
    return settings
