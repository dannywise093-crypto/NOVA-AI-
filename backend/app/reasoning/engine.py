"""Adaptive reasoning plans for NOVA tasks."""

from __future__ import annotations

from dataclasses import dataclass
from app.models.task import AgentPlan, Capability, PlanStep, Task


@dataclass(frozen=True)
class ReasoningProfile:
    mode: str
    max_steps: int
    require_verification: bool = True


class ReasoningEngine:
    """Creates bounded reasoning plans without exposing private chain-of-thought."""

    def profile(self, task: Task) -> ReasoningProfile:
        capabilities = set(task.capabilities)
        if Capability.AGENTIC in capabilities or Capability.CODING in capabilities:
            return ReasoningProfile("deep", 8)
        if Capability.RESEARCH in capabilities or Capability.DOCUMENTS in capabilities:
            return ReasoningProfile("analytical", 6)
        return ReasoningProfile("direct", 3)

    def build_plan(self, task: Task) -> AgentPlan:
        profile = self.profile(task)
        steps: list[PlanStep] = []
        capabilities = set(task.capabilities)

        if profile.mode != "direct":
            steps.append(PlanStep("understand", "Clarify the objective, constraints, and success criteria"))

        if Capability.DOCUMENTS in capabilities:
            steps.append(PlanStep(
                "evidence", "Retrieve relevant project evidence",
                Capability.DOCUMENTS, "knowledge.retrieve",
                {"project_id": task.metadata.get("project_id", ""), "query": task.goal},
            ))
        if Capability.RESEARCH in capabilities:
            steps.append(PlanStep("research", "Gather and compare relevant external evidence", Capability.RESEARCH, "web.search"))
        if Capability.CODING in capabilities:
            steps.append(PlanStep("implementation", "Develop and inspect a solution", Capability.CODING, "code.sandbox"))
        if not steps:
            steps.append(PlanStep("solve", "Analyze the objective and construct a solution", Capability.REASONING))

        if profile.require_verification:
            steps.append(PlanStep("verify", "Check correctness, completeness, and consistency", Capability.REASONING))

        return AgentPlan(task.goal, tuple(steps[:profile.max_steps]))


    def planning_budget(self, task: Task) -> dict[str, int]:
        profile = self.profile(task)
        return {
            "max_steps": profile.max_steps,
            "max_tool_calls": max(2, profile.max_steps),
            "max_replans": 2 if profile.mode == "deep" else 1,
        }
