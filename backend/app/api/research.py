from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.config import settings
from app.research.http_provider import HttpSearchProvider
from app.research.engine import ResearchEngine
from app.research.synthesis import EvidenceSynthesizer
from app.research.search import UnconfiguredSearchProvider
from app.research.model_synthesis import ModelResearchSynthesizer
from app.core.container import build_providers
from app.router import ModelRouter
from app.auth.dependencies import get_current_user
from app.auth.models import User

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
async def research_search(request: ResearchRequest, current_user: User = Depends(get_current_user)) -> dict[str, object]:
    engine = ResearchEngine(provider)
    bundle = await engine.gather(request.query, rounds=2, limit_per_round=request.limit)
    synthesis = EvidenceSynthesizer().synthesize(request.query, list(bundle.evidence))
    report = await ModelResearchSynthesizer(ModelRouter(build_providers())).synthesize(request.query, synthesis)
    return {
        "query": request.query,
        "sources": [source.__dict__ for source in bundle.sources],
        "claims": [claim.__dict__ for claim in synthesis.claims],
        "report": {
            "answer": report.answer,
            "model": report.model,
            "provider": report.provider,
            "citations": list(report.citations),
        },
        "evidence": [
            {
                "uri": item.uri,
                "title": item.title,
                "text": item.text[:12000],
                "status_code": item.status_code,
                "content_type": item.content_type,
            }
            for item in synthesis.evidence
        ],
        "configured": not isinstance(provider, UnconfiguredSearchProvider),
    }
