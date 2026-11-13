"""On-disk job store. Job id = hash of source, so re-asking is a cache hit."""
from __future__ import annotations

import hashlib
import json
import shutil
import time
from pathlib import Path

from . import config


def job_id(source: str, language: str | None, model: str | None) -> str:
    key = f"{source}|{language or ''}|{model or config.MODEL}"
    return hashlib.sha1(key.encode()).hexdigest()[:12]


def job_dir(jid: str) -> Path:
    return config.JOBS_DIR / jid


def read_meta(jid: str) -> dict | None:
    p = job_dir(jid) / "meta.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def write_meta(jid: str, **fields) -> dict:
    d = job_dir(jid)
    d.mkdir(parents=True, exist_ok=True)
    meta = read_meta(jid) or {"id": jid, "created": time.time()}
    meta.update(fields)
    meta["updated"] = time.time()
    tmp = d / "meta.json.tmp"
    tmp.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(d / "meta.json")
    return meta


def list_meta() -> list[dict]:
    if not config.JOBS_DIR.exists():
        return []
    out = []
    for d in config.JOBS_DIR.iterdir():
        m = read_meta(d.name)
        if m:
            out.append(m)
    return sorted(out, key=lambda m: m.get("created", 0), reverse=True)


def save_transcript(jid: str, data: dict) -> None:
    (job_dir(jid) / "transcript.json").write_text(
        json.dumps(data, ensure_ascii=False), encoding="utf-8"
    )


def load_transcript(jid: str) -> dict | None:
    p = job_dir(jid) / "transcript.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def delete(jid: str) -> bool:
    d = job_dir(jid)
    if d.exists():
        shutil.rmtree(d)
        return True
    return False
