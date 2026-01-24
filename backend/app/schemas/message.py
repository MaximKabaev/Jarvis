from datetime import datetime

from pydantic import BaseModel, Field


class MessageCreate(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True
