from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.message import MessageResponse


class ConversationCreate(BaseModel):
    title: str | None = Field(default=None, max_length=255)


class ConversationUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    summary: str | None = None


class ConversationResponse(BaseModel):
    id: str
    user_id: str
    title: str | None
    summary: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConversationWithMessages(ConversationResponse):
    messages: list[MessageResponse] = []


class ConversationList(BaseModel):
    conversations: list[ConversationResponse]
    total: int
