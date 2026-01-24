from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.schemas.memory import MemoryCreate, MemoryUpdate, MemoryResponse, MemoryList
from app.services.memory import MemoryService

router = APIRouter()


@router.post("/", response_model=MemoryResponse, status_code=status.HTTP_201_CREATED)
async def create_memory(
    memory_data: MemoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    memory = await MemoryService.create_memory(db, current_user.id, memory_data)
    return memory


@router.get("/", response_model=MemoryList)
async def get_memories(
    category: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    memories, total = await MemoryService.get_memories(
        db, current_user.id, category=category, skip=skip, limit=limit
    )
    return MemoryList(memories=memories, total=total)


@router.get("/search", response_model=list[MemoryResponse])
async def search_memories(
    q: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    memories = await MemoryService.search_memories(db, current_user.id, q, limit)
    return memories


@router.get("/{memory_id}", response_model=MemoryResponse)
async def get_memory(
    memory_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    memory = await MemoryService.get_memory_by_id(db, memory_id, current_user.id)
    if not memory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Memory not found",
        )
    # Update last accessed
    await MemoryService.update_last_accessed(db, memory)
    return memory


@router.put("/{memory_id}", response_model=MemoryResponse)
async def update_memory(
    memory_id: str,
    memory_data: MemoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    memory = await MemoryService.get_memory_by_id(db, memory_id, current_user.id)
    if not memory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Memory not found",
        )
    updated_memory = await MemoryService.update_memory(db, memory, memory_data)
    return updated_memory


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory(
    memory_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    memory = await MemoryService.get_memory_by_id(db, memory_id, current_user.id)
    if not memory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Memory not found",
        )
    await MemoryService.delete_memory(db, memory)
