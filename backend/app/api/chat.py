from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.container import build_orchestrator
from app.models.types import ChatMessage

router = APIRouter(tags=["chat"])
orchestrator = build_orchestrator()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    history: list[ChatMessage] = Field(default_factory=list)
    model: str | None = None


class ChatResponse(BaseModel):
    content: str
    model: str
    provider: str
    routing_reason: str


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    messages = [*request.history, ChatMessage(role="user", content=request.message)]
    result = await orchestrator.run(
        task=request.message,
        messages=messages,
        preferred_model=request.model,
    )
    return ChatResponse(
        content=result.response.content,
        model=result.response.model,
        provider=result.response.provider,
        routing_reason=result.model_reason,
    )
