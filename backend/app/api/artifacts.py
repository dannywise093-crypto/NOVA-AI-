from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from app.artifacts.base import ProjectArtifact
from app.artifacts.storage import build_artifact_storage
from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.db.artifact_repository import create_artifact, list_artifacts
from app.db.project_repository import get_project, list_projects
from app.db.knowledge_repository import replace_chunks
from app.db.session import get_session
from app.knowledge.ingest import DocumentIngestor
from app.knowledge.extract import extract_text
from app.knowledge.vector import InMemoryVectorStore

router = APIRouter(tags=["artifacts"])
ingestor = DocumentIngestor()
vector_store = InMemoryVectorStore()
storage = build_artifact_storage()

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
TEXT_TYPES = {"text/plain", "text/markdown", "text/csv", "application/json", "application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
TEXT_SUFFIXES = {".txt", ".md", ".csv", ".json", ".py", ".ts", ".tsx", ".js", ".jsx", ".pdf", ".docx"}

@router.post("/artifacts/upload", response_model=ProjectArtifact)
async def upload_artifact(
    project_id: str = Form(min_length=1, max_length=100),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ProjectArtifact:
    project = await get_project(session, project_id, user.id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    filename = Path(file.filename or "upload").name
    suffix = Path(filename).suffix.lower()
    mime_type = file.content_type or "application/octet-stream"
    if mime_type not in TEXT_TYPES and suffix not in TEXT_SUFFIXES:
        raise HTTPException(status_code=415, detail="Only text-based documents are supported in this foundation release")
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds the 10 MB upload limit")
    artifact_id = str(uuid4())
    storage_key = await storage.put(f"artifacts/{project_id}/{artifact_id}/{filename}", data)
    artifact = await create_artifact(session, ProjectArtifact(
        id=artifact_id, project_id=project_id, name=filename, mime_type=mime_type,
        size_bytes=len(data), storage_key=storage_key,
    ))
    try:
        text = extract_text(data, filename, mime_type)
    except ValueError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    chunks = ingestor.chunk(artifact_id, text)
    await vector_store.upsert(chunks)
    await replace_chunks(session, project_id, artifact_id, [(chunk.id, chunk.index, chunk.text) for chunk in chunks])
    return artifact

@router.get("/artifacts/{artifact_id}/content")
async def get_artifact_content(
    artifact_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    projects = await list_projects(session, user.id)
    allowed = {item.id for item in projects}
    artifacts = await list_artifacts(session, allowed)
    artifact = next((item for item in artifacts if item.id == artifact_id), None)
    if artifact is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return {
        "artifact_id": artifact.id,
        "project_id": artifact.project_id,
        "name": artifact.name,
        "mime_type": artifact.mime_type,
        "storage_key": artifact.storage_key,
    }

@router.get("/artifacts", response_model=list[ProjectArtifact])
async def list_artifacts_endpoint(
    project_id: str | None = None,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[ProjectArtifact]:
    projects = await list_projects(session, user.id)
    allowed_projects = {item.id for item in projects}
    if project_id is not None and project_id not in allowed_projects:
        raise HTTPException(status_code=404, detail="Project not found")
    return await list_artifacts(session, {project_id} if project_id else allowed_projects)
