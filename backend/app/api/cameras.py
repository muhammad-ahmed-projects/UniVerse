from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.camera import Camera
from app.models.camera_settings import CameraSettings
from app.models.user import UserRole
from app.schemas.camera import CameraCreate, CameraOut, CameraUpdate
from app.schemas.camera_settings import CameraSettingsOut, CameraSettingsUpdate
from app.services.ws_manager import manager

router = APIRouter(prefix="/cameras", tags=["cameras"])


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
    "", response_model=CameraOut, status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
def create_camera(payload: CameraCreate, db: Session = Depends(get_db)) -> Camera:
    camera = Camera(name=payload.name, location=payload.location, stream_source=payload.stream_source)
    db.add(camera)
    db.commit()
    db.refresh(camera)
    return camera


@router.put(
    "/{camera_id}", response_model=CameraOut,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def update_camera(camera_id: int, payload: CameraUpdate, db: Session = Depends(get_db)) -> Camera:
    camera = _get_camera_or_404(camera_id, db)
    status_changed = "status" in payload.model_dump(exclude_unset=True) and payload.status != camera.status
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(camera, field, value)
    db.commit()
    db.refresh(camera)

    if status_changed:
        await manager.broadcast({
            "type": "camera_status",
            "camera_id": camera.id,
            "status": camera.status.value,
        })
    return camera


@router.delete(
    "/{camera_id}", status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
def delete_camera(camera_id: int, db: Session = Depends(get_db)) -> None:
    camera = _get_camera_or_404(camera_id, db)
    db.delete(camera)
    db.commit()


@router.get(
    "/{camera_id}/settings", response_model=CameraSettingsOut,
    dependencies=[Depends(get_current_user)],
)
def get_camera_settings(camera_id: int, db: Session = Depends(get_db)) -> CameraSettings:
    _get_camera_or_404(camera_id, db)
    settings = db.query(CameraSettings).filter(CameraSettings.camera_id == camera_id).first()
    if settings is None:
        # Defaults, created on first read so the UI always has a row to edit.
        settings = CameraSettings(camera_id=camera_id)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


@router.put(
    "/{camera_id}/settings", response_model=CameraSettingsOut,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
def update_camera_settings(
    camera_id: int, payload: CameraSettingsUpdate, db: Session = Depends(get_db),
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
