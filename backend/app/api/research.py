from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.research.search import UnconfiguredSearchProvider

router = APIRouter(tags=["research"])
provider = UnconfiguredSearchProvider()


class ResearchRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int = 8


@router.post("/research/search")
async def research_search(request: ResearchRequest) -> dict[str, object]:
    sources = await provider.search(request.query, limit=request.limit)
    return {"query": request.query, "sources": [source.__dict__ for source in sources]}
