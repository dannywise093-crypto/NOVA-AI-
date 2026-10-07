"""Adaptive agent execution with bounded replanning."""

from __future__ import annotations

from dataclasses import dataclass
from app.agents.executor import AgentExecutor, ExecutionTrace
from app.agents.planner import TaskPlanner
from app.models.task import AgentPlan, Task
from app.models.tool import ToolResult


@dataclass(frozen=True)
class AdaptiveExecution:
    traces: tuple[ExecutionTrace, ...]
    final_plan: AgentPlan
    replans: int


class AdaptiveAgentRuntime:
    def __init__(self, executor: AgentExecutor, planner: TaskPlanner | None = None, max_replans: int = 2) -> None:
        self.executor = executor
        self.planner = planner or TaskPlanner()
        self.max_replans = max(0, max_replans)

    async def run(self, task: Task) -> AdaptiveExecution:
        traces: list[ExecutionTrace] = []
        plan = self.planner.plan(task)

        for attempt in range(self.max_replans + 1):
            trace = await self.executor.execute(plan)
            traces.append(trace)
            failures = [
                step.result for step in trace.steps
                if step.result is not None and not step.result.success
            ]
            if not failures or attempt >= self.max_replans:
                return AdaptiveExecution(tuple(traces), plan, attempt)

            # Re-plan from the observed failure without exposing internal reasoning.
            failed_tools = {result.tool for result in failures}
            metadata = dict(task.metadata)
            metadata["failed_tools"] = sorted(failed_tools)
            metadata["replan_attempt"] = attempt + 1
            plan = self.planner.plan(Task(task.goal, task.capabilities, metadata))

        return AdaptiveExecution(tuple(traces), plan, self.max_replans)
