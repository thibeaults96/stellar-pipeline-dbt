"""Lightweight SQL parsing helpers for objective checking (no sqlglot dependency)."""
from __future__ import annotations

import re


def extract_column_aliases(sql: str) -> list[str]:
    """Extract column aliases from SQL using regex (no AST parser needed)."""
    # Strip Jinja
    cleaned = re.sub(r"\{\{.*?\}\}", "placeholder", sql)
    cleaned = re.sub(r"\{%.*?%\}", "", cleaned)
    cleaned = re.sub(r"\{#.*?#\}", "", cleaned)
    # Strip comments
    cleaned = re.sub(r"--.*$", "", cleaned, flags=re.MULTILINE)

    aliases: list[str] = []
    # Match: expression AS alias_name
    for m in re.finditer(r"\bas\s+(\w+)", cleaned, re.IGNORECASE):
        alias = m.group(1).lower()
        # Skip SQL keywords that appear after AS in CTEs (e.g., "with source as (")
        if alias in ("select", "from", "where", "join", "on", "and", "or", "not",
                      "in", "is", "null", "case", "when", "then", "else", "end",
                      "group", "order", "having", "limit", "union", "all", "distinct"):
            continue
        aliases.append(alias)
    return aliases
