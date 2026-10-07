from dataclasses import dataclass

from app.models.types import ChatMessage, ModelRequest, ModelResponse
from app.router import ModelRouter


@dataclass(frozen=True)
class AgentResult:
    response: ModelResponse
    model_reason: str


class AgentOrchestrator:
    def __init__(self, router: ModelRouter) -> None:
        self.router = router

    async def run(
        self,
        task: str,
        messages: list[ChatMessage],
        preferred_model: str | None = None,
    ) -> AgentResult:
        request = ModelRequest(messages=tuple(messages))
        failures: list[str] = []

        for choice in self.router.rank(task, preferred_model):
            try:
                response = await choice.provider.chat(choice.model, request)
                reason = choice.reason
                if failures:
                    reason += f"; recovered after {len(failures)} provider failure(s)"
                return AgentResult(response=response, model_reason=reason)
            except Exception as exc:
                failures.append(f"{choice.model}: {exc}")

        details = "; ".join(failures)
        raise RuntimeError(f"All configured AI models failed: {details}")
