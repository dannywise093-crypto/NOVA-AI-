from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.container import build_orchestrator
from app.models.types import ChatMessage

router = APIRouter(tags=["tasks"])
orchestrator = build_orchestrator()


class TaskRequest(BaseModel):
    goal: str = Field(min_length=1)
    messages: list[ChatMessage] = Field(default_factory=list)
    model: str | None = None


class TaskResponse(BaseModel):
    content: str
    model: str
    provider: str
    routing_reason: str
    capabilities: list[str]
    verification: dict[str, object]
    events: list[dict[str, object]]


@router.post("/tasks/run", response_model=TaskResponse)
async def run_task(request: TaskRequest) -> TaskResponse:
    messages = [*request.messages, ChatMessage(role="user", content=request.goal)]
    result = await orchestrator.run(request.goal, messages, request.model)
    events = [event for step in (result.trace.steps if result.trace else []) for event in step.events]
    return TaskResponse(
        content=result.response.content,
        model=result.response.model,
        provider=result.response.provider,
        routing_reason=result.model_reason,
        capabilities=[cap.value for cap in orchestrator.infer_capabilities(request.goal)],
        verification={
            "passed": result.verification.passed if result.verification else False,
            "score": result.verification.score if result.verification else 0.0,
            "notes": result.verification.notes if result.verification else "No verification result",
        },
        events=[{"type": event.type.value, "message": event.message, "data": event.data} for event in events],
    )
