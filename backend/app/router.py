from dataclasses import dataclass
from app.models.base import ModelInfo
from app.providers.base import ModelProvider


@dataclass(frozen=True)
class ModelChoice:
    model: str
    provider: ModelProvider
    reason: str
    score: float = 0.0


class ModelRouter:
    def __init__(self, providers: list[ModelProvider]) -> None:
        self.providers = providers

    def available_models(self) -> list[ModelInfo]:
        return [model for provider in self.providers for model in provider.list_models()]

    def _requirements(self, task: str) -> set[str]:
        text = task.lower()
        required = {"chat"}
        rules = {
            "reasoning": ("reason", "analyze", "complex", "debug", "plan", "why"),
            "coding": ("code", "coding", "program", "debug", "github", "python", "typescript"),
            "research": ("research", "sources", "latest", "search", "compare", "evidence"),
            "multimodal": ("image", "photo", "video", "audio", "screenshot"),
            "documents": ("document", "pdf", "file", "contract", "report"),
            "real_time": ("today", "now", "live", "current", "real-time"),
            "agentic": ("agent", "autonomous", "workflow", "automate", "tool"),
        }
        for capability, words in rules.items():
            if any(word in text for word in words):
                required.add(capability)
        return required

    def _score(self, model: ModelInfo, required: set[str], task: str) -> tuple[float, list[str]]:
        score = 0.0
        reasons: list[str] = []
        capabilities = set(model.capabilities)
        matched = required & capabilities
        score += len(matched) * 10
        if matched:
            reasons.append("capabilities=" + ",".join(sorted(matched)))
        if "multimodal" in required and model.supports_vision:
            score += 15
            reasons.append("vision")
        if ("agentic" in required or "coding" in required) and model.supports_tools:
            score += 8
            reasons.append("tools")
        if model.context_window and ("documents" in required or len(task) > 12000):
            score += min(model.context_window / 8192, 8)
        if model.supports_streaming:
            score += 1
        return score, reasons

    def rank(self, task: str, preferred_model: str | None = None) -> list[ModelChoice]:
        models = self.available_models()
        if not models:
            raise RuntimeError("No AI models are configured.")

        choices: list[ModelChoice] = []
        if preferred_model:
            for provider in self.providers:
                if provider.supports(preferred_model):
                    choices.append(ModelChoice(preferred_model, provider, "explicit model preference", 1000.0))
                    break

        required = self._requirements(task)
        ranked: list[tuple[float, ModelInfo, ModelProvider, str]] = []
        for provider in self.providers:
            for model in provider.list_models():
                if model.id == preferred_model:
                    continue
                score, reasons = self._score(model, required, task)
                ranked.append((score, model, provider, "; ".join(reasons) or "general-purpose fallback"))
        ranked.sort(key=lambda item: item[0], reverse=True)
        choices.extend(ModelChoice(model.id, provider, reason, score) for score, model, provider, reason in ranked)
        return choices

    def choose(self, task: str, preferred_model: str | None = None) -> ModelChoice:
        return self.rank(task, preferred_model)[0]
