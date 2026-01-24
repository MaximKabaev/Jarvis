from datetime import datetime
from uuid import uuid4

from sqlalchemy import String, DateTime, Text, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Memory(Base):
    __tablename__ = "memories"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    category: Mapped[str] = mapped_column(String(50), index=True)  # e.g., "preference", "fact", "context"
    content: Mapped[str] = mapped_column(Text)
    importance: Mapped[int] = mapped_column(Integer, default=5)  # 1-10 scale
    source_conversation_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    last_accessed_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="memories")
    source_conversation: Mapped["Conversation | None"] = relationship(
        "Conversation", back_populates="extracted_memories"
    )
