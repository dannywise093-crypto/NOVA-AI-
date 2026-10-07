from fastapi import APIRouter

from app.core.container import build_providers
from app.router import ModelRouter

router = APIRouter(tags=["models"])
router_instance = ModelRouter(build_providers())


@router.get("/models")
async def models() -> list[dict[str, object]]:
    return [
        {
            "id": model.id,
            "provider": model.provider,
            "capabilities": list(model.capabilities),
        }
        for model in router_instance.available_models()
    ]
