"""Agent notes memory: one markdown file per lecture + INDEX.md."""
from __future__ import annotations

import re
import time
from pathlib import Path

from . import config


def _dir() -> Path:
    d = config.NOTES_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def slugify(title: str) -> str:
    s = re.sub(r"[^\w]+", "-", title.lower(), flags=re.UNICODE).strip("-_")
    return s[:60] or "lecture"


def save(title: str, content: str, gist: str, job_id: str | None = None, source: str | None = None) -> dict:
    slug = slugify(title)
    d = _dir()
    front = ["---", f"title: {title}", f"date: {time.strftime('%Y-%m-%d')}"]
    if job_id:
        front.append(f"job_id: {job_id}")
    if source:
        front.append(f"source: {source}")
    front.append("---\n")
    (d / f"{slug}.md").write_text("\n".join(front) + "\n" + content.strip() + "\n", encoding="utf-8")

    idx = d / "INDEX.md"
    lines = idx.read_text(encoding="utf-8").splitlines() if idx.exists() else ["# Lecture notes index", ""]
    entry = f"- [{title}]({slug}.md) — {gist.strip()}" + (f" (job {job_id})" if job_id else "")
    marker = f"]({slug}.md)"
    for i, line in enumerate(lines):
        if marker in line:
            lines[i] = entry
            break
    else:
        lines.append(entry)
    idx.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"slug": slug, "path": str(d / f"{slug}.md"), "index": str(idx)}


def read_index() -> str:
    idx = _dir() / "INDEX.md"
    return idx.read_text(encoding="utf-8") if idx.exists() else "(no notes yet)"


def read_note(slug: str) -> str:
    p = _dir() / f"{Path(slug).stem if slug.endswith('.md') else Path(slug).name}.md"
    if not p.exists():
        raise FileNotFoundError(f"no note '{slug}'; see INDEX")
    return p.read_text(encoding="utf-8")
