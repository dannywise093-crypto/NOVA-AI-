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

    def rank(self, task: str, preferred_model: str | None = None) -> list[ModelChoice]:
        models = self.available_models()
        if not models:
            raise RuntimeError("No AI models are configured.")

        choices: list[ModelChoice] = []
        if preferred_model:
            for provider in self.providers:
                if provider.supports(preferred_model):
                    choices.append(
                        ModelChoice(
                            preferred_model,
                            provider,
                            "explicit model preference",
                        )
                    )
                    break

        normalized = task.lower()
        wanted = "reasoning" if any(
            word in normalized for word in ("reason", "analyze", "complex", "debug", "plan")
        ) else "chat"

        for model in models:
            if model.id == preferred_model:
                continue
            if wanted in model.capabilities:
                provider = next(p for p in self.providers if p.supports(model.id))
                choices.append(
                    ModelChoice(model.id, provider, f"matched capability: {wanted}")
                )

        for model in models:
            if model.id in {choice.model for choice in choices}:
                continue
            provider = next(p for p in self.providers if p.supports(model.id))
            choices.append(ModelChoice(model.id, provider, "default fallback"))

        return choices

    def choose(self, task: str, preferred_model: str | None = None) -> ModelChoice:
        return self.rank(task, preferred_model)[0]
