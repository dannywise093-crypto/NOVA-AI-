from dataclasses import dataclass
from app.agents.executor import AgentExecutor, ExecutionTrace
from app.agents.planner import TaskPlanner
from app.models.task import Capability, Task
from app.models.types import ChatMessage, ModelRequest, ModelResponse
from app.router import ModelRouter
from app.tools.registry import ToolRegistry
from app.verification import ResultVerifier, VerificationResult
from app.agents.adaptive_runtime import AdaptiveAgentRuntime


@dataclass(frozen=True)
class AgentResult:
    response: ModelResponse
    model_reason: str
    trace: ExecutionTrace | None = None
    verification: VerificationResult | None = None


class AgentOrchestrator:
    def __init__(self, router: ModelRouter, tools: ToolRegistry | None = None) -> None:
        self.router = router
        self.planner = TaskPlanner()
        self.executor = AgentExecutor(tools or ToolRegistry())
        self.verifier = ResultVerifier()
        self.runtime = AdaptiveAgentRuntime(self.executor, self.planner)

    def infer_capabilities(self, task: str) -> tuple[Capability, ...]:
        text = task.lower()
        found = [Capability.REASONING]
        rules = {
            Capability.RESEARCH: ("research", "sources", "latest", "search", "compare"),
            Capability.CODING: ("code", "coding", "program", "debug", "github"),
            Capability.DOCUMENTS: ("document", "pdf", "file", "contract", "report"),
            Capability.MULTIMODAL: ("image", "photo", "video", "audio", "screenshot"),
            Capability.REAL_TIME: ("today", "now", "live", "current", "real-time"),
            Capability.AGENTIC: ("autonomous", "workflow", "automate", "agent"),
        }
        for capability, words in rules.items():
            if any(word in text for word in words):
                found.append(capability)
        return tuple(dict.fromkeys(found))

    async def run(
        self,
        task: str,
        messages: list[ChatMessage],
        preferred_model: str | None = None,
        *,
        project_id: str | None = None,
    ) -> AgentResult:
        capabilities = self.infer_capabilities(task)
        plan = self.planner.plan(Task(goal=task, capabilities=capabilities, metadata={"project_id": project_id} if project_id else {}))
        context = list(messages)
        tools = tuple(self.executor.tools.schemas())
        failures: list[str] = []

        for choice in self.router.rank(task, preferred_model):
            try:
                model_info = next(
                    (m for m in choice.provider.list_models() if m.id == choice.model),
                    None,
                )
                request = ModelRequest(
                    messages=tuple(context),
                    metadata={
                        "capabilities": [c.value for c in capabilities],
                        "project_id": project_id,
                        "plan": [step.objective for step in plan.steps],
                        "plan_tools": [step.tool for step in plan.steps if step.tool],
                    },
                    tools=tools if model_info and model_info.supports_tools else (),
                )
                for _ in range(8):
                    response = await choice.provider.chat(choice.model, request)
                    if not response.tool_calls:
                        verification = self.verifier.verify(response.content, expected_goal=task)
                        reason = f"{choice.reason}; plan={len(plan.steps)} steps"
                        if failures:
                            reason = f"{reason}; recovered after {len(failures)} provider failure(s)"
                        return AgentResult(response, reason, None, verification)
                    context.append(
                        ChatMessage(
                            role="assistant",
                            content=response.content,
                            tool_calls=response.tool_calls,
                        )
                    )
                    for call in response.tool_calls:
                        result = await self.executor.execute_tool_call(call)
                        context.append(
                            ChatMessage(
                                role="tool",
                                content=str(result.output if result.success else {"error": result.error}),
                                tool_call_id=call.id or call.name,
                            )
                        )
                    request = ModelRequest(
                        messages=tuple(context),
                        metadata={
                            "capabilities": [c.value for c in capabilities],
                            "project_id": project_id,
                        },
                        tools=tools if model_info and model_info.supports_tools else (),
                    )
                raise RuntimeError("Tool-call loop exceeded 8 iterations")
            except Exception as exc:
                failures.append(f"{choice.model}: {exc}")
        raise RuntimeError("All configured AI models failed: " + "; ".join(failures))
