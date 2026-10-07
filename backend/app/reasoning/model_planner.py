"""Model-driven planning with strict bounds and safe fallback."""

from __future__ import annotations

import json
from typing import Any

from app.knowledge.query_expansion import expand_query
from app.models.task import AgentPlan, Capability, PlanStep, Task
from app.models.types import ChatMessage, ModelRequest


class ModelPlanningEngine:
    def __init__(self, provider, model: str, fallback=None) -> None:
        self.provider = provider
        self.model = model
        self.fallback = fallback

    async def build_plan(self, task: Task, max_steps: int = 8) -> AgentPlan:
        request = ModelRequest(messages=(
            ChatMessage(
                role="system",
                content=(
                    "Create a concise execution plan. Return ONLY JSON: "
                    '{"steps":[{"id":"...","objective":"...","capability":"reasoning|research|coding|documents","tool":null}]}'. 
                    " Use only bounded, necessary steps. Never include hidden reasoning."
                ),
            ),
            ChatMessage(role="user", content=task.goal),
        ), temperature=0.0, max_tokens=700)
        try:
            response = await self.provider.chat(self.model, request)
            payload = json.loads(response.content)
            raw_steps = payload.get("steps", [])
            steps: list[PlanStep] = []
            allowed = {item.value: item for item in Capability}
            for raw in raw_steps[:max_steps]:
                capability = allowed.get(str(raw.get("capability", "reasoning")), Capability.REASONING)
                tool = raw.get("tool")
                if tool not in {"knowledge.retrieve", "web.search", "code.sandbox", None}:
                    tool = None
                steps.append(PlanStep(
                    id=str(raw.get("id", f"step_{len(steps)+1}"))[:80],
                    objective=str(raw.get("objective", ""))[:500],
                    capability=capability,
                    tool=tool,
                ))
            if steps:
                return AgentPlan(task.goal, tuple(steps))
        except Exception:
            pass
        return self.fallback.build_plan(task) if self.fallback else AgentPlan(task.goal, ())
