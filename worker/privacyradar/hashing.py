from __future__ import annotations

import hashlib


def normalize_markdown(text: str) -> str:
    lines = [line.rstrip() for line in text.replace("\r\n", "\n").split("\n")]
    collapsed: list[str] = []
    blank = False
    for line in lines:
        if not line.strip():
            if not blank:
                collapsed.append("")
            blank = True
            continue
        blank = False
        collapsed.append(" ".join(line.split()))
    return "\n".join(collapsed).strip() + "\n"


def doc_hash(markdown: str) -> str:
    return hashlib.sha256(normalize_markdown(markdown).encode("utf-8")).hexdigest()


def section_hashes(markdown: str) -> dict[str, str]:
    """Hash each heading-delimited section so we know which clause moved."""
    text = normalize_markdown(markdown)
    sections: dict[str, list[str]] = {}
    current = "_preamble"
    sections[current] = []
    for line in text.split("\n"):
        if line.startswith("#") or (len(line) > 12 and line.isupper()):
            current = line.lstrip("#").strip()[:120] or current
            sections.setdefault(current, [])
            continue
        sections[current].append(line)
    out: dict[str, str] = {}
    for name, lines in sections.items():
        body = "\n".join(lines).strip()
        if body:
            out[name] = hashlib.sha256(body.encode("utf-8")).hexdigest()
    return out


def changed_sections(old: dict[str, str], new: dict[str, str]) -> list[str]:
    names = set(old) | set(new)
    return sorted(name for name in names if old.get(name) != new.get(name))
