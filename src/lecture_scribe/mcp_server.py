"""MCP server (stdio): lets an agent transcribe videos and keep lecture notes by itself.

Runs on the user's machine, so it needs no HTTP service, no tunnels and no files
shuttled by hand. Register it once in Claude Desktop / Claude Code (see docs/AGENT.md).
"""
from __future__ import annotations

import time

from mcp.server.fastmcp import FastMCP

from . import formats, notes, store
from .server import JobRequest, create_job

mcp = FastMCP("lecture-scribe")


def _status(jid: str) -> dict:
    meta = store.read_meta(jid)
    if not meta:
        raise ValueError(f"no such job: {jid}")
    return {k: meta.get(k) for k in ("id", "status", "progress", "title", "language", "duration", "model", "error")}


def _wait(jid: str, seconds: float) -> dict:
    deadline = time.time() + max(0.0, seconds)
    while True:
        st = _status(jid)
        if st["status"] in ("done", "error") or time.time() >= deadline:
            return st
        time.sleep(1.0)


def _done_data(jid: str) -> dict:
    st = _status(jid)
    if st["status"] != "done":
        raise ValueError(f"job {jid} is {st['status']} ({(st['progress'] or 0):.0%}); call job_status and retry later")
    data = store.load_transcript(jid)
    if not data:
        raise ValueError("transcript missing on disk")
    return data


@mcp.tool()
def transcribe_video(
    source: str,
    referer: str | None = None,
    language: str | None = "ru",
    title: str | None = None,
    force: bool = False,
    wait_seconds: int = 40,
) -> dict:
    """Start transcribing a video (page URL, player.vimeo.com/video/<id>, .m3u8/.mp4 URL, or local file).

    Same source again returns the cached job instantly. Waits up to wait_seconds, then returns the
    job status; if status is not 'done', call job_status(job_id, wait_seconds=...) until it is.
    Pass referer = the lecture page origin (e.g. https://mooc.lektorium.tv/) for embedded players.
    """
    meta = create_job(JobRequest(source=source, referer=referer, language=language, title=title, force=force))
    return _wait(meta["id"], wait_seconds)


@mcp.tool()
def job_status(job_id: str, wait_seconds: int = 40) -> dict:
    """Status of a transcription job (queued/downloading/transcribing/done/error) with progress 0..1.
    Waits up to wait_seconds for it to finish."""
    return _wait(job_id, wait_seconds)


@mcp.tool()
def list_jobs() -> list[dict]:
    """All known transcription jobs, newest first."""
    return [_status(m["id"]) | {"source": m.get("source")} for m in store.list_meta()]


@mcp.tool()
def get_transcript(job_id: str, start_seconds: float = 0, end_seconds: float | None = None) -> str:
    """Transcript as '[HH:MM:SS] text' lines. Optional time window in seconds. For long videos
    (>40 min) prefer get_chunks and summarise piece by piece."""
    data = _done_data(job_id)
    return formats.to_txt(formats.window(data["segments"], start_seconds, end_seconds))


@mcp.tool()
def get_chunks(job_id: str, minutes: float = 10) -> list[dict]:
    """Transcript split into fixed N-minute windows: [{index,start_ts,end_ts,text}]."""
    return formats.chunks(_done_data(job_id)["segments"], minutes)


@mcp.tool()
def save_notes(title: str, content: str, gist: str, job_id: str | None = None, source: str | None = None) -> dict:
    """Save a lecture's notes (markdown: summary, chapters with timestamps, terms) to the notes memory
    and update INDEX.md. gist = one sentence about what the lecture is about. Saving the same title replaces it."""
    return notes.save(title, content, gist, job_id, source)


@mcp.tool()
def read_index() -> str:
    """INDEX.md of all saved lecture notes. Read it BEFORE working on a lecture: it may already be covered."""
    return notes.read_index()


@mcp.tool()
def read_note(slug: str) -> str:
    """Full saved notes for one lecture (slug as in INDEX.md links, without .md)."""
    return notes.read_note(slug)


def main() -> None:
    mcp.run()  # stdio


if __name__ == "__main__":
    main()
