import pytest

from app.agents.planner import TaskPlanner
from app.models.task import Capability, Task
from app.models.tool import ToolResult, ToolSpec
from app.tools.registry import ToolRegistry


class EchoTool:
    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(name="echo", description="Echo input")

    async def execute(self, arguments: dict) -> ToolResult:
        return ToolResult(tool="echo", output=arguments)


def test_planner_builds_research_and_verification_steps():
    plan = TaskPlanner().plan(Task("Research current AI models", (Capability.RESEARCH,)))
    assert plan.steps[0].tool == "web.search"
    assert plan.steps[-1].id == "verify"


@pytest.mark.asyncio
async def test_tool_registry_executes_registered_tool():
    registry = ToolRegistry([EchoTool()])
    result = await registry.execute("echo", {"value": "nova"})
    assert result.success is True
    assert result.output["value"] == "nova"


@pytest.mark.asyncio
async def test_tool_registry_rejects_unknown_tool():
    result = await ToolRegistry().execute("missing", {})
    assert result.success is False
    assert result.error == "Unknown tool"
