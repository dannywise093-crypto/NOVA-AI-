from fastapi import FastAPI

from app.core.config import settings
from app.api.chat import router as chat_router
from app.api.health import router as health_router
from app.api.models import router as models_router
from app.api.projects import router as projects_router
from app.api.tasks import router as tasks_router
from app.api.knowledge import router as knowledge_router
from app.api.stream import router as stream_router
from app.api.research import router as research_router
from app.api.events import router as events_router
from app.api.conversations_db import router as conversations_router
from app.api.artifacts import router as artifacts_router
from app.api.auth_db import router as auth_router
from app.api.memory import router as memory_router
from app.api.agent_tasks import router as agent_tasks_router
from app.api.tool_approvals import router as tool_approvals_router
from app.tasks.durable_worker import durable_task_worker

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
app.include_router(research_router, prefix="/api")
app.include_router(events_router, prefix="/api")
app.include_router(conversations_router, prefix="/api")
app.include_router(artifacts_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(memory_router, prefix="/api")
app.include_router(agent_tasks_router, prefix="/api")
app.include_router(tool_approvals_router, prefix="/api")

@app.on_event("startup")
async def startup() -> None:
    if settings.environment == "development":
        from app.db.bootstrap import create_schema
        await create_schema()
    await durable_task_worker.start()

@app.on_event("shutdown")
async def shutdown() -> None:
    await durable_task_worker.stop()


@app.get("/")
async def root() -> dict[str, str]:
    return {"name": "NOVA AI", "version": "0.2.0", "status": "online", "platform": "ai"}
