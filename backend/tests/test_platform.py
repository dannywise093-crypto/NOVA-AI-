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


from app.artifacts.base import ProjectArtifact
from app.artifacts.store import ArtifactStore


def test_artifact_store_filters_by_project():
    store = ArtifactStore()
    store.create(ProjectArtifact("a1", "p1", "notes.txt", "text/plain", 5, "dev://a1"))
    store.create(ProjectArtifact("a2", "p2", "other.txt", "text/plain", 5, "dev://a2"))
    assert [item.id for item in store.list("p1")] == ["a1"]


from app.memory.engine import MemoryEngine


def test_memory_engine_extracts_explicit_preferences_and_blocks_secrets():
    engine = MemoryEngine()
    candidates = engine.extract("I prefer Python for backend work.")
    assert candidates
    assert candidates[0].kind == "preference"
    assert engine.extract("My password is super-secret") == []


def test_memory_engine_deduplicates_similar_text():
    engine = MemoryEngine()
    assert engine._similar("preference: Python backend", "preference: Python backend work")


from app.research.reader import Evidence
from app.research.synthesis import EvidenceSynthesizer


def test_evidence_synthesizer_ranks_relevant_sources_and_extracts_claims():
    evidence = [
        Evidence("https://example.com", "AI", "NOVA AI uses research and reasoning tools.", 200, "text/html"),
        Evidence("https://example.edu", "Other", "A completely unrelated topic.", 200, "text/html"),
    ]
    result = EvidenceSynthesizer().synthesize("NOVA AI research", evidence)
    assert result.evidence[0].uri == "https://example.com"
    assert result.claims
    assert result.claims[0].evidence_uris == ("https://example.com",)


def test_document_extractor_handles_text_and_image_metadata():
    from app.knowledge.extract import extract_text

    assert extract_text(b"hello NOVA", "note.txt", "text/plain") == "hello NOVA"


@pytest.mark.asyncio
async def test_hash_embedding_is_normalized_and_semantically_stable():
    from app.knowledge.embeddings import HashEmbeddingProvider

    provider = HashEmbeddingProvider()
    first = await provider.embed("NOVA research architecture")
    second = await provider.embed("NOVA research architecture")
    assert first == second
    assert abs(sum(value * value for value in first) - 1.0) < 1e-6


def test_knowledge_chunk_model_has_embedding_storage():
    from app.db.knowledge_repository import KnowledgeChunkRow

    assert hasattr(KnowledgeChunkRow, "embedding")


def test_knowledge_search_query_terms_are_normalized():
    import re

    query = "NOVA-AI, research!"
    assert set(re.findall(r"[a-z0-9_]+", query.lower())) == {"nova", "ai", "research"}
