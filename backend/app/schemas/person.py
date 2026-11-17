from datetime import datetime

from pydantic import BaseModel, Field


class PersonCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    notes: str | None = Field(default=None, max_length=500)


class PersonOut(BaseModel):
    id: int
    name: str
    notes: str | None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
