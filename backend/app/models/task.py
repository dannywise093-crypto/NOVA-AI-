from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class Capability(StrEnum):
    CHAT = "chat"
    REASONING = "reasoning"
    RESEARCH = "research"
    CODING = "coding"
    MULTIMODAL = "multimodal"
    DOCUMENTS = "documents"
    AGENTIC = "agentic"
    INTEGRATIONS = "integrations"
    REAL_TIME = "real_time"


@dataclass(frozen=True)
class Task:
    goal: str
    capabilities: tuple[Capability, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PlanStep:
    id: str
    objective: str
    capability: Capability = Capability.REASONING
    tool: str | None = None
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AgentPlan:
    goal: str
    steps: tuple[PlanStep, ...]
