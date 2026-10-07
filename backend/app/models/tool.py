from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    capabilities: tuple[str, ...] = ()
    requires_confirmation: bool = False


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolResult:
    tool: str
    output: Any
    success: bool = True
    error: str | None = None


class Tool(Protocol):
    @property
    def spec(self) -> ToolSpec: ...

    async def execute(self, arguments: dict[str, Any]) -> ToolResult: ...
