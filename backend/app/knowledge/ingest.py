from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentChunk:
    id: str
    document_id: str
    text: str
    index: int
    metadata: dict[str, str]


class DocumentIngestor:
    """Minimal deterministic chunker; embeddings/storage are separate concerns."""

    def chunk(self, document_id: str, text: str, *, chunk_size: int = 1600) -> list[DocumentChunk]:
        if chunk_size < 100:
            raise ValueError("chunk_size must be at least 100")
        chunks = []
        for index, start in enumerate(range(0, len(text), chunk_size)):
            value = text[start:start + chunk_size]
            chunks.append(DocumentChunk(f"{document_id}:{index}", document_id, value, index, {}))
        return chunks
