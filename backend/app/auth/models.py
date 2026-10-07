from dataclasses import dataclass, field
from datetime import datetime, timezone


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class User:
    id: str
    email: str
    password_hash: str
    created_at: str = field(default_factory=now_iso)
    disabled: bool = False
