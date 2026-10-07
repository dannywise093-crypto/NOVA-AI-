from datetime import datetime
import json
import math
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import Base
from sqlalchemy.orm import Mapped, mapped_column
from app.knowledge.base import KnowledgeItem, KnowledgeSource

class KnowledgeChunkRow(Base):
    __tablename__ = "knowledge_chunks"
    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    artifact_id: Mapped[str] = mapped_column(ForeignKey("artifacts.id"), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    embedding: Mapped[str | None] = mapped_column(Text, nullable=True)

async def replace_chunks(session: AsyncSession, project_id: str, artifact_id: str, chunks: list[tuple[str, int, str, list[float] | None]]) -> None:
    rows = (await session.scalars(select(KnowledgeChunkRow).where(KnowledgeChunkRow.artifact_id == artifact_id))).all()
    for row in rows:
        await session.delete(row)
    for chunk_id, index, text, embedding in chunks:
        session.add(KnowledgeChunkRow(id=chunk_id, project_id=project_id, artifact_id=artifact_id, chunk_index=index, text=text, embedding=json.dumps(embedding) if embedding else None, created_at=datetime.now()))
    await session.commit()

async def search_chunks(session: AsyncSession, project_id: str, query: str, limit: int = 8) -> list[KnowledgeItem]:
    rows = (await session.scalars(select(KnowledgeChunkRow).where(KnowledgeChunkRow.project_id == project_id))).all()
    terms = set(query.lower().split())
    query_embedding = None
    try:
        from app.knowledge.embeddings import HashEmbeddingProvider
        query_embedding = await HashEmbeddingProvider().embed(query)
    except Exception:
        pass
    def score(row):
        lexical = len(terms & set(row.text.lower().split()))
        if not query_embedding or not row.embedding:
            return lexical
        vector = json.loads(row.embedding)
        cosine = sum(a * b for a, b in zip(query_embedding, vector)) / max(1, math.sqrt(sum(a*a for a in query_embedding)) * math.sqrt(sum(b*b for b in vector)))
        return lexical + cosine * 5
    ranked = sorted(rows, key=score, reverse=True)
    result = []
    for row in ranked[:limit]:
        overlap = len(terms & set(row.text.lower().split()))
        result.append(KnowledgeItem(
            id=row.id,
            text=row.text,
            source=KnowledgeSource(id=row.artifact_id, title=row.artifact_id, source_type="artifact"),
            score=float(overlap),
            metadata={"project_id": project_id, "chunk_index": str(row.chunk_index)},
        ))
    return result
