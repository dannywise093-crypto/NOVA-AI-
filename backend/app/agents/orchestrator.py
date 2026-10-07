from dataclasses import dataclass
from app.agents.executor import AgentExecutor, ExecutionTrace
from app.agents.planner import TaskPlanner
from app.models.task import Capability, Task
from app.models.types import ChatMessage, ModelRequest, ModelResponse
from app.router import ModelRouter
from app.tools.registry import ToolRegistry
from app.verification import ResultVerifier, VerificationResult

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

    def infer_capabilities(self, task: str) -> tuple[Capability, ...]:
        text = task.lower()
        found = [Capability.REASONING]
        rules = {
            Capability.RESEARCH: ("research","sources","latest","search","compare"),
            Capability.CODING: ("code","coding","program","debug","github"),
            Capability.DOCUMENTS: ("document","pdf","file","contract","report"),
            Capability.MULTIMODAL: ("image","photo","video","audio","screenshot"),
            Capability.REAL_TIME: ("today","now","live","current","real-time"),
            Capability.AGENTIC: ("autonomous","workflow","automate","agent"),
        }
        for capability, words in rules.items():
            if any(word in text for word in words): found.append(capability)
        return tuple(dict.fromkeys(found))

    async def run(self, task: str, messages: list[ChatMessage], preferred_model: str | None = None, *, project_id: str | None = None) -> AgentResult:
        capabilities = self.infer_capabilities(task)
        context = list(messages)
        tools = tuple(self.executor.tools.schemas())
        failures = []
        for choice in self.router.rank(task, preferred_model):
            try:
                request = ModelRequest(messages=tuple(context),
                    metadata={"capabilities":[c.value for c in capabilities],"project_id":project_id},
                    tools=tools if choice.provider.list_models()[0].supports_tools else ())
                for _ in range(8):
                    response = await choice.provider.chat(choice.model, request)
                    if not response.tool_calls:
                        verification = self.verifier.verify(response.content, expected_goal=task)
                        return AgentResult(response, choice.reason, None, verification)
                    context.append(ChatMessage(role="assistant", content=response.content, tool_calls=response.tool_calls))
                    for call in response.tool_calls:
                        result = await self.executor.execute_tool_call(call)
                        context.append(ChatMessage(
                            role="tool", content=str(result.output if result.success else {"error": result.error}),
                            tool_call_id=call.name,
                        ))
                raise RuntimeError("Tool-call loop exceeded 8 iterations")
            except Exception as exc:
                failures.append(f"{choice.model}: {exc}")
        raise RuntimeError("All configured AI models failed: " + "; ".join(failures))
