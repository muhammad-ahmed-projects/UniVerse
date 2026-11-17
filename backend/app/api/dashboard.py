from fastapi import APIRouter, Depends
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.alert import Alert
from app.models.camera import Camera, CameraStatus
from app.models.incident import Incident
from app.models.person import Person
from app.schemas.dashboard import DashboardSummary

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary, dependencies=[Depends(get_current_user)])
def dashboard_summary(db: Session = Depends(get_db)) -> DashboardSummary:
    def count(stmt: Select[tuple[int]]) -> int:
        return db.scalar(stmt) or 0

    return DashboardSummary(
        cameras_total=count(select(func.count(Camera.id))),
        cameras_online=count(select(func.count(Camera.id)).where(Camera.status == CameraStatus.ONLINE)),
        alerts_total=count(select(func.count(Alert.id))),
        alerts_unreviewed=count(select(func.count(Alert.id)).where(Alert.incident_id.is_(None))),
        incidents_open=count(select(func.count(Incident.id)).where(Incident.status != "resolved")),
        people_registered=count(select(func.count(Person.id)).where(Person.is_active.is_(True))),
    )
