from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone
import uuid

class AnnouncementBase(BaseModel):
    title: str
    content: str

class AnnouncementCreate(AnnouncementBase):
    pass

class Announcement(AnnouncementBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_by: str  # admin ID
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))