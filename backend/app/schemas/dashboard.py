from pydantic import BaseModel


class DashboardSummary(BaseModel):
    cameras_total: int
    cameras_online: int
    alerts_total: int
    alerts_unreviewed: int
    incidents_open: int
    people_registered: int
