from dataclasses import dataclass

from app.models.base import ModelInfo
from app.providers.base import ModelProvider

@dataclass(frozen=True)
class ModelChoice:
    model: str
    provider: ModelProvider
    reason: str

class ModelRouter:
    def __init__(self, providers: list[ModelProvider]) -> None:
        self.providers = providers

    def available_models(self) -> list[ModelInfo]:
        return [
            model
            for provider in self.providers
            for model in provider.list_models()
        ]

    def choose(self, task: str, preferred_model: str | None = None) -> ModelChoice:
        models = self.available_models()
        if preferred_model:
            for provider in self.providers:
                if provider.supports(preferred_model):
                    return ModelChoice(preferred_model, provider, "explicit model preference")

        normalized = task.lower()
        wanted_capability = "reasoning" if any(
            word in normalized for word in ("reason", "analyze", "complex", "debug", "plan")
        ) else "chat"

        for model in models:
            if wanted_capability in model.capabilities:
                provider = next(p for p in self.providers if p.supports(model.id))
                return ModelChoice(model.id, provider, f"matched capability: {wanted_capability}")

        if not models:
            raise RuntimeError("No AI models are configured.")

        model = models[0]
        provider = next(p for p in self.providers if p.supports(model.id))
        return ModelChoice(model.id, provider, "default fallback")
