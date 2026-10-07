from app.models.task import AgentPlan, Capability, PlanStep, Task


class TaskPlanner:
    """Deterministic baseline planner; model-driven planning can replace this later."""

    def plan(self, task: Task) -> AgentPlan:
        steps: list[PlanStep] = []
        if Capability.RESEARCH in task.capabilities:
            steps.append(PlanStep("research", "Gather and compare relevant evidence", Capability.RESEARCH, "web.search"))
        if Capability.DOCUMENTS in task.capabilities:
            steps.append(PlanStep("retrieve", "Retrieve relevant project or document context", Capability.DOCUMENTS, "knowledge.retrieve", {"project_id": task.metadata.get("project_id", ""), "query": task.goal}))
        if Capability.CODING in task.capabilities:
            steps.append(PlanStep("implement", "Design, implement, and inspect the requested code", Capability.CODING, "code.sandbox"))
        if not steps:
            steps.append(PlanStep("reason", "Analyze the goal and produce the best answer", Capability.REASONING))
        steps.append(PlanStep("verify", "Check the result for correctness and completeness", Capability.REASONING))
        return AgentPlan(goal=task.goal, steps=tuple(steps))
