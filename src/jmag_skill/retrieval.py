"""Bounded retrieval over lightweight catalogs and anchored JMAG Help metadata."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any, Iterable


def _tokens(text: str) -> set[str]:
    expanded = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    return set(re.findall(r"[a-z0-9_]+", expanded.lower()))


def _rank(entries: Iterable[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    wanted = _tokens(query)
    scored = []
    for entry in entries:
        primary = " ".join(str(entry.get(key, "")) for key in ("id", "symbol", "method"))
        secondary = " ".join(str(entry.get(key, "")) for key in ("module", "class"))
        summary = str(entry.get("summary", ""))
        score = (4 * len(wanted & _tokens(primary))
                 + 2 * len(wanted & _tokens(secondary))
                 + len(wanted & _tokens(summary)))
        if score:
            scored.append((score, entry))
    return [entry for _, entry in sorted(scored, key=lambda item: (-item[0], item[1].get("id", item[1].get("method", ""))))]


def search_catalog(entries: Iterable[dict[str, Any]], query: str, limit: int = 5) -> list[dict[str, Any]]:
    stable = (entry for entry in entries if entry.get("status") == "stable")
    return _rank(stable, query)[: min(limit, 5)]


class HelpIndex:
    def __init__(self, index_path: Path | str, help_root: Path | str):
        self.index_path = Path(index_path)
        self.help_root = Path(help_root).resolve()

    def entries(self) -> list[dict[str, Any]]:
        if not self.index_path.exists():
            return []
        return [json.loads(line) for line in self.index_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def search(self, query: str, limit: int = 3) -> list[dict[str, Any]]:
        return _rank(self.entries(), query)[: min(limit, 3)]

    def extract(self, hits: Iterable[dict[str, Any]], max_topics: int = 3) -> list[dict[str, Any]]:
        sections = []
        for hit in list(hits)[: min(max_topics, 3)]:
            source = (self.help_root / hit["source"]).resolve()
            if self.help_root not in source.parents or not source.is_file():
                raise ValueError(f"Help source escapes configured root: {source}")
            raw = source.read_text(encoding="utf-8", errors="ignore")
            anchor = re.escape(str(hit["anchor"]))
            locations = [match.start() for pattern in (rf'id=["\']{anchor}["\']', rf'href=["\']#{anchor}["\']') for match in re.finditer(pattern, raw, re.IGNORECASE)]
            if not locations:
                excerpt = raw[:3500]
            else:
                position = max(locations)
                excerpt = raw[max(0, position - 200): position + 3500]
            text = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", excerpt))).strip()
            sections.append({**hit, "text": text[:4000]})
        return sections
