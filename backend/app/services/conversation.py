from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.conversation import Conversation
from app.models.message import Message
from app.schemas.conversation import ConversationCreate, ConversationUpdate
from app.schemas.message import MessageCreate


class ConversationService:
    @staticmethod
    async def create_conversation(
        db: AsyncSession, user_id: str, conversation_data: ConversationCreate
    ) -> Conversation:
        conversation = Conversation(
            user_id=user_id,
            title=conversation_data.title,
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        return conversation

    @staticmethod
    async def get_conversation_by_id(
        db: AsyncSession, conversation_id: str, user_id: str
    ) -> Conversation | None:
        result = await db.execute(
            select(Conversation)
            .where(Conversation.id == conversation_id, Conversation.user_id == user_id)
            .options(selectinload(Conversation.messages))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_conversations(
        db: AsyncSession,
        user_id: str,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Conversation], int]:
        query = (
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
            .offset(skip)
            .limit(limit)
        )
        count_query = select(func.count(Conversation.id)).where(
            Conversation.user_id == user_id
        )

        result = await db.execute(query)
        conversations = list(result.scalars().all())

        count_result = await db.execute(count_query)
        total = count_result.scalar()

        return conversations, total

    @staticmethod
    async def update_conversation(
        db: AsyncSession, conversation: Conversation, conversation_data: ConversationUpdate
    ) -> Conversation:
        update_data = conversation_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(conversation, field, value)
        await db.commit()
        await db.refresh(conversation)
        return conversation

    @staticmethod
    async def delete_conversation(db: AsyncSession, conversation: Conversation) -> None:
        await db.delete(conversation)
        await db.commit()

    @staticmethod
    async def add_message(
        db: AsyncSession, conversation_id: str, message_data: MessageCreate
    ) -> Message:
        message = Message(
            conversation_id=conversation_id,
            role=message_data.role,
            content=message_data.content,
        )
        db.add(message)
        await db.commit()
        await db.refresh(message)
        return message

    @staticmethod
    async def get_messages(
        db: AsyncSession,
        conversation_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Message]:
        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
