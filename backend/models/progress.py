from pydantic import BaseModel, Field, ConfigDict
from typing import List
from datetime import datetime, timezone, date
import uuid

class Progress(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    student_id: str
    completed_tasks: int = 0
    total_tasks: int = 0
    current_streak: int = 0
    longest_streak: int = 0
    badges: List[str] = []  # List of badge names
    last_activity: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    streak_dates: List[str] = []  # ISO date strings

class Badge(BaseModel):
    name: str
    description: str
    icon: str
    earned_at: datetime