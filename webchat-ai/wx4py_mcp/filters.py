"""Keyword / message filters (from wxauto-mcp MessageListener idea)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional


@dataclass
class MessageFilter:
    keywords: list[str] = field(default_factory=list)
    exclude_keywords: list[str] = field(default_factory=list)
    reply_on_at: bool = False
    is_at_me: bool = False

    def match(self, content: str) -> bool:
        text = (content or "").strip()
        if not text:
            return False
        lower = text.lower()
        if self.exclude_keywords:
            for word in self.exclude_keywords:
                if word.lower() in lower:
                    return False
        if self.reply_on_at and not self.is_at_me:
            return False
        if not self.keywords:
            return True
        return any(word.lower() in lower for word in self.keywords)


def parse_keywords(raw: Optional[str]) -> list[str]:
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]
