import json
from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.container import build_orchestrator
from app.models.types import ChatMessage

router = APIRouter(tags=["stream"])
orchestrator = build_orchestrator()


class StreamRequest(BaseModel):
    goal: str = Field(min_length=1)
    messages: list[ChatMessage] = Field(default_factory=list)
    model: str | None = None


async def event_stream(request: StreamRequest) -> AsyncIterator[str]:
    messages = [*request.messages, ChatMessage(role="user", content=request.goal)]
    try:
        result = await orchestrator.run(request.goal, messages, request.model)
        if result.trace:
            for step in result.trace.steps:
                for event in step.events:
                    yield f"data: {json.dumps({'type': event.type.value, 'message': event.message, 'data': event.data})}\\n\\n"
        yield f"data: {json.dumps({'type': 'response.final', 'content': result.response.content, 'model': result.response.model, 'provider': result.response.provider})}\\n\\n"
    except Exception as exc:
        yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\\n\\n"


@router.post("/stream")
async def stream(request: StreamRequest) -> StreamingResponse:
    return StreamingResponse(event_stream(request), media_type="text/event-stream")
