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
        choice = self.router.choose(task, preferred_model)
        request = ModelRequest(messages=tuple(messages))
        response = await choice.provider.chat(choice.model, request)
        return AgentResult(response=response, model_reason=choice.reason)
