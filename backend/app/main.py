from fastapi import FastAPI
from app.api.chat import router as chat_router
from app.api.health import router as health_router
from app.api.models import router as models_router
from app.api.projects import router as projects_router
from app.api.tasks import router as tasks_router
from app.api.knowledge import router as knowledge_router
from app.api.stream import router as stream_router

app = FastAPI(
    title="NOVA AI API",
    version="0.2.0",
    description="The intelligence, agent, tool, knowledge, and integration backend for NOVA AI.",
)

app.include_router(health_router, prefix="/api")
app.include_router(models_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(projects_router, prefix="/api")
app.include_router(tasks_router, prefix="/api")
app.include_router(knowledge_router, prefix="/api")
app.include_router(stream_router, prefix="/api")


@app.get("/")
async def root() -> dict[str, str]:
    return {"name": "NOVA AI", "version": "0.2.0", "status": "online", "platform": "ai"}
