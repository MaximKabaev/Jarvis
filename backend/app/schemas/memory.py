from datetime import datetime

from pydantic import BaseModel, Field


class MemoryCreate(BaseModel):
    category: str = Field(..., max_length=50)
    content: str
    importance: int = Field(default=5, ge=1, le=10)
    source_conversation_id: str | None = None


class MemoryUpdate(BaseModel):
    category: str | None = Field(default=None, max_length=50)
    content: str | None = None
    importance: int | None = Field(default=None, ge=1, le=10)


class MemoryResponse(BaseModel):
    id: str
    user_id: str
    category: str
    content: str
    importance: int
    source_conversation_id: str | None
    created_at: datetime
    updated_at: datetime
    last_accessed_at: datetime

    class Config:
        from_attributes = True


class MemoryList(BaseModel):
    memories: list[MemoryResponse]
    total: int
