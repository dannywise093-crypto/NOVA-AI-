"""Document extraction before knowledge chunking."""

from __future__ import annotations

from pathlib import Path


def extract_text(data: bytes, filename: str, mime_type: str) -> str:
    suffix = Path(filename).suffix.lower()
    if mime_type in {"text/plain", "text/markdown", "text/csv", "application/json"} or suffix in {
        ".txt", ".md", ".csv", ".json", ".py", ".ts", ".tsx", ".js", ".jsx"
    }:
        return data.decode("utf-8", errors="replace")

    if mime_type == "application/pdf" or suffix == ".pdf":
        try:
            from pypdf import PdfReader
            import io
            reader = PdfReader(io.BytesIO(data))
            return "\n\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as exc:
            raise ValueError("Unable to extract text from PDF") from exc

    if mime_type in {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    } or suffix == ".docx":
        try:
            from docx import Document
            import io
            document = Document(io.BytesIO(data))
            return "\n\n".join(p.text for p in document.paragraphs)
        except Exception as exc:
            raise ValueError("Unable to extract text from DOCX") from exc

    raise ValueError("Unsupported document format")
