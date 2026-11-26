"""YAML frontmatter parser and Markdown relative link extractor (stdlib only)."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import unquote

INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
FENCE_OPEN_RE = re.compile(r"^(`{3,}|~{3,})")


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _consume_block_scalar(lines: list[str], start: int, indicator: str) -> tuple[str, int]:
    block: list[str] = []
    idx = start
    min_indent: int | None = None
    while idx < len(lines):
        raw = lines[idx]
        if not raw.strip():
            block.append("")
            idx += 1
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if indent == 0:
            break
        if min_indent is None or indent < min_indent:
            min_indent = indent
        block.append(raw)
        idx += 1

    cut = min_indent or 0
    dedented = [line[cut:] if line else "" for line in block]
    while dedented and dedented[-1] == "":
        dedented.pop()

    if indicator.startswith(">"):
        text = " ".join(part.strip() for part in dedented if part.strip())
    else:
        text = "\n".join(dedented)
    return text.strip(), idx


def _consume_list(lines: list[str], start: int) -> tuple[list[str], int]:
    items: list[str] = []
    idx = start
    while idx < len(lines):
        stripped = lines[idx].strip()
        if not stripped:
            idx += 1
            continue
        if not stripped.startswith("- "):
            break
        items.append(_strip_quotes(stripped[2:].strip()))
        idx += 1
    return items, idx


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter (single-line, quoted, block scalars |/>, lists) and body."""
    normalized = text.replace("\r\n", "\n")
    raw_lines = normalized.splitlines(keepends=True)
    if not raw_lines or raw_lines[0].rstrip() != "---":
        raise ValueError("missing opening YAML frontmatter '---'")

    close_idx: int | None = None
    for idx in range(1, len(raw_lines)):
        if raw_lines[idx].rstrip() == "---":
            close_idx = idx
            break
    if close_idx is None:
        raise ValueError("missing closing YAML frontmatter '---'")

    meta_lines = [line.rstrip("\n") for line in raw_lines[1:close_idx]]
    raw_body = "".join(raw_lines[close_idx + 1 :])

    meta: dict[str, Any] = {}
    idx = 0
    while idx < len(meta_lines):
        line = meta_lines[idx]
        if not line.strip() or line.lstrip().startswith("#"):
            idx += 1
            continue
        if ":" not in line or line.startswith(" "):
            idx += 1
            continue
        key, raw_val = line.split(":", 1)
        key = key.strip()
        val = raw_val.strip()
        if val in {"|", "|-", "|+", ">", ">-", ">+"}:
            meta[key], idx = _consume_block_scalar(meta_lines, idx + 1, val)
        elif val == "":
            meta[key], idx = _consume_list(meta_lines, idx + 1)
        else:
            meta[key] = _strip_quotes(val)
            idx += 1

    body = raw_body.lstrip("\n")
    return meta, body


def extract_relative_links(markdown_text: str) -> list[str]:
    """Extract relative markdown link targets while respecting nested fenced/inline code."""
    links: list[str] = []
    fence_char = ""
    fence_len = 0

    for line in markdown_text.splitlines():
        stripped = line.lstrip()
        if not fence_char:
            open_match = FENCE_OPEN_RE.match(stripped)
            if open_match:
                token = open_match.group(1)
                fence_char = token[0]
                fence_len = len(token)
                continue
        else:
            close_re = rf"^{re.escape(fence_char)}{{{fence_len},}}\s*$"
            if re.match(close_re, stripped):
                fence_char = ""
                fence_len = 0
            continue

        cleaned = INLINE_CODE_RE.sub("", line)
        for match in MD_LINK_RE.finditer(cleaned):
            target = match.group(1).strip()
            if not target:
                continue
            target = target.split()[0].strip("<>")
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target = target.split("#", 1)[0]
            if target:
                links.append(unquote(target))
    return links
