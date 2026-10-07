"""Streaming provider contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any
import json

from app.models.base import ModelInfo
from app.models.types import ModelRequest, ModelResponse


class ModelProvider(ABC):
    @abstractmethod
    def list_models(self) -> list[ModelInfo]:
        raise NotImplementedError

    @abstractmethod
    async def chat(self, model: str, request: ModelRequest) -> ModelResponse:
        raise NotImplementedError

    async def stream_events(self, model: str, request: ModelRequest) -> AsyncIterator[dict[str, Any]]:
        response = await self.chat(model, request)
        if response.content:
            yield {"type": "text_delta", "text": response.content}
        for index, call in enumerate(response.tool_calls):
            yield {
                "type": "tool_call_delta",
                "index": index,
                "id": call.id,
                "name": call.name,
                "arguments": json.dumps(call.arguments),
            }
        yield {"type": "done", "finish_reason": response.finish_reason}

    async def stream(self, model: str, request: ModelRequest) -> AsyncIterator[str]:
        async for event in self.stream_events(model, request):
            if event.get("type") == "text_delta" and event.get("text"):
                yield str(event["text"])

    def supports(self, model: str) -> bool:
        return any(item.id == model for item in self.list_models())
