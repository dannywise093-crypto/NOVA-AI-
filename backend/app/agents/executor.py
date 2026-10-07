from dataclasses import dataclass

from app.models.task import AgentPlan, PlanStep
from app.models.tool import ToolResult
from app.tools.registry import ToolRegistry


@dataclass(frozen=True)
class ExecutionStep:
    step: PlanStep
    result: ToolResult | None = None


@dataclass(frozen=True)
class ExecutionTrace:
    plan: AgentPlan
    steps: tuple[ExecutionStep, ...]


class AgentExecutor:
    def __init__(self, tools: ToolRegistry, max_steps: int = 12) -> None:
        self.tools = tools
        self.max_steps = max_steps

    async def execute(self, plan: AgentPlan) -> ExecutionTrace:
        executed: list[ExecutionStep] = []
        for step in plan.steps[: self.max_steps]:
            result = None
            if step.tool:
                result = await self.tools.execute(step.tool, {})
            executed.append(ExecutionStep(step=step, result=result))
        return ExecutionTrace(plan=plan, steps=tuple(executed))
