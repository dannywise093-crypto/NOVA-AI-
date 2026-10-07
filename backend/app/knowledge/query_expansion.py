"""Deterministic query expansion for project knowledge retrieval."""

from __future__ import annotations

import re


def expand_query(query: str, max_queries: int = 4) -> list[str]:
    """Return bounded alternate formulations without requiring an LLM."""
    clean = " ".join(query.split()).strip()
    if not clean:
        return []
    queries = [clean]
    tokens = re.findall(r"[a-z0-9_]+", clean.lower())

    # Keyword-focused view helps lexical retrieval when the original question is verbose.
    if len(tokens) > 3:
        keyword_query = " ".join(tokens[:12])
        if keyword_query != clean.lower():
            queries.append(keyword_query)

    # Question framing variants improve recall for explanatory requests.
    if clean.lower().startswith(("what is ", "what are ")):
        queries.append(clean[8:] + " definition")
    elif clean.lower().startswith(("how do ", "how does ", "how can ")):
        queries.append(clean + " implementation steps")
    elif clean.lower().startswith(("why ",)):
        queries.append(clean + " rationale explanation")

    result: list[str] = []
    seen: set[str] = set()
    for item in queries:
        normalized = item.lower().strip()
        if normalized and normalized not in seen:
            result.append(item)
            seen.add(normalized)
        if len(result) >= max_queries:
            break
    return result
