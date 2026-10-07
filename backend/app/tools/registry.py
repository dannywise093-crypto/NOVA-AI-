from app.models.tool import Tool, ToolResult, ToolSpec


class ToolRegistry:
    def __init__(self, tools: list[Tool] | None = None) -> None:
        self._tools = {tool.spec.name: tool for tool in (tools or [])}

    def register(self, tool: Tool) -> None:
        if tool.spec.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.spec.name}")
        self._tools[tool.spec.name] = tool

    def specs(self) -> list[ToolSpec]:
        return [tool.spec for tool in self._tools.values()]

    async def execute(self, name: str, arguments: dict) -> ToolResult:
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult(tool=name, output=None, success=False, error="Unknown tool")
        try:
            return await tool.execute(arguments)
        except Exception as exc:
            return ToolResult(tool=name, output=None, success=False, error=str(exc))
