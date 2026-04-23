from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class AIResponse:
    text: str
    provider: str
    chat_url: str
    success: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass(slots=True)
class AIChatOptions:
    mode: str = "new_chat"
    existing_chat_url: str | None = None
    max_retries: int = 2
    response_timeout_s: float = 20.0
    force_new_chat: bool = False

    def resolved_mode(self) -> str:
        mode = (self.mode or "new_chat").strip().lower()
        return mode if mode in {"new_chat", "existing_chat"} else "new_chat"
