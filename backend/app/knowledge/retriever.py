from app.knowledge.base import KnowledgeItem


class KnowledgeRetriever:
    """Retrieval contract; vector/search implementations can plug in later."""

    async def search(self, query: str, *, limit: int = 8) -> list[KnowledgeItem]:
        return []
