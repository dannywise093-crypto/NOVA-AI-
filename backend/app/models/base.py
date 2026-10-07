from dataclasses import dataclass, field


@dataclass(frozen=True)
class ModelInfo:
    id: str
    provider: str
    capabilities: tuple[str, ...]
    context_window: int | None = None
    supports_tools: bool = False
    supports_vision: bool = False
    supports_streaming: bool = True
    metadata: dict[str, object] = field(default_factory=dict)
