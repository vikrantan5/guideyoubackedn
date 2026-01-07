from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime, timezone
import uuid

class TaskBase(BaseModel):
    title: str
    description: str
    difficulty: str  # "Easy", "Medium", "Hard"
    submission_type: str  # "image", "text", "video", "link"
    deadline: datetime

class TaskCreate(TaskBase):
    assigned_to: Optional[List[str]] = []  # List of student IDs

class Task(TaskBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_by: str  # admin ID
    assigned_to: List[str] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    difficulty: Optional[str] = None
    submission_type: Optional[str] = None
    deadline: Optional[datetime] = None
    assigned_to: Optional[List[str]] = None