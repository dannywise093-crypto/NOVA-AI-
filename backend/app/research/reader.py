"""Fetch and extract readable evidence from research sources."""

from __future__ import annotations

import re
from dataclasses import dataclass
from html import unescape

import httpx


@dataclass(frozen=True)
class Evidence:
    uri: str
    title: str
    text: str
    status_code: int
    content_type: str


class SourceReader:
    def __init__(self, *, timeout: float = 12.0, max_bytes: int = 1_000_000) -> None:
        self.timeout = timeout
        self.max_bytes = max_bytes

    async def read(self, uri: str, *, title: str = "") -> Evidence | None:
        if not uri.startswith(("http://", "https://")):
            return None

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                headers={"User-Agent": "NOVA-AI-Research/1.0"},
            ) as client:
                response = await client.get(uri)
                response.raise_for_status()
                body = response.content[:self.max_bytes]
        except (httpx.HTTPError, ValueError):
            return None

        content_type = response.headers.get("content-type", "")
        if "html" in content_type:
            text = self._html_to_text(body.decode("utf-8", errors="replace"))
        else:
            text = body.decode("utf-8", errors="replace")

        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            return None

        return Evidence(
            uri=str(response.url),
            title=title or str(response.url),
            text=text[:200_000],
            status_code=response.status_code,
            content_type=content_type,
        )

    @staticmethod
    def _html_to_text(html: str) -> str:
        html = re.sub(r"(?is)<(script|style|noscript|svg).*?>.*?</\1>", " ", html)
        html = re.sub(r"(?is)<[^>]+>", " ", html)
        return unescape(html)
