from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.person import Person
from app.models.user import UserRole
from app.schemas.person import PersonCreate, PersonOut

router = APIRouter(prefix="/people", tags=["people"])


@router.get("", response_model=list[PersonOut], dependencies=[Depends(get_current_user)])
def list_people(db: Session = Depends(get_db)) -> list[Person]:
    return db.query(Person).order_by(Person.id).all()


@router.get("/{person_id}", response_model=PersonOut, dependencies=[Depends(get_current_user)])
def get_person(person_id: int, db: Session = Depends(get_db)) -> Person:
    person = db.get(Person, person_id)
    if person is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")
    return person


@router.post(
    "",
    response_model=PersonOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
def create_person(payload: PersonCreate, db: Session = Depends(get_db)) -> Person:
    # Face embeddings are registered separately (app/ai/prototypes/face_recognition.py
    # writes directly to the gitignored face_db/embeddings.pkl store for now). This
    # endpoint tracks the consent-based registration record itself.
    person = Person(name=payload.name, notes=payload.notes)
    db.add(person)
    db.commit()
    db.refresh(person)
    return person


@router.delete(
    "/{person_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
def delete_person(person_id: int, db: Session = Depends(get_db)) -> None:
    person = db.get(Person, person_id)
    if person is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")
    db.delete(person)
    db.commit()
