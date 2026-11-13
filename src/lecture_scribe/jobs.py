"""Transcription jobs: download audio, run Whisper in one background worker, cache by source."""
from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from . import store
from .media import fetch_audio
from .transcribe import transcribe

_pool = ThreadPoolExecutor(max_workers=1)  # Whisper is heavy: one job at a time
_lock = threading.Lock()


@dataclass
class JobRequest:
    source: str  # page URL, player URL, direct .m3u8/.mp4 URL, or local file path
    language: str | None = None  # "ru", "en"... None = auto-detect
    model: str | None = None
    referer: str | None = None
    headers: dict[str, str] | None = None
    title: str | None = None
    force: bool = False  # re-run even if cached


def _run(jid: str, req: JobRequest) -> None:
    try:
        store.write_meta(jid, status="downloading", progress=0.0)
        wav = fetch_audio(req.source, store.job_dir(jid), req.referer, req.headers)
        store.write_meta(jid, status="transcribing", progress=0.0)
        result = transcribe(
            wav,
            language=req.language,
            model=req.model,
            on_progress=lambda p: store.write_meta(jid, progress=round(p, 3)),
        )
        store.save_transcript(jid, result)
        store.write_meta(
            jid,
            status="done",
            progress=1.0,
            language=result["language"],
            duration=result["duration"],
            model=result["model"],
            error=None,
        )
    except Exception as e:  # noqa: BLE001 - surfaced to the agent via job status
        store.write_meta(jid, status="error", error=str(e))


def create_job(req: JobRequest) -> dict:
    """Queue a job, or return the cached/running one for the same source."""
    jid = store.job_id(req.source, req.language, req.model)
    with _lock:
        meta = store.read_meta(jid)
        if meta and not req.force and meta["status"] in ("queued", "downloading", "transcribing", "done"):
            return meta
        if req.force:
            store.delete(jid)
        meta = store.write_meta(
            jid,
            status="queued",
            progress=0.0,
            source=req.source,
            title=req.title,
            language=req.language,
            error=None,
        )
        _pool.submit(_run, jid, req)
    return meta
