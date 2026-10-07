from app.agents.orchestrator import AgentOrchestrator
from app.core.config import settings
from app.providers.mock import MockProvider
from app.providers.openai_compatible import OpenAICompatibleProvider
from app.router import ModelRouter
from app.tools.registry import ToolRegistry
from app.tools.builtin import CurrentTimeTool, KnowledgeRetrieveTool, WebSearchTool
from app.tools.code_sandbox import CodeSandboxTool
from app.knowledge.model_query_expansion import expand_with_model
from app.knowledge.embeddings import build_embedding_provider


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


def build_orchestrator(session=None) -> AgentOrchestrator:
    providers = build_providers()
    expander = lambda query: expand_with_model(query, providers[0], settings.model_name) if settings.model_name else expand_with_model(query)
    tools = ToolRegistry([CurrentTimeTool(), WebSearchTool(), KnowledgeRetrieveTool(session, query_expander=expander, embedding_provider=build_embedding_provider(\n        settings.embedding_base_url or settings.model_base_url,\n        settings.embedding_api_key or settings.model_api_key,\n        settings.embedding_model,\n    )), CodeSandboxTool()])
    return AgentOrchestrator(ModelRouter(build_providers()), tools)
