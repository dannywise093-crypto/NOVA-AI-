from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ContentPart:
    type: str
    text: str | None = None
    uri: str | None = None
    mime_type: str | None = None


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str
    parts: tuple[ContentPart, ...] = ()


@dataclass(frozen=True)
class ModelRequest:
    messages: tuple[ChatMessage, ...]
    temperature: float = 0.2
    max_tokens: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ModelResponse:
    content: str
    model: str
    provider: str
    usage: dict[str, int] = field(default_factory=dict)
    finish_reason: str | None = None
