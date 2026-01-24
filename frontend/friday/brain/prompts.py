from datetime import datetime
from typing import Any


SYSTEM_PROMPT = """You are Friday, a helpful AI assistant. You have a warm, friendly personality while remaining professional and efficient.

Key traits:
- Helpful and proactive in assisting the user
- Concise but thorough in responses
- Remembers context from the conversation
- Acknowledges when you don't know something

{memory_context}

Current date and time: {current_time}

Remember to be conversational since the user is speaking to you via voice. Keep responses natural and appropriate for spoken dialogue."""


MEMORY_EXTRACTION_PROMPT = """Analyze the following conversation and extract any important information that should be remembered about the user. Focus on:

1. Personal preferences (likes, dislikes)
2. Important facts about the user (name, occupation, location, etc.)
3. Recurring topics or interests
4. Specific requests to remember something
5. Context that might be useful in future conversations

Conversation:
{conversation}

Return a JSON array of memories to store. Each memory should have:
- "category": one of "preference", "fact", "interest", "context", "request"
- "content": the information to remember
- "importance": 1-10 scale (10 being most important)

Only include genuinely important information. If nothing significant should be remembered, return an empty array.

JSON response:"""


class PromptBuilder:
    def __init__(self):
        self._memories: list[dict[str, Any]] = []

    def set_memories(self, memories: list[dict[str, Any]]):
        self._memories = memories

    def build_system_prompt(self) -> str:
        memory_context = self._format_memories()
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")

        return SYSTEM_PROMPT.format(
            memory_context=memory_context,
            current_time=current_time,
        )

    def _format_memories(self) -> str:
        if not self._memories:
            return "You don't have any stored memories about this user yet."

        lines = ["Here's what you remember about the user:"]

        # Group by category
        by_category: dict[str, list[str]] = {}
        for memory in self._memories:
            category = memory.get("category", "general")
            content = memory.get("content", "")
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(content)

        # Format each category
        category_labels = {
            "preference": "Preferences",
            "fact": "Personal Facts",
            "interest": "Interests",
            "context": "Context",
            "request": "Specific Requests",
        }

        for category, items in by_category.items():
            label = category_labels.get(category, category.title())
            lines.append(f"\n{label}:")
            for item in items:
                lines.append(f"  - {item}")

        return "\n".join(lines)

    def build_memory_extraction_prompt(self, conversation: list[dict[str, str]]) -> str:
        # Format conversation for extraction
        formatted_conv = []
        for msg in conversation:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            formatted_conv.append(f"{role.title()}: {content}")

        conversation_text = "\n".join(formatted_conv)
        return MEMORY_EXTRACTION_PROMPT.format(conversation=conversation_text)

    def build_chat_messages(
        self,
        conversation_history: list[dict[str, str]],
        user_message: str,
    ) -> list[dict[str, str]]:
        messages = [
            {"role": "system", "content": self.build_system_prompt()},
        ]

        # Add conversation history
        for msg in conversation_history:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", ""),
            })

        # Add current message
        messages.append({"role": "user", "content": user_message})

        return messages
