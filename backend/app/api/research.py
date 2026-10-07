from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.config import settings
from app.research.http_provider import HttpSearchProvider
from app.research.search import UnconfiguredSearchProvider

router = APIRouter(tags=["research"])

provider = (
    HttpSearchProvider(settings.search_base_url, settings.search_api_key)
    if settings.search_base_url and settings.search_api_key
    else UnconfiguredSearchProvider()
)


class ResearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    limit: int = Field(default=8, ge=1, le=20)


@router.post("/research/search")
async def research_search(request: ResearchRequest) -> dict[str, object]:
    sources = await provider.search(request.query, limit=request.limit)
    return {
        "query": request.query,
        "sources": [source.__dict__ for source in sources],
        "configured": not isinstance(provider, UnconfiguredSearchProvider),
    }
