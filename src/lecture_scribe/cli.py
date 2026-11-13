"""lecture-scribe CLI: `serve` starts the service, everything else is a thin client."""
from __future__ import annotations

import argparse
import json
import sys
import time

import httpx

from . import config


def _client() -> httpx.Client:
    return httpx.Client(base_url=config.SERVER_URL, timeout=60)


def _die(msg: str, code: int = 1):
    print(msg, file=sys.stderr)
    sys.exit(code)


def _call(method: str, path: str, **kw) -> httpx.Response:
    try:
        with _client() as c:
            r = c.request(method, path, **kw)
    except httpx.ConnectError:
        _die(
            f"Service not reachable at {config.SERVER_URL}. Start it with:  lecture-scribe serve",
            2,
        )
    if r.status_code >= 400:
        try:
            detail = r.json().get("detail", r.text)
        except Exception:  # noqa: BLE001
            detail = r.text
        _die(f"HTTP {r.status_code}: {detail}", 3)
    return r


def cmd_serve(a):
    import uvicorn

    uvicorn.run("lecture_scribe.server:app", host=a.host, port=a.port, log_level="info")


def cmd_submit(a):
    headers = dict(h.split(":", 1) for h in (a.header or []))
    body = {
        "source": a.source,
        "language": a.language,
        "model": a.model,
        "referer": a.referer,
        "headers": headers or None,
        "title": a.title,
        "force": a.force,
    }
    meta = _call("POST", "/jobs", json=body).json()
    if not a.wait:
        print(json.dumps(meta, ensure_ascii=False))
        return
    jid = meta["id"]
    last = None
    while True:
        meta = _call("GET", f"/jobs/{jid}").json()
        line = f"{meta['status']} {meta.get('progress', 0):.0%}"
        if line != last:
            print(line, file=sys.stderr)
            last = line
        if meta["status"] == "done":
            print(jid)
            return
        if meta["status"] == "error":
            _die(f"job {jid} failed: {meta.get('error')}")
        time.sleep(a.interval)


def cmd_status(a):
    path = f"/jobs/{a.id}" if a.id else "/jobs"
    print(json.dumps(_call("GET", path).json(), ensure_ascii=False, indent=2))


def cmd_get(a):
    params = {"format": a.format, "start": a.start}
    if a.end is not None:
        params["end"] = a.end
    r = _call("GET", f"/jobs/{a.id}/transcript", params=params)
    print(json.dumps(r.json(), ensure_ascii=False) if a.format == "json" else r.text)


def cmd_chunks(a):
    r = _call("GET", f"/jobs/{a.id}/chunks", params={"minutes": a.minutes})
    print(json.dumps(r.json(), ensure_ascii=False, indent=2))


def cmd_rm(a):
    print(json.dumps(_call("DELETE", f"/jobs/{a.id}").json()))


def main(argv=None):
    p = argparse.ArgumentParser(prog="lecture-scribe", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("serve", help="start the local transcription service")
    s.add_argument("--host", default=config.HOST)
    s.add_argument("--port", type=int, default=config.PORT)
    s.set_defaults(fn=cmd_serve)

    s = sub.add_parser("submit", help="queue a video for transcription")
    s.add_argument("source", help="page URL, direct .m3u8/.mp4 URL, or local file")
    s.add_argument("--language", help="ru, en... (default: auto)")
    s.add_argument("--model", help="override model for this job")
    s.add_argument("--referer", help="Referer header (often needed for LMS CDNs)")
    s.add_argument("--header", action="append", help="extra header 'Name: value' (repeatable)")
    s.add_argument("--title")
    s.add_argument("--force", action="store_true", help="ignore cache")
    s.add_argument("--wait", action="store_true", help="block until done, print job id")
    s.add_argument("--interval", type=float, default=5.0)
    s.set_defaults(fn=cmd_submit)

    s = sub.add_parser("status", help="job status (or list all jobs)")
    s.add_argument("id", nargs="?")
    s.set_defaults(fn=cmd_status)

    s = sub.add_parser("get", help="print transcript (optionally a time window in seconds)")
    s.add_argument("id")
    s.add_argument("--format", choices=["txt", "json", "srt", "vtt"], default="txt")
    s.add_argument("--start", type=float, default=0.0)
    s.add_argument("--end", type=float)
    s.set_defaults(fn=cmd_get)

    s = sub.add_parser("chunks", help="transcript split into N-minute windows (JSON)")
    s.add_argument("id")
    s.add_argument("--minutes", type=float, default=10.0)
    s.set_defaults(fn=cmd_chunks)

    s = sub.add_parser("rm", help="delete a job and its files")
    s.add_argument("id")
    s.set_defaults(fn=cmd_rm)

    a = p.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
