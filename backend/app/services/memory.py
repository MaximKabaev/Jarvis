from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import Memory
from app.schemas.memory import MemoryCreate, MemoryUpdate


class MemoryService:
    @staticmethod
    async def create_memory(
        db: AsyncSession, user_id: str, memory_data: MemoryCreate
    ) -> Memory:
        memory = Memory(
            user_id=user_id,
            category=memory_data.category,
            content=memory_data.content,
            importance=memory_data.importance,
            source_conversation_id=memory_data.source_conversation_id,
        )
        db.add(memory)
        await db.commit()
        await db.refresh(memory)
        return memory

    @staticmethod
    async def get_memory_by_id(
        db: AsyncSession, memory_id: str, user_id: str
    ) -> Memory | None:
        result = await db.execute(
            select(Memory).where(Memory.id == memory_id, Memory.user_id == user_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_memories(
        db: AsyncSession,
        user_id: str,
        category: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[Memory], int]:
        query = select(Memory).where(Memory.user_id == user_id)
        count_query = select(func.count(Memory.id)).where(Memory.user_id == user_id)

        if category:
            query = query.where(Memory.category == category)
            count_query = count_query.where(Memory.category == category)

        query = query.order_by(Memory.importance.desc(), Memory.updated_at.desc())
        query = query.offset(skip).limit(limit)

        result = await db.execute(query)
        memories = list(result.scalars().all())

        count_result = await db.execute(count_query)
        total = count_result.scalar()

        return memories, total

    @staticmethod
    async def update_memory(
        db: AsyncSession, memory: Memory, memory_data: MemoryUpdate
    ) -> Memory:
        update_data = memory_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(memory, field, value)
        memory.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(memory)
        return memory

    @staticmethod
    async def delete_memory(db: AsyncSession, memory: Memory) -> None:
        await db.delete(memory)
        await db.commit()

    @staticmethod
    async def update_last_accessed(db: AsyncSession, memory: Memory) -> Memory:
        memory.last_accessed_at = datetime.utcnow()
        await db.commit()
        await db.refresh(memory)
        return memory

    @staticmethod
    async def search_memories(
        db: AsyncSession,
        user_id: str,
        query: str,
        limit: int = 10,
    ) -> list[Memory]:
        # Simple search - in production, consider using full-text search
        result = await db.execute(
            select(Memory)
            .where(Memory.user_id == user_id)
            .where(Memory.content.ilike(f"%{query}%"))
            .order_by(Memory.importance.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
