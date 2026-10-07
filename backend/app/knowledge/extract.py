"""Document extraction before knowledge chunking."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any


def extract_document(data: bytes, filename: str, mime_type: str) -> dict[str, Any]:
    suffix = Path(filename).suffix.lower()
    if mime_type == "application/pdf" or suffix == ".pdf":
        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(data))
            pages = [
                {"page": i + 1, "text": page.extract_text() or ""}
                for i, page in enumerate(reader.pages)
            ]
            return {
                "kind": "pdf",
                "pages": pages,
                "page_count": len(pages),
                "text": "\n\n".join(page["text"] for page in pages),
            }
        except Exception as exc:
            raise ValueError("Unable to extract text from PDF") from exc

    text = extract_text(data, filename, mime_type)
    return {
        "kind": "text",
        "pages": [{"page": 1, "text": text}],
        "page_count": 1,
        "text": text,
    }


def extract_text(data: bytes, filename: str, mime_type: str) -> str:
    suffix = Path(filename).suffix.lower()
    if mime_type in {"text/plain", "text/markdown", "text/csv", "application/json"} or suffix in {
        ".txt", ".md", ".csv", ".json", ".py", ".ts", ".tsx", ".js", ".jsx"
    }:
        return data.decode("utf-8", errors="replace")

    if mime_type == "application/pdf" or suffix == ".pdf":
        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(data))
            return "\n\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as exc:
            raise ValueError("Unable to extract text from PDF") from exc

    if (
        mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        or suffix == ".docx"
    ):
        try:
            from docx import Document

            document = Document(io.BytesIO(data))
            return "\n\n".join(paragraph.text for paragraph in document.paragraphs)
        except Exception as exc:
            raise ValueError("Unable to extract text from DOCX") from exc

    raise ValueError("Unsupported document format")
