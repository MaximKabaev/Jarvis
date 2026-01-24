import json
from typing import AsyncGenerator, Any

import httpx

from friday.config import get_config
from friday.utils.logging import get_logger

logger = get_logger(__name__)


class LLMClient:
    def __init__(self):
        self.config = get_config()
        self.base_url = self.config.llm.base_url

    async def generate(
        self,
        messages: list[dict[str, str]],
        stream: bool = False,
    ) -> str | AsyncGenerator[str, None]:
        if stream:
            return self._generate_stream(messages)
        else:
            return await self._generate_sync(messages)

    async def _generate_sync(self, messages: list[dict[str, str]]) -> str:
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.config.llm.model,
                        "messages": messages,
                        "stream": False,
                        "options": {
                            "temperature": self.config.llm.temperature,
                            "num_predict": self.config.llm.max_tokens,
                        },
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    return data.get("message", {}).get("content", "")
                else:
                    logger.error(f"LLM request failed: {response.status_code} - {response.text}")
                    return ""

        except httpx.TimeoutException:
            logger.error("LLM request timed out")
            return ""
        except Exception as e:
            logger.error(f"LLM request error: {e}")
            return ""

    async def _generate_stream(
        self,
        messages: list[dict[str, str]],
    ) -> AsyncGenerator[str, None]:
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.config.llm.model,
                        "messages": messages,
                        "stream": True,
                        "options": {
                            "temperature": self.config.llm.temperature,
                            "num_predict": self.config.llm.max_tokens,
                        },
                    },
                ) as response:
                    if response.status_code != 200:
                        logger.error(f"LLM stream request failed: {response.status_code}")
                        return

                    async for line in response.aiter_lines():
                        if line:
                            try:
                                data = json.loads(line)
                                content = data.get("message", {}).get("content", "")
                                if content:
                                    yield content
                            except json.JSONDecodeError:
                                continue

        except Exception as e:
            logger.error(f"LLM stream error: {e}")

    async def check_health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> list[str]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    return [model["name"] for model in data.get("models", [])]
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
        return []

    async def extract_json(self, prompt: str) -> Any:
        """Generate and parse JSON response"""
        messages = [{"role": "user", "content": prompt}]
        response = await self._generate_sync(messages)

        # Try to extract JSON from response
        response = response.strip()

        # Handle code blocks
        if "```json" in response:
            start = response.index("```json") + 7
            end = response.index("```", start)
            response = response[start:end].strip()
        elif "```" in response:
            start = response.index("```") + 3
            end = response.index("```", start)
            response = response[start:end].strip()

        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            return None
