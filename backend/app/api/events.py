from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.container import build_orchestrator

router = APIRouter(tags=["agent"])
orchestrator = build_orchestrator()


class CapabilityRequest(BaseModel):
    goal: str = Field(min_length=1)


@router.post("/agent/capabilities")
async def capabilities(request: CapabilityRequest) -> dict[str, object]:
    return {"goal": request.goal, "capabilities": [cap.value for cap in orchestrator.infer_capabilities(request.goal)]}
