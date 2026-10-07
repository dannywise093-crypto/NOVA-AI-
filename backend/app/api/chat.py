from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.container import build_orchestrator
from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.db.session import get_session
from app.db.project_repository import get_project
from app.db.memory_repository import search_memories
from app.memory.engine import MemoryEngine
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.types import ChatMessage, ContentPart

router = APIRouter(tags=["chat"])
orchestrator = build_orchestrator()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    history: list[ChatMessage] = Field(default_factory=list)
    model: str | None = None
    project_id: str | None = None


class PlanStepResponse(BaseModel):
    id: str
    objective: str
    capability: str
    tool: str | None = None


class ChatResponse(BaseModel):
    content: str
    model: str
    provider: str
    routing_reason: str
    capabilities: list[str]
    plan: list[PlanStepResponse]
    verification: dict[str, object]


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)) -> ChatResponse:
    if request.project_id is not None and await get_project(session, request.project_id, user.id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    memories = await search_memories(session, user.id, request.message, project_id=request.project_id, limit=6)
    memory_context = ""
    if memories:
        memory_context = "Relevant NOVA memories (use only when helpful):\\n" + "\\n".join(
            f"- {memory.content}" for memory in memories
        )
    messages = [*request.history]
    if memory_context:
        messages.append(ChatMessage(role="system", content=memory_context))
    parts = tuple(
        ContentPart(
            type=str(item.get("type") or "file"),
            uri=str(item["uri"]),
            mime_type=item.get("mime_type"),
        )
        for item in request.attachments
        if item.get("uri")
    )
    messages.append(ChatMessage(
        role="user",
        content=request.message,
        parts=parts,
    ))
    result = await build_orchestrator(session).run(
        task=request.message,
        messages=messages,
        preferred_model=request.model,
        project_id=request.project_id,
    )
    await MemoryEngine().remember(session, user.id, request.message, project_id=request.project_id)
    return ChatResponse(
        content=result.response.content,
        model=result.response.model,
        provider=result.response.provider,
        routing_reason=result.model_reason,
        capabilities=[cap.value for cap in build_orchestrator(session).infer_capabilities(request.message)],
        verification={
            "passed": result.verification.passed if result.verification else False,
            "score": result.verification.score if result.verification else 0.0,
            "notes": result.verification.notes if result.verification else "No verification result",
        },
        plan=[
            PlanStepResponse(
                id=step.step.id,
                objective=step.step.objective,
                capability=step.step.capability.value,
                tool=step.step.tool,
            )
            for step in (result.trace.steps if result.trace else [])
        ],
    )
