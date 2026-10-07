from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from app.models.base import ModelInfo
from app.models.types import ModelRequest, ModelResponse

class ModelProvider(ABC):
    @abstractmethod
    def list_models(self) -> list[ModelInfo]:
        raise NotImplementedError

    @abstractmethod
    async def chat(self, model: str, request: ModelRequest) -> ModelResponse:
        raise NotImplementedError

    async def stream(self, model: str, request: ModelRequest) -> AsyncIterator[str]:
        """Fallback streaming contract for providers without native streaming."""
        response = await self.chat(model, request)
        if response.content:
            yield response.content

    def supports(self, model: str) -> bool:
        return any(item.id == model for item in self.list_models())
