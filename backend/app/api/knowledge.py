from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.knowledge.ingest import DocumentIngestor
from app.knowledge.vector import InMemoryVectorStore

router = APIRouter(tags=["knowledge"])
ingestor = DocumentIngestor()
store = InMemoryVectorStore()


class DocumentIngestRequest(BaseModel):
    document_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    chunk_size: int = 1600


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int = 8


@router.post("/knowledge/ingest")
async def ingest_document(request: DocumentIngestRequest) -> dict[str, object]:
    chunks = ingestor.chunk(request.document_id, request.text, chunk_size=request.chunk_size)
    await store.upsert(chunks)
    return {"document_id": request.document_id, "chunks": len(chunks)}


@router.post("/knowledge/search")
async def search_knowledge(request: KnowledgeSearchRequest) -> dict[str, object]:
    chunks = await store.search(request.query, limit=request.limit)
    return {"query": request.query, "results": [{"id": c.id, "document_id": c.document_id, "text": c.text, "index": c.index} for c in chunks]}
