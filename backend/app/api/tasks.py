from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.conversations.store import ConversationStore
from app.core.container import build_orchestrator
from app.models.types import ChatMessage

router = APIRouter(tags=["tasks"])
orchestrator = build_orchestrator()
conversation_store = ConversationStore()

class TaskRequest(BaseModel):
    goal: str = Field(min_length=1)
    messages: list[ChatMessage] = Field(default_factory=list)
    model: str | None = None
    conversation_id: str | None = None

class TaskResponse(BaseModel):
    content: str
    model: str
    provider: str
    routing_reason: str
    capabilities: list[str]
    verification: dict[str, object]
    events: list[dict[str, object]]

@router.post("/tasks/run", response_model=TaskResponse)
async def run_task(request: TaskRequest, user: User = Depends(get_current_user)) -> TaskResponse:
    messages = list(request.messages)
    if request.conversation_id:
        conversation = conversation_store.get(request.conversation_id)
        if conversation is None or conversation.owner_id != user.id:
            raise HTTPException(status_code=404, detail="Conversation not found")
        messages = [ChatMessage(role=item.role, content=item.content) for item in conversation.messages]
    messages.append(ChatMessage(role="user", content=request.goal))
    result = await orchestrator.run(request.goal, messages, request.model)
    events = [event for step in (result.trace.steps if result.trace else []) for event in step.events]
    if request.conversation_id:
        conversation = conversation_store.get(request.conversation_id)
        if conversation is not None:
            from app.conversations.base import Message
            conversation.add_message(Message(id=f"task-user-{len(conversation.messages)}", role="user", content=request.goal))
            conversation.add_message(Message(id=f"task-assistant-{len(conversation.messages)}", role="assistant", content=result.response.content))
            conversation_store.save(conversation)
    return TaskResponse(
        content=result.response.content, model=result.response.model, provider=result.response.provider,
        routing_reason=result.model_reason,
        capabilities=[cap.value for cap in orchestrator.infer_capabilities(request.goal)],
        verification={
            "passed": result.verification.passed if result.verification else False,
            "score": result.verification.score if result.verification else 0.0,
            "notes": result.verification.notes if result.verification else "No verification result",
        },
        events=[{"type": event.type.value, "message": event.message, "data": event.data} for event in events],
    )
