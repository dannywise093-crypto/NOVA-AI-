from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class AgentEventType(StrEnum):
    TASK_STARTED = "task.started"
    PLAN_CREATED = "plan.created"
    STEP_STARTED = "step.started"
    TOOL_STARTED = "tool.started"
    TOOL_FINISHED = "tool.finished"
    STEP_FINISHED = "step.finished"
    RESPONSE_DELTA = "response.delta"
    VERIFICATION = "verification"
    TASK_FINISHED = "task.finished"
    ERROR = "error"


@dataclass(frozen=True)
class AgentEvent:
    type: AgentEventType
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)
