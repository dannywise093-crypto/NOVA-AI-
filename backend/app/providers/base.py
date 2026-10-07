from abc import ABC, abstractmethod

from app.models.base import ModelInfo
from app.models.types import ModelRequest, ModelResponse

class ModelProvider(ABC):
    @abstractmethod
    def list_models(self) -> list[ModelInfo]:
        raise NotImplementedError

    @abstractmethod
    async def chat(self, model: str, request: ModelRequest) -> ModelResponse:
        raise NotImplementedError

    def supports(self, model: str) -> bool:
        return any(item.id == model for item in self.list_models())
