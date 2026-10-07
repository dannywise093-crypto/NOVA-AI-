import pytest

from app.models.types import ChatMessage
from app.providers.mock import MockProvider
from app.router import ModelRouter
from app.agents.orchestrator import AgentOrchestrator

def test_router_prefers_reasoning_for_analysis_tasks():
    router = ModelRouter([MockProvider()])
    choice = router.choose("Analyze this complex problem")
    assert choice.model == "nova-mock"
    assert "reasoning" in choice.reason

@pytest.mark.asyncio
async def test_orchestrator_runs():
    agent = AgentOrchestrator(ModelRouter([MockProvider()]))
    result = await agent.run(
        "Say hello",
        [ChatMessage(role="user", content="Hello NOVA")],
    )
    assert result.response.provider == "mock"
    assert "Hello NOVA" in result.response.content
