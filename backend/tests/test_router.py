from app.models.base import ModelInfo
from app.models.types import ChatMessage
from app.providers.mock import MockProvider
from app.router import ModelRouter
from app.agents.orchestrator import AgentOrchestrator
import pytest

class SpecialistProvider(MockProvider):
    def list_models(self) -> list[ModelInfo]:
        return [
            ModelInfo("vision-model", "specialist", ("chat", "multimodal"), 131072, True, True, True),
            ModelInfo("code-model", "specialist", ("chat", "coding", "reasoning"), 65536, True, False, True),
        ]

def test_router_prefers_reasoning_for_analysis_tasks():
    router = ModelRouter([MockProvider()])
    choice = router.choose("Analyze this complex problem")
    assert choice.model == "nova-mock"
    assert "reasoning" in choice.reason

def test_router_prefers_vision_capability_for_image_tasks():
    router = ModelRouter([SpecialistProvider(), MockProvider()])
    choice = router.choose("Analyze this screenshot")
    assert choice.model == "vision-model"
    assert choice.score > 0

def test_router_prefers_tools_for_coding_tasks():
    router = ModelRouter([SpecialistProvider(), MockProvider()])
    choice = router.choose("Debug this Python code")
    assert choice.model == "code-model"

@pytest.mark.asyncio
async def test_orchestrator_runs():
    agent = AgentOrchestrator(ModelRouter([MockProvider()]))
    result = await agent.run("Say hello", [ChatMessage(role="user", content="Hello NOVA")])
    assert result.response.provider == "mock"
    assert "Hello NOVA" in result.response.content

class FailingProvider(MockProvider):
    async def chat(self, model, request):
        raise RuntimeError("simulated outage")

@pytest.mark.asyncio
async def test_orchestrator_falls_back_after_provider_failure():
    agent = AgentOrchestrator(ModelRouter([FailingProvider(), MockProvider()]))
    result = await agent.run("Say hello", [ChatMessage(role="user", content="fallback works")])
    assert result.response.provider == "mock"
    assert "recovered" in result.model_reason
