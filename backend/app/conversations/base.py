from dataclasses import dataclass, field
from datetime import datetime, timezone


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Message:
    id: str
    role: str
    content: str
    created_at: str = field(default_factory=now_iso)


@dataclass
class Conversation:
    id: str
    title: str
    project_id: str | None = None
    messages: list[Message] = field(default_factory=list)
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)

    def add_message(self, message: Message) -> None:
        self.messages.append(message)
        self.updated_at = now_iso()
