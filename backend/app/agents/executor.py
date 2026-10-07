from dataclasses import dataclass

from app.events import AgentEvent, AgentEventType
from app.models.task import AgentPlan, PlanStep
from app.models.tool import ToolResult
from app.tools.permissions import PermissionPolicy
from app.tools.registry import ToolRegistry


@dataclass(frozen=True)
class ExecutionStep:
    step: PlanStep
    result: ToolResult | None = None
    events: tuple[AgentEvent, ...] = ()


@dataclass(frozen=True)
class ExecutionTrace:
    plan: AgentPlan
    steps: tuple[ExecutionStep, ...]


class AgentExecutor:
    def __init__(self, tools: ToolRegistry, max_steps: int = 12, policy: PermissionPolicy | None = None) -> None:
        self.tools = tools
        self.max_steps = max_steps
        self.policy = policy or PermissionPolicy()

    async def execute(self, plan: AgentPlan) -> ExecutionTrace:
        executed: list[ExecutionStep] = []
        for step in plan.steps[: self.max_steps]:
            events = [AgentEvent(AgentEventType.STEP_STARTED, step.objective, {"step": step.id})]
            result = None
            if step.tool:
                spec = next((s for s in self.tools.specs() if s.name == step.tool), None)
                if spec is None:
                    result = ToolResult(step.tool, None, False, "Tool is not registered")
                elif any(not self.policy.allowed(cap) for cap in spec.capabilities):
                    result = ToolResult(step.tool, None, False, "Tool blocked by permission policy")
                else:
                    events.append(AgentEvent(AgentEventType.TOOL_STARTED, step.tool))
                    result = await self.tools.execute(step.tool, {})
                    events.append(AgentEvent(AgentEventType.TOOL_FINISHED, step.tool, {"success": result.success}))
            events.append(AgentEvent(AgentEventType.STEP_FINISHED, step.objective, {"success": result.success if result else True}))
            executed.append(ExecutionStep(step=step, result=result, events=tuple(events)))
        return ExecutionTrace(plan=plan, steps=tuple(executed))
