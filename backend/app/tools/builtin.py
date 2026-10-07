from sqlalchemy.ext.asyncio import AsyncSession
from app.db.knowledge_repository import search_chunks
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
    def __init__(self, session: AsyncSession | None = None) -> None:
        self.session = session
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
        items = await search_chunks(self.session, project_id, query, int(arguments.get("limit", 8)))
        return ToolResult(self.spec.name, {
            "query": query,
            "items": [{"id": item.id, "text": item.text, "score": item.score, "source": item.source.id, "metadata": item.metadata} for item in items],
        })
