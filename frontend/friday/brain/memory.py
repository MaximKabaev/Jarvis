from typing import Any

from friday.cloud.client import CloudClient
from friday.brain.llm import LLMClient
from friday.brain.prompts import PromptBuilder
from friday.utils.logging import get_logger

logger = get_logger(__name__)


class MemoryManager:
    def __init__(self, cloud_client: CloudClient, llm_client: LLMClient):
        self.cloud = cloud_client
        self.llm = llm_client
        self.prompt_builder = PromptBuilder()
        self._cached_memories: list[dict[str, Any]] = []

    async def load_memories(self, limit: int = 50) -> list[dict[str, Any]]:
        """Load memories from cloud storage"""
        try:
            result = await self.cloud.get_memories(limit=limit)
            if result:
                self._cached_memories = result.get("memories", [])
                self.prompt_builder.set_memories(self._cached_memories)
                logger.info(f"Loaded {len(self._cached_memories)} memories")
            return self._cached_memories
        except Exception as e:
            logger.error(f"Failed to load memories: {e}")
            return []

    async def search_relevant_memories(
        self,
        query: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Search for memories relevant to a query"""
        try:
            memories = await self.cloud.search_memories(query, limit=limit)
            return memories
        except Exception as e:
            logger.error(f"Failed to search memories: {e}")
            return []

    async def extract_and_store_memories(
        self,
        conversation: list[dict[str, str]],
        conversation_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Extract important information from conversation and store as memories"""
        if len(conversation) < 2:
            return []

        try:
            # Build extraction prompt
            prompt = self.prompt_builder.build_memory_extraction_prompt(conversation)

            # Extract memories using LLM
            extracted = await self.llm.extract_json(prompt)

            if not extracted or not isinstance(extracted, list):
                return []

            # Store each extracted memory
            stored_memories = []
            for memory_data in extracted:
                if not isinstance(memory_data, dict):
                    continue

                category = memory_data.get("category", "context")
                content = memory_data.get("content", "")
                importance = memory_data.get("importance", 5)

                if not content:
                    continue

                # Validate category
                valid_categories = ["preference", "fact", "interest", "context", "request"]
                if category not in valid_categories:
                    category = "context"

                # Store memory
                memory = await self.cloud.create_memory(
                    category=category,
                    content=content,
                    importance=min(max(importance, 1), 10),
                    source_conversation_id=conversation_id,
                )

                if memory:
                    stored_memories.append(memory)
                    logger.info(f"Stored memory: [{category}] {content[:50]}...")

            # Update cache
            if stored_memories:
                self._cached_memories.extend(stored_memories)
                self.prompt_builder.set_memories(self._cached_memories)

            return stored_memories

        except Exception as e:
            logger.error(f"Failed to extract memories: {e}")
            return []

    async def add_memory(
        self,
        content: str,
        category: str = "context",
        importance: int = 5,
    ) -> dict[str, Any] | None:
        """Manually add a memory"""
        try:
            memory = await self.cloud.create_memory(
                category=category,
                content=content,
                importance=importance,
            )
            if memory:
                self._cached_memories.append(memory)
                self.prompt_builder.set_memories(self._cached_memories)
            return memory
        except Exception as e:
            logger.error(f"Failed to add memory: {e}")
            return None

    def get_cached_memories(self) -> list[dict[str, Any]]:
        """Get currently cached memories"""
        return self._cached_memories

    def clear_cache(self):
        """Clear memory cache"""
        self._cached_memories = []
        self.prompt_builder.set_memories([])
