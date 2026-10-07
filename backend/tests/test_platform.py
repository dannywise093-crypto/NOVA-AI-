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


from app.knowledge.ingest import DocumentIngestor
from app.knowledge.vector import InMemoryVectorStore


def test_document_ingestor_chunks_text():
    chunks = DocumentIngestor().chunk("doc-1", "a" * 250, chunk_size=100)
    assert len(chunks) == 3
    assert chunks[0].document_id == "doc-1"


@pytest.mark.asyncio
async def test_vector_store_returns_relevant_chunk():
    store = InMemoryVectorStore()
    await store.upsert(DocumentIngestor().chunk("doc-2", "NOVA research platform architecture", chunk_size=100))
    results = await store.search("NOVA architecture")
    assert results
    assert "architecture" in results[0].text


from app.tools.permissions import PermissionPolicy, ToolPermission


def test_permission_policy_blocks_network_by_default():
    assert PermissionPolicy().allowed("network") is False
    assert PermissionPolicy(ToolPermission(allow_network=True)).allowed("network") is True


from app.conversations.base import Conversation, Message
from app.conversations.store import ConversationStore


def test_conversation_store_persists_messages():
    store = ConversationStore()
    conversation = store.create(Conversation("conv-1", "NOVA task"))
    conversation.add_message(Message("msg-1", "user", "Build NOVA"))
    store.save(conversation)
    loaded = store.get("conv-1")
    assert loaded is not None
    assert loaded.messages[0].content == "Build NOVA"
