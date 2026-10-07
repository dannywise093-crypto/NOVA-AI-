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

async def search_chunks(session: AsyncSession, project_id: str, query: str, limit: int = 8, artifact_id: str | None = None) -> list[KnowledgeItem]:
    statement = select(KnowledgeChunkRow).where(KnowledgeChunkRow.project_id == project_id)
    if artifact_id:
        statement = statement.where(KnowledgeChunkRow.artifact_id == artifact_id)
    rows = (await session.scalars(statement)).all()
    import re
    terms = set(re.findall(r"[a-z0-9_]+", query.lower()))
    query_embedding = None
    try:
        from app.knowledge.embeddings import HashEmbeddingProvider
        query_embedding = await HashEmbeddingProvider().embed(query)
    except Exception:
        pass
    def score(row):
        words = set(re.findall(r"[a-z0-9_]+", row.text.lower()))
        lexical = len(terms & words) / max(1, len(terms))
        phrase_bonus = 0.25 if query.lower() in row.text.lower() else 0.0
        if not query_embedding or not row.embedding:
            return lexical
        vector = json.loads(row.embedding)
        cosine = sum(a * b for a, b in zip(query_embedding, vector)) / max(1, math.sqrt(sum(a*a for a in query_embedding)) * math.sqrt(sum(b*b for b in vector)))
        return lexical * 5 + cosine * 5 + phrase_bonus
    ranked = sorted(rows, key=score, reverse=True)
    selected = []
    seen_artifacts: set[str] = set()
    for row in ranked:
        if len(selected) >= limit:
            break
        # Avoid returning only one artifact when several documents contain useful evidence.
        if row.artifact_id in seen_artifacts and len(selected) < max(2, limit // 2):
            continue
        selected.append(row)
        seen_artifacts.add(row.artifact_id)
    result = []
    for row in selected:
        overlap = len(terms & set(re.findall(r"[a-z0-9_]+", row.text.lower())))
        result.append(KnowledgeItem(
            id=row.id,
            text=row.text,
            source=KnowledgeSource(id=row.artifact_id, title=row.artifact_id, source_type="artifact"),
            score=float(overlap),
            metadata={"project_id": project_id, "chunk_index": str(row.chunk_index)},
        ))
    return result
