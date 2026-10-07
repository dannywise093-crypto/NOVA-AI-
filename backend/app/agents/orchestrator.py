from dataclasses import dataclass

from app.agents.executor import AgentExecutor, ExecutionTrace
from app.agents.planner import TaskPlanner
from app.models.task import Capability, Task
from app.models.types import ChatMessage, ModelRequest, ModelResponse
from app.router import ModelRouter
from app.tools.registry import ToolRegistry


@dataclass(frozen=True)
class AgentResult:
    response: ModelResponse
    model_reason: str
    trace: ExecutionTrace | None = None


class AgentOrchestrator:
    def __init__(self, router: ModelRouter, tools: ToolRegistry | None = None) -> None:
        self.router = router
        self.planner = TaskPlanner()
        self.executor = AgentExecutor(tools or ToolRegistry())

    def infer_capabilities(self, task: str) -> tuple[Capability, ...]:
        normalized = task.lower()
        found: list[Capability] = [Capability.REASONING]
        rules = {
            Capability.RESEARCH: ("research", "sources", "latest", "search", "compare"),
            Capability.CODING: ("code", "coding", "program", "debug", "github"),
            Capability.DOCUMENTS: ("document", "pdf", "file", "contract", "report"),
            Capability.MULTIMODAL: ("image", "photo", "video", "audio", "screenshot"),
            Capability.REAL_TIME: ("today", "now", "live", "current", "real-time"),
            Capability.AGENTIC: ("autonomous", "workflow", "automate", "agent"),
        }
        for capability, words in rules.items():
            if any(word in normalized for word in words):
                found.append(capability)
        return tuple(dict.fromkeys(found))

    async def run(self, task: str, messages: list[ChatMessage], preferred_model: str | None = None) -> AgentResult:
        capabilities = self.infer_capabilities(task)
        plan = self.planner.plan(Task(goal=task, capabilities=capabilities))
        trace = await self.executor.execute(plan)
        request = ModelRequest(messages=tuple(messages), metadata={"capabilities": [c.value for c in capabilities]})
        failures: list[str] = []
        for choice in self.router.rank(task, preferred_model):
            try:
                response = await choice.provider.chat(choice.model, request)
                reason = choice.reason
                if failures:
                    reason += f"; recovered after {len(failures)} provider failure(s)"
                return AgentResult(response=response, model_reason=reason, trace=trace)
            except Exception as exc:
                failures.append(f"{choice.model}: {exc}")
        raise RuntimeError(f"All configured AI models failed: {'; '.join(failures)}")
