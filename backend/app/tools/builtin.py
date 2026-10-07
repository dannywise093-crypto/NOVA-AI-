from sqlalchemy.ext.asyncio import AsyncSession
from app.db.knowledge_repository import search_chunks
from app.knowledge.query_expansion import expand_query
from app.models.tool import ToolResult, ToolSpec

class CurrentTimeTool:
    @property
    def spec(self) -> ToolSpec:
        return ToolSpec("system.time", "Return the server UTC time", ("system",))
    async def execute(self, arguments: dict) -> ToolResult:
        from datetime import datetime, timezone
        return ToolResult(tool=self.spec.name, output={"utc": datetime.now(timezone.utc).isoformat()})

class WebSearchTool:
    @property
    def spec(self) -> ToolSpec:
        return ToolSpec("web.search", "Search the web for current information", ("network", "research"), True)
    async def execute(self, arguments: dict) -> ToolResult:
        return ToolResult(tool=self.spec.name, output={"status": "not_configured", "query": arguments.get("query", "")}, success=False, error="Web search provider not configured")

class KnowledgeRetrieveTool:
    def __init__(self, session: AsyncSession | None = None, query_expander=None) -> None:
        self.session = session
        self.query_expander = query_expander
    @property
    def spec(self) -> ToolSpec:
        return ToolSpec("knowledge.retrieve", "Retrieve relevant indexed project knowledge", ("knowledge",))
    async def execute(self, arguments: dict) -> ToolResult:
        query = str(arguments.get("query", "")).strip()
        project_id = str(arguments.get("project_id", "")).strip()
        if self.session is None:
            return ToolResult(self.spec.name, {"items": [], "query": query}, False, "Knowledge database session is not configured")
        if not query or not project_id:
            return ToolResult(self.spec.name, {"items": [], "query": query}, False, "query and project_id are required")
        limit = min(max(int(arguments.get("limit", 8)), 1), 20)
        artifact_id = str(arguments.get("artifact_id", "")).strip() or None
        if self.query_expander is not None:
            queries = await self.query_expander(query)
        else:
            queries = expand_query(query, max_queries=4)
        merged = {}
        for expanded_query in queries:
            items = await search_chunks(
                self.session, project_id, expanded_query,
                min(limit, 8), artifact_id=artifact_id,
            )
            for item in items:
                current = merged.get(item.id)
                if current is None or item.score > current.score:
                    merged[item.id] = item
        items = sorted(merged.values(), key=lambda item: item.score, reverse=True)[:limit]
        return ToolResult(self.spec.name, {
            "query": query,
            "expanded_queries": queries,
            "items": [{"id": item.id, "text": item.text, "score": item.score, "source": item.source.id, "metadata": item.metadata} for item in items],
        })
