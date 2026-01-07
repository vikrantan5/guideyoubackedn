from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime, timezone
import uuid

class MessageBase(BaseModel):
    chat_id: str
    sender_id: str
    content: str
    message_type: str = "text"  # "text" or "image"

class MessageCreate(MessageBase):
    pass

class Message(MessageBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_deleted: bool = False
    is_read: bool = False

class ChatSession(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    admin_id: str
    student_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))