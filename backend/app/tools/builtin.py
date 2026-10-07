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
    @property
    def spec(self) -> ToolSpec:
        return ToolSpec("knowledge.retrieve", "Retrieve relevant indexed project knowledge", ("knowledge",))

    async def execute(self, arguments: dict) -> ToolResult:
        return ToolResult(tool=self.spec.name, output={"items": [], "query": arguments.get("query", "")})
