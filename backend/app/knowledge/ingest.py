from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentChunk:
    id: str
    document_id: str
    text: str
    index: int
    metadata: dict[str, str]


class DocumentIngestor:
    """Deterministic chunker with optional page provenance."""

    def chunk(self, document_id: str, text: str, *, chunk_size: int = 1600) -> list[DocumentChunk]:
        return self._chunk_parts(document_id, [(1, text)], chunk_size=chunk_size)

    def chunk_pages(self, document_id: str, pages: list[dict[str, object]], *, chunk_size: int = 1600) -> list[DocumentChunk]:
        parts = [(int(page["page"]), str(page.get("text", ""))) for page in pages]
        return self._chunk_parts(document_id, parts, chunk_size=chunk_size)

    def _chunk_parts(self, document_id: str, parts: list[tuple[int, str]], *, chunk_size: int) -> list[DocumentChunk]:
        if chunk_size < 100:
            raise ValueError("chunk_size must be at least 100")
        chunks: list[DocumentChunk] = []
        index = 0
        for page, text in parts:
            for start in range(0, len(text), chunk_size):
                value = text[start:start + chunk_size]
                if value:
                    chunks.append(DocumentChunk(f"{document_id}:{index}", document_id, value, index, {"source_page": str(page)}))
                    index += 1
        return chunks
