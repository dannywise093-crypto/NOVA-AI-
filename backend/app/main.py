from fastapi import FastAPI
from app.api.health import router as health_router

app = FastAPI(
    title="NOVA AI API",
    version="0.1.0",
    description="The orchestration backend for NOVA AI.",
)

app.include_router(health_router, prefix="/api")

@app.get("/")
async def root() -> dict[str, str]:
    return {"name": "NOVA AI", "version": "0.1.0", "status": "online"}
