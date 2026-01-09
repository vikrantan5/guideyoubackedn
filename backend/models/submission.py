from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime, timezone
import uuid

class SubmissionCreate(BaseModel):
    task_id: str
    content: Optional[str] = None
    submission_type: Optional[str] = None

class Submission(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str
    student_id: str
    content: str = "Task marked as complete"
    submission_type: str = "text"
    status: str = "pending"  # "pending", "approved", "rejected"
    feedback: Optional[str] = None
    ai_feedback: Optional[str] = None
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_late: bool = False
    likes: int = 0

class SubmissionUpdate(BaseModel):
    status: Optional[str] = None
    feedback: Optional[str] = None