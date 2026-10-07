import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.core.container import build_orchestrator
from app.db.project_repository import get_project
from app.db.memory_repository import search_memories
from app.db.session import get_session
from app.events import AgentEventType
from app.models.task import Task\nfrom app.models.types import ChatMessage, ContentPart

router = APIRouter(tags=["stream"])

class StreamRequest(BaseModel):
    goal: str = Field(min_length=1)
    messages: list[ChatMessage] = Field(default_factory=list)
    model: str | None = None
    project_id: str | None = None
    attachments: list[dict[str, str | None]] = []

def sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\\n\\n"

async def event_stream(
    request: StreamRequest,
    session: AsyncSession,
    user: User,
) -> AsyncIterator[str]:
    if request.project_id:
        project = await get_project(session, request.project_id, user.id)
        if project is None:
            yield sse({"type": "error", "message": "Project not found"})
            return

    memories = await search_memories(session, user.id, request.goal, project_id=request.project_id, limit=6)
    messages = [*request.messages]
    if memories:
        messages.append(ChatMessage(
            role="system",
            content="Relevant NOVA memories (use only when helpful):\\n" + "\\n".join(f"- {m.content}" for m in memories),
        ))
    parts = tuple(
        ContentPart(
            type=str(item.get("type") or "file"),
            uri=str(item["uri"]),
            mime_type=item.get("mime_type"),
        )
        for item in request.attachments
        if item.get("uri")
    )
    messages.append(ChatMessage(role="user", content=request.goal, parts=parts))
    orchestrator = build_orchestrator(session)
    try:
        yield sse({"type": AgentEventType.TASK_STARTED.value, "message": request.goal})
        capabilities = orchestrator.infer_capabilities(request.goal)
        plan = orchestrator.planner.plan(__import__("app.models.task", fromlist=["Task"]).Task(
            goal=request.goal, capabilities=capabilities,
            metadata={"project_id": request.project_id} if request.project_id else {},
        ))
        yield sse({"type": AgentEventType.PLAN_CREATED.value, "data": {
            "steps": [{"id": step.id, "objective": step.objective, "tool": step.tool} for step in plan.steps],
            "capabilities": [c.value for c in capabilities],
        }})

        # Execute tools first, preserving the same context used by normal orchestration.
        trace = await orchestrator.executor.execute(plan)
        for step in trace.steps:
            for event in step.events:
                yield sse({"type": event.type.value, "message": event.message, "data": event.data})
                if event.type == AgentEventType.ERROR:
                    yield sse({"type": "tool.error", "message": event.message})

        context_messages = list(messages)
        tool_context = []
        for step in trace.steps:
            if step.result is None:
                continue
            if step.result.success:
                tool_context.append(f"[Tool result: {step.step.tool}]\\n{step.result.output}")
            elif step.result.error:
                tool_context.append(f"[Tool error: {step.step.tool}]\\n{step.result.error}")
        if tool_context:
            context_messages.append(ChatMessage(
                role="system",
                content="The following are trusted NOVA tool results. Use them as context; do not claim to have used a tool that did not return successfully.\\n\\n" + "\\n\\n".join(tool_context),
            ))

        from app.models.types import ModelRequest
        accumulated = ""
        selected = None
        failures = []
        for choice in orchestrator.router.rank(request.goal, request.model):
            try:
                selected = choice
                yield sse({"type": "model.selected", "data": {
                    "model": choice.model, "provider": choice.provider.list_models()[0].provider,
                    "reason": choice.reason, "score": choice.score,
                }})
                context = list(context_messages)
                for _ in range(8):
                    request_model = ModelRequest(
                        messages=tuple(context),
                        metadata={"capabilities": [c.value for c in capabilities], "project_id": request.project_id},
                        tools=tuple(orchestrator.executor.tools.schemas()),
                    )
                    call_buffers = {}
                    finish_reason = None
                    async for event in choice.provider.stream_events(choice.model, request_model):
                        event_type = event.get("type")
                        if event_type == "text_delta":
                            delta = str(event.get("text", ""))
                            accumulated += delta
                            yield sse({"type": AgentEventType.RESPONSE_DELTA.value, "data": {"delta": delta}})
                        elif event_type == "tool_call_delta":
                            index = int(event.get("index", 0))
                            state = call_buffers.setdefault(index, {"id": None, "name": None, "arguments": ""})
                            if event.get("id"):
                                state["id"] = event["id"]
                            if event.get("name"):
                                state["name"] = event["name"]
                            state["arguments"] += str(event.get("arguments", ""))
                            yield sse({"type": "tool.call.delta", "data": {
                                "index": index, "id": state["id"], "name": state["name"],
                                "arguments": event.get("arguments", ""),
                            }})
                        elif event_type == "done":
                            finish_reason = event.get("finish_reason")

                    if not call_buffers:
                        break

                    from app.models.tool import ToolCall
                    calls = []
                    for state in call_buffers.values():
                        try:
                            arguments = json.loads(state["arguments"] or "{}")
                        except json.JSONDecodeError:
                            arguments = {}
                        calls.append(ToolCall(
                            name=str(state["name"] or ""),
                            arguments=arguments,
                            id=state["id"],
                        ))

                    context.append(ChatMessage(
                        role="assistant",
                        content="",
                        tool_calls=tuple(calls),
                    ))
                    for call in calls:
                        result = await orchestrator.executor.execute_tool_call(call)
                        yield sse({"type": "tool.call.result", "data": {
                            "id": call.id or call.name,
                            "tool": call.name,
                            "success": result.success,
                            "output": result.output if result.success else None,
                            "error": result.error,
                        }})
                        context.append(ChatMessage(
                            role="tool",
                            content=str(result.output if result.success else {"error": result.error}),
                            tool_call_id=call.id or call.name,
                        ))
                else:
                    raise RuntimeError("Streaming tool-call loop exceeded 8 iterations")
                break
            except Exception as exc:
                failures.append(f"{choice.model}: {exc}")
                yield sse({"type": "provider.failed", "data": {"model": choice.model, "error": str(exc)}})

        if selected is None:
            raise RuntimeError("All configured AI models failed: " + "; ".join(failures))
        verification = orchestrator.verifier.verify(accumulated, expected_goal=request.goal)
        yield sse({"type": AgentEventType.VERIFICATION.value, "data": {
            "passed": verification.passed, "score": verification.score, "notes": verification.notes,
        }})
        yield sse({"type": "response.final", "content": accumulated, "model": selected.model,
                   "provider": selected.provider.list_models()[0].provider,
                   "routing_reason": selected.reason, "routing_score": selected.score,
                   "capabilities": [c.value for c in capabilities],
                   "verification": {"passed": verification.passed, "score": verification.score}})
        yield sse({"type": AgentEventType.TASK_FINISHED.value})
    except Exception as exc:
        yield sse({"type": AgentEventType.ERROR.value, "message": str(exc)})

@router.post("/stream")
async def stream(
    request: StreamRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    return StreamingResponse(event_stream(request, session, user), media_type="text/event-stream")
