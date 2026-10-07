from app.models.base import ModelInfo
from app.models.types import ModelRequest, ModelResponse
from app.providers.base import ModelProvider

class MockProvider(ModelProvider):
    """Deterministic provider used for local development and tests."""

    def list_models(self) -> list[ModelInfo]:
        return [
            ModelInfo(
                id="nova-mock",
                provider="mock",
                capabilities=("chat", "reasoning", "coding"),
                    context_window=32768,
                    supports_tools=True,
                    supports_vision=True,
                    supports_streaming=True,
            )
        ]

    async def chat(self, model: str, request: ModelRequest) -> ModelResponse:
        latest = next(
            (message.content for message in reversed(request.messages) if message.role == "user"),
            "",
        )
        return ModelResponse(
            content=f"NOVA mock response: {latest}",
            model=model,
            provider="mock",
            finish_reason="stop",
        )
