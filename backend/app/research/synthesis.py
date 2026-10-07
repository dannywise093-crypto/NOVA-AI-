"""Evidence ranking and lightweight claim synthesis for NOVA research."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.research.reader import Evidence


@dataclass(frozen=True)
class Claim:
    text: str
    evidence_uris: tuple[str, ...]
    confidence: float


@dataclass(frozen=True)
class Synthesis:
    claims: tuple[Claim, ...]
    evidence: tuple[Evidence, ...]
    contradictions: tuple[tuple[str, str], ...] = ()


class EvidenceSynthesizer:
    def rank(self, query: str, evidence: list[Evidence]) -> list[Evidence]:
        terms = set(re.findall(r"\w+", query.lower()))
        def score(item: Evidence) -> tuple[int, int, int]:
            words = set(re.findall(r"\w+", item.text.lower()))
            return (
                len(terms & words),
                1 if ".gov" in item.uri or ".edu" in item.uri else 0,
                min(len(item.text), 100_000),
            )
        return sorted(evidence, key=score, reverse=True)

    def synthesize(self, query: str, evidence: list[Evidence]) -> Synthesis:
        ranked = self.rank(query, evidence)
        claims: list[Claim] = []

        for item in ranked[:10]:
            sentences = re.split(r"(?<=[.!?])\s+", item.text)
            query_terms = set(re.findall(r"\w+", query.lower()))
            relevant = [
                sentence.strip()
                for sentence in sentences
                if len(query_terms & set(re.findall(r"\w+", sentence.lower()))) >= max(1, min(3, len(query_terms)))
            ]
            for sentence in relevant[:3]:
                claims.append(Claim(
                    text=sentence[:1000],
                    evidence_uris=(item.uri,),
                    confidence=min(0.95, 0.45 + 0.05 * len(query_terms & set(re.findall(r"\w+", sentence.lower())))),
                ))

        contradictions: list[tuple[str, str]] = []
        for index, left in enumerate(claims):
            for right in claims[index + 1:]:
                left_words = set(re.findall(r"\\w+", left.text.lower()))
                right_words = set(re.findall(r"\\w+", right.text.lower()))
                overlap = len(left_words & right_words) / max(1, min(len(left_words), len(right_words)))
                negation_conflict = (
                    (" not " in f" {left.text.lower()} " and " not " not in f" {right.text.lower()} ")
                    or (" not " in f" {right.text.lower()} " and " not " not in f" {left.text.lower()} ")
                )
                if overlap >= 0.65 and negation_conflict:
                    contradictions.append((left.text, right.text))
        return Synthesis(
            claims=tuple(claims[:20]),
            evidence=tuple(ranked),
            contradictions=tuple(contradictions[:10]),
        )
