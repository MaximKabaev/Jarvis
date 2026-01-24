from typing import Any

import httpx

from friday.config import get_config
from friday.cloud.auth import AuthManager
from friday.utils.logging import get_logger

logger = get_logger(__name__)


class CloudClient:
    def __init__(self, auth_manager: AuthManager | None = None):
        self.config = get_config()
        self.auth = auth_manager or AuthManager()
        self.base_url = self.config.cloud.server_url

    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs,
    ) -> httpx.Response:
        headers = kwargs.pop("headers", {})
        headers.update(self.auth.get_auth_header())

        async with httpx.AsyncClient() as client:
            response = await client.request(
                method,
                f"{self.base_url}{endpoint}",
                headers=headers,
                **kwargs,
            )
            return response

    async def _get(self, endpoint: str, **kwargs) -> httpx.Response:
        return await self._request("GET", endpoint, **kwargs)

    async def _post(self, endpoint: str, **kwargs) -> httpx.Response:
        return await self._request("POST", endpoint, **kwargs)

    async def _put(self, endpoint: str, **kwargs) -> httpx.Response:
        return await self._request("PUT", endpoint, **kwargs)

    async def _delete(self, endpoint: str, **kwargs) -> httpx.Response:
        return await self._request("DELETE", endpoint, **kwargs)

    # Health check
    async def health_check(self) -> bool:
        try:
            response = await self._get("/health")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    # Memory operations
    async def get_memories(
        self,
        category: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> dict[str, Any] | None:
        params = {"skip": skip, "limit": limit}
        if category:
            params["category"] = category

        response = await self._get("/memories/", params=params)
        if response.status_code == 200:
            return response.json()
        logger.error(f"Failed to get memories: {response.status_code}")
        return None

    async def create_memory(
        self,
        category: str,
        content: str,
        importance: int = 5,
        source_conversation_id: str | None = None,
    ) -> dict[str, Any] | None:
        data = {
            "category": category,
            "content": content,
            "importance": importance,
        }
        if source_conversation_id:
            data["source_conversation_id"] = source_conversation_id

        response = await self._post("/memories/", json=data)
        if response.status_code == 201:
            return response.json()
        logger.error(f"Failed to create memory: {response.status_code}")
        return None

    async def search_memories(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        response = await self._get("/memories/search", params={"q": query, "limit": limit})
        if response.status_code == 200:
            return response.json()
        logger.error(f"Failed to search memories: {response.status_code}")
        return []

    async def delete_memory(self, memory_id: str) -> bool:
        response = await self._delete(f"/memories/{memory_id}")
        return response.status_code == 204

    # Conversation operations
    async def create_conversation(self, title: str | None = None) -> dict[str, Any] | None:
        data = {}
        if title:
            data["title"] = title

        response = await self._post("/conversations/", json=data)
        if response.status_code == 201:
            return response.json()
        logger.error(f"Failed to create conversation: {response.status_code}")
        return None

    async def get_conversation(self, conversation_id: str) -> dict[str, Any] | None:
        response = await self._get(f"/conversations/{conversation_id}")
        if response.status_code == 200:
            return response.json()
        logger.error(f"Failed to get conversation: {response.status_code}")
        return None

    async def get_conversations(
        self,
        skip: int = 0,
        limit: int = 50,
    ) -> dict[str, Any] | None:
        response = await self._get("/conversations/", params={"skip": skip, "limit": limit})
        if response.status_code == 200:
            return response.json()
        logger.error(f"Failed to get conversations: {response.status_code}")
        return None

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
    ) -> dict[str, Any] | None:
        response = await self._post(
            f"/conversations/{conversation_id}/messages",
            json={"role": role, "content": content},
        )
        if response.status_code == 201:
            return response.json()
        logger.error(f"Failed to add message: {response.status_code}")
        return None

    async def get_messages(
        self,
        conversation_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        response = await self._get(
            f"/conversations/{conversation_id}/messages",
            params={"skip": skip, "limit": limit},
        )
        if response.status_code == 200:
            return response.json()
        logger.error(f"Failed to get messages: {response.status_code}")
        return []

    async def update_conversation(
        self,
        conversation_id: str,
        title: str | None = None,
        summary: str | None = None,
    ) -> dict[str, Any] | None:
        data = {}
        if title is not None:
            data["title"] = title
        if summary is not None:
            data["summary"] = summary

        response = await self._put(f"/conversations/{conversation_id}", json=data)
        if response.status_code == 200:
            return response.json()
        logger.error(f"Failed to update conversation: {response.status_code}")
        return None
