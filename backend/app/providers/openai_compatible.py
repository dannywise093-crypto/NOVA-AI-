import httpx

from app.models.base import ModelInfo
from app.models.types import ModelRequest, ModelResponse
from app.providers.base import ModelProvider


class OpenAICompatibleProvider(ModelProvider):
    """Provider for APIs exposing OpenAI-compatible chat completions."""

    def __init__(self, base_url: str, api_key: str, model: str, provider_name: str = "openai-compatible") -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.default_model = model
        self.provider_name = provider_name

    def list_models(self) -> list[ModelInfo]:
        return [
            ModelInfo(
                id=self.default_model,
                provider=self.provider_name,
                capabilities=("chat", "reasoning", "coding"),
                    context_window=32768,
                    supports_tools=True,
                    supports_vision=True,
                    supports_streaming=True,
            )
        ]

    async def chat(self, model: str, request: ModelRequest) -> ModelResponse:
        payload = {
            "model": model,
            "messages": [
                {"role": message.role, "content": message.content}
                for message in request.messages
            ],
            "temperature": request.temperature,
        }
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens

        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        choice = data["choices"][0]
        usage = data.get("usage") or {}
        return ModelResponse(
            content=choice["message"]["content"],
            model=data.get("model", model),
            provider=self.provider_name,
            usage={
                key: int(value)
                for key, value in usage.items()
                if isinstance(value, (int, float))
            },
            finish_reason=choice.get("finish_reason"),
        )
