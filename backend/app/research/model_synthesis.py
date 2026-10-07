"""Model-backed synthesis for citation-aware deep research."""

from __future__ import annotations

from dataclasses import dataclass

from app.models.types import ChatMessage, ModelRequest
from app.router import ModelRouter
from app.research.synthesis import Synthesis


@dataclass(frozen=True)
class ResearchReport:
    answer: str
    model: str
    provider: str
    citations: tuple[str, ...]


class ModelResearchSynthesizer:
    def __init__(self, router: ModelRouter) -> None:
        self.router = router

    async def synthesize(self, query: str, synthesis: Synthesis) -> ResearchReport:
        evidence = synthesis.evidence[:10]
        source_blocks = []
        for index, item in enumerate(evidence, 1):
            source_blocks.append(
                f"[S{index}] {item.title}\nURL: {item.uri}\n{item.text[:6000]}"
            )

        prompt = (
            "Answer the research question using only the supplied evidence. "
            "Be precise about uncertainty and conflicting evidence. "
            "Cite factual claims inline with [S#] markers. Do not invent sources.\n\n"
            f"QUESTION:\n{query}\n\n"
            "EVIDENCE:\n" + "\n\n".join(source_blocks)
        )
        choice = self.router.choose(query + " research evidence", None)
        response = await choice.provider.chat(
            choice.model,
            ModelRequest(
                messages=(
                    ChatMessage(
                        role="system",
                        content="You are NOVA's evidence-grounded research synthesizer.",
                    ),
                    ChatMessage(role="user", content=prompt),
                ),
                temperature=0.1,
                max_tokens=4000,
            ),
        )
        citations = tuple(
            item.uri for index, item in enumerate(evidence, 1)
            if f"[S{index}]" in response.content
        )
        return ResearchReport(
            answer=response.content,
            model=response.model,
            provider=response.provider,
            citations=citations,
        )
