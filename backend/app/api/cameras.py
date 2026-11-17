from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.camera import Camera
from app.models.user import UserRole
from app.schemas.camera import CameraCreate, CameraOut, CameraUpdate

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
def update_camera(camera_id: int, payload: CameraUpdate, db: Session = Depends(get_db)) -> Camera:
    camera = _get_camera_or_404(camera_id, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(camera, field, value)
    db.commit()
    db.refresh(camera)
    return camera


@router.delete(
    "/{camera_id}", status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
def delete_camera(camera_id: int, db: Session = Depends(get_db)) -> None:
    camera = _get_camera_or_404(camera_id, db)
    db.delete(camera)
    db.commit()
