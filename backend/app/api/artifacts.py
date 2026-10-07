from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.artifacts.base import ProjectArtifact
from app.artifacts.store import ArtifactStore
from app.knowledge.ingest import DocumentIngestor
from app.knowledge.vector import InMemoryVectorStore

router = APIRouter(tags=["artifacts"])
store = ArtifactStore()
ingestor = DocumentIngestor()
vector_store = InMemoryVectorStore()

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
TEXT_TYPES = {"text/plain", "text/markdown", "text/csv", "application/json"}
TEXT_SUFFIXES = {".txt", ".md", ".csv", ".json", ".py", ".ts", ".tsx", ".js", ".jsx"}


@router.post("/artifacts/upload", response_model=ProjectArtifact)
async def upload_artifact(
    project_id: str = Form(min_length=1, max_length=100),
    file: UploadFile = File(...),
) -> ProjectArtifact:
    filename = Path(file.filename or "upload").name
    suffix = Path(filename).suffix.lower()
    mime_type = file.content_type or "application/octet-stream"

    if mime_type not in TEXT_TYPES and suffix not in TEXT_SUFFIXES:
        raise HTTPException(status_code=415, detail="Only text-based documents are supported in this foundation release")

    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds the 10 MB upload limit")

    artifact_id = str(uuid4())
    storage_key = f"dev://artifacts/{project_id}/{artifact_id}/{filename}"
    artifact = store.create(ProjectArtifact(
        id=artifact_id,
        project_id=project_id,
        name=filename,
        mime_type=mime_type,
        size_bytes=len(data),
        storage_key=storage_key,
    ))

    text = data.decode("utf-8", errors="replace")
    chunks = ingestor.chunk(artifact_id, text)
    await vector_store.upsert(chunks)
    return artifact


@router.get("/artifacts", response_model=list[ProjectArtifact])
async def list_artifacts(project_id: str | None = None) -> list[ProjectArtifact]:
    return store.list(project_id)
