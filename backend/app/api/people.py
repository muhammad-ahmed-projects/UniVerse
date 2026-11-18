from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.camera import Camera
from app.models.person import FaceEmbedding, Person
from app.models.user import UserRole
from app.schemas.person import FaceEmbeddingOut, FaceSampleOut, PersonCreate, PersonOut, SightingCreate
from app.services import images, media_store
from app.services.face_encoder import FaceEncoder, get_face_encoder
from app.services.ws_manager import manager

router = APIRouter(prefix="/people", tags=["people"])
embeddings_router = APIRouter(prefix="/face-embeddings", tags=["people"])

# Face data is biometric: only admins manage it, and only admins or the AI
# scripts' service account can read embeddings (proposal: restricted access).
admin_only = Depends(require_role(UserRole.ADMIN))
admin_or_ai_service = Depends(require_role(UserRole.ADMIN, UserRole.AI_SERVICE))

# Below this width the detector still finds a face, but the embedding is too
# blurry to recognize reliably later.
MIN_FACE_WIDTH_PX = 60
MAX_FACES_PER_PERSON = 20
THUMBNAIL_WIDTH_PX = 256


def _get_person_or_404(person_id: int, db: Session) -> Person:
    person = db.get(Person, person_id)
    if person is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")
    return person


def _get_face_or_404(person_id: int, face_id: int, db: Session) -> FaceEmbedding:
    face = db.get(FaceEmbedding, face_id)
    if face is None or face.person_id != person_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Face sample not found")
    return face


@router.get("", response_model=list[PersonOut], dependencies=[Depends(get_current_user)])
def list_people(db: Session = Depends(get_db)) -> list[Person]:
    return db.query(Person).order_by(Person.id).all()


@router.get("/{person_id}", response_model=PersonOut, dependencies=[Depends(get_current_user)])
def get_person(person_id: int, db: Session = Depends(get_db)) -> Person:
    return _get_person_or_404(person_id, db)


@router.post("", response_model=PersonOut, status_code=status.HTTP_201_CREATED, dependencies=[admin_only])
def create_person(payload: PersonCreate, db: Session = Depends(get_db)) -> Person:
    """The consent-based registration record. Face photos are added next,
    with POST /people/{id}/faces."""
    person = Person(name=payload.name, notes=payload.notes)
    db.add(person)
    db.commit()
    db.refresh(person)
    return person


@router.delete("/{person_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[admin_only])
def delete_person(person_id: int, db: Session = Depends(get_db)) -> None:
    person = _get_person_or_404(person_id, db)
    thumbnails = [face.image_file for face in person.faces]
    db.delete(person)  # face_embeddings rows cascade in the database
    db.commit()
    for name in thumbnails:
        media_store.delete("faces", name)


@router.post(
    "/{person_id}/faces",
    response_model=FaceSampleOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[admin_only],
)
def add_face(
    person_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    encoder: FaceEncoder = Depends(get_face_encoder),
) -> FaceEmbedding:
    """Register one face photo: detect the face, store its ArcFace embedding
    (what the recognizer matches against) and a cropped thumbnail."""
    person = _get_person_or_404(person_id, db)
    if person.face_count >= MAX_FACES_PER_PERSON:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A person can have at most {MAX_FACES_PER_PERSON} face photos",
        )

    image = images.decode(images.read_upload(file))
    faces = encoder.detect(image)
    if not faces:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="No face found in the photo. Use a clear, well-lit, front-facing photo.",
        )
    if len(faces) > 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Found {len(faces)} faces in the photo. Use a photo with only this person in it.",
        )
    face = faces[0]
    x1, y1, x2, y2 = face.bbox
    if x2 - x1 < MIN_FACE_WIDTH_PX:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"The face is too small ({x2 - x1}px wide). Move closer or use a sharper photo.",
        )

    # Thumbnail: the face plus a 30% margin, clamped to the image.
    height, width = image.shape[:2]
    margin_x, margin_y = int((x2 - x1) * 0.3), int((y2 - y1) * 0.3)
    crop = image[max(y1 - margin_y, 0) : min(y2 + margin_y, height), max(x1 - margin_x, 0) : min(x2 + margin_x, width)]
    file_name = media_store.save("faces", images.encode_jpeg(crop, max_width=THUMBNAIL_WIDTH_PX, quality=90))

    sample = FaceEmbedding(person_id=person.id, embedding=face.embedding, image_file=file_name)
    db.add(sample)
    try:
        db.commit()
    except Exception:
        media_store.delete("faces", file_name)
        raise
    db.refresh(sample)
    return sample


@router.get("/{person_id}/faces", response_model=list[FaceSampleOut], dependencies=[admin_only])
def list_faces(person_id: int, db: Session = Depends(get_db)) -> list[FaceEmbedding]:
    return _get_person_or_404(person_id, db).faces


@router.get("/{person_id}/faces/{face_id}/image", response_class=FileResponse, dependencies=[admin_only])
def get_face_image(person_id: int, face_id: int, db: Session = Depends(get_db)) -> FileResponse:
    face = _get_face_or_404(person_id, face_id, db)
    path = media_store.path_for("faces", face.image_file) if face.image_file else None
    if path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Face image not found")
    # no-store: face thumbnails are biometric data, so keep them out of the browser cache.
    return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "no-store"})


@router.delete("/{person_id}/faces/{face_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[admin_only])
def delete_face(person_id: int, face_id: int, db: Session = Depends(get_db)) -> None:
    face = _get_face_or_404(person_id, face_id, db)
    file_name = face.image_file
    db.delete(face)
    db.commit()
    media_store.delete("faces", file_name)


@router.post("/{person_id}/sightings", response_model=PersonOut, dependencies=[admin_or_ai_service])
def report_sighting(
    person_id: int,
    payload: SightingCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> Person:
    """face_recognition.py reports that it recognized this person on a camera."""
    person = _get_person_or_404(person_id, db)
    if db.get(Camera, payload.camera_id) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="camera_id does not exist")
    person.last_seen_at = datetime.now(UTC)
    person.last_seen_camera_id = payload.camera_id
    db.commit()
    db.refresh(person)

    background_tasks.add_task(
        manager.broadcast,
        {
            "type": "person_seen",
            "person_id": person.id,
            "camera_id": payload.camera_id,
            "similarity": round(payload.similarity, 3),
            "seen_at": person.last_seen_at.isoformat(),
        },
    )
    return person


@embeddings_router.get("", response_model=list[FaceEmbeddingOut], dependencies=[admin_or_ai_service])
def list_face_embeddings(db: Session = Depends(get_db)) -> list[FaceEmbeddingOut]:
    """Every face sample of every active person, for the recognizer to match against."""
    rows = (
        db.query(FaceEmbedding, Person.name)
        .join(Person, FaceEmbedding.person_id == Person.id)
        .filter(Person.is_active.is_(True))
        .order_by(FaceEmbedding.id)
        .all()
    )
    return [FaceEmbeddingOut(person_id=face.person_id, name=name, embedding=face.embedding) for face, name in rows]
