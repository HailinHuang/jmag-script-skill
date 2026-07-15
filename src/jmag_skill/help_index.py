"""Build a compact method index from local Doxygen-style JMAG Help HTML."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path


ITEM = re.compile(r'<tr class="memitem:(?P<anchor>[^"]+)">(?P<body>.*?)</tr>', re.IGNORECASE | re.DOTALL)
LINK = re.compile(r'<a class="el"[^>]*>(?P<label>[^<]+)</a>', re.IGNORECASE)


def _plain(value: str) -> str:
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", value))).strip()


def build_help_index(help_root: Path | str, output: Path | str) -> int:
    root, target = Path(help_root), Path(output)
    rows: list[dict[str, str]] = []
    for source in root.glob("*/class*.html"):
        if source.name.endswith("-members.html"):
            continue
        module = source.parent.name
        class_name = source.stem.removeprefix("class")
        raw = source.read_text(encoding="utf-8", errors="ignore")
        seen: set[tuple[str, str]] = set()
        for match in ITEM.finditer(raw):
            anchor = match.group("anchor")
            labels = [_plain(link.group("label")) for link in LINK.finditer(match.group("body"))]
            if not labels:
                continue
            method = labels[-1]
            key = (method, anchor)
            if not method or method in {"More...", "Public Member Functions"} or key in seen:
                continue
            seen.add(key)
            description = re.search(
                rf'<tr class="memdesc:{re.escape(anchor)}">.*?<td class="mdescRight">(?P<text>.*?)</td></tr>',
                raw[match.end():], re.IGNORECASE | re.DOTALL,
            )
            summary = _plain(description.group("text")) if description else ""
            summary = summary.removesuffix("More...").strip()
            rows.append({
                "module": module, "class": class_name, "method": method,
                "summary": summary[:320],
                "source": source.relative_to(root).as_posix(), "anchor": anchor,
            })
    rows.sort(key=lambda row: (row["module"], row["class"], row["method"], row["anchor"]))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + ("\n" if rows else ""), encoding="utf-8")
    return len(rows)
