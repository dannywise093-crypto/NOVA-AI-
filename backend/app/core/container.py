from app.agents.orchestrator import AgentOrchestrator
from app.core.config import settings
from app.providers.mock import MockProvider
from app.providers.openai_compatible import OpenAICompatibleProvider
from app.router import ModelRouter


def build_providers() -> list:
    providers = [MockProvider()]

    if settings.model_api_key and settings.model_name:
        providers.insert(
            0,
            OpenAICompatibleProvider(
                base_url=settings.model_base_url,
                api_key=settings.model_api_key,
                model=settings.model_name,
                provider_name=settings.model_provider_name,
            ),
        )

    return providers


def build_orchestrator() -> AgentOrchestrator:
    return AgentOrchestrator(ModelRouter(build_providers()))
