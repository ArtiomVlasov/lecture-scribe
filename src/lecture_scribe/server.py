"""FastAPI service. Runs on localhost; one background worker (Whisper is heavy)."""
from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from . import __version__, config, formats, store
from .media import fetch_audio
from .transcribe import transcribe

app = FastAPI(title="lecture-scribe", version=__version__)
_pool = ThreadPoolExecutor(max_workers=1)
_lock = threading.Lock()


class JobRequest(BaseModel):
    source: str  # page URL, direct .m3u8/.mp4 URL, or local file path
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
    except Exception as e:  # noqa: BLE001 - surfaced to the client
        store.write_meta(jid, status="error", error=str(e))


@app.get("/health")
def health():
    return {"ok": True, "version": __version__, "model": config.MODEL, "backend": config.BACKEND}


@app.post("/jobs")
def create_job(req: JobRequest):
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


@app.get("/jobs")
def list_jobs():
    return store.list_meta()


@app.get("/jobs/{jid}")
def get_job(jid: str):
    meta = store.read_meta(jid)
    if not meta:
        raise HTTPException(404, "no such job")
    return meta


def _ready(jid: str) -> dict:
    meta = store.read_meta(jid)
    if not meta:
        raise HTTPException(404, "no such job")
    if meta["status"] != "done":
        raise HTTPException(409, f"job is {meta['status']} ({meta.get('progress', 0):.0%}); poll /jobs/{jid}")
    data = store.load_transcript(jid)
    if not data:
        raise HTTPException(500, "transcript missing on disk")
    return data


@app.get("/jobs/{jid}/transcript")
def transcript(
    jid: str,
    format: str = Query("txt", pattern="^(txt|json|srt|vtt)$"),
    start: float = 0.0,
    end: float | None = None,
    line_seconds: float = 25.0,
):
    """Whole transcript, or a time window (seconds) when start/end are given."""
    data = _ready(jid)
    segs = formats.window(data["segments"], start, end)
    if format == "json":
        return {**data, "segments": segs}
    if format == "srt":
        return PlainTextResponse(formats.to_srt(segs))
    if format == "vtt":
        return PlainTextResponse(formats.to_vtt(segs), media_type="text/vtt")
    return PlainTextResponse(formats.to_txt(segs, line_seconds))


@app.get("/jobs/{jid}/chunks")
def chunks(jid: str, minutes: float = Query(10.0, gt=0.5, le=60)):
    """Fixed-length windows, for summarising long lectures piece by piece."""
    data = _ready(jid)
    return {"duration": data["duration"], "chunks": formats.chunks(data["segments"], minutes)}


@app.delete("/jobs/{jid}")
def delete_job(jid: str):
    if not store.delete(jid):
        raise HTTPException(404, "no such job")
    return {"deleted": jid}
