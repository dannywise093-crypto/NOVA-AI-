from app.conversations.base import Conversation


class ConversationStore:
    """Persistence contract with an in-memory development implementation."""

    def __init__(self) -> None:
        self._items: dict[str, Conversation] = {}

    def create(self, conversation: Conversation) -> Conversation:
        if conversation.id in self._items:
            raise ValueError(f"Conversation already exists: {conversation.id}")
        self._items[conversation.id] = conversation
        return conversation

    def get(self, conversation_id: str) -> Conversation | None:
        return self._items.get(conversation_id)

    def list(self, project_id: str | None = None) -> list[Conversation]:
        items = list(self._items.values())
        if project_id is not None:
            items = [item for item in items if item.project_id == project_id]
        return items

    def save(self, conversation: Conversation) -> Conversation:
        if conversation.id not in self._items:
            raise ValueError(f"Conversation does not exist: {conversation.id}")
        self._items[conversation.id] = conversation
        return conversation
