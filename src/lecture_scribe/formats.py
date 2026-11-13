"""Turning raw Whisper segments into agent-friendly text."""
from __future__ import annotations

from typing import Iterable

Segment = dict  # {"start": float, "end": float, "text": str}


def ts(seconds: float, vtt: bool = False, srt: bool = False) -> str:
    seconds = max(0.0, float(seconds))
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    if srt or vtt:
        ms = int(round((seconds - int(seconds)) * 1000))
        sep = "," if srt else "."
        return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"
    return f"{h:02d}:{m:02d}:{s:02d}"


def merge(segments: Iterable[Segment], target_seconds: float = 25.0) -> list[Segment]:
    """Glue short Whisper segments into ~target-second lines.

    Fewer lines = fewer tokens for the agent, while keeping a timestamp every
    ~25 s so it can cite moments of the video.
    """
    out: list[Segment] = []
    cur: Segment | None = None
    for seg in segments:
        text = seg["text"].strip()
        if not text:
            continue
        if cur is None:
            cur = {"start": seg["start"], "end": seg["end"], "text": text}
        elif seg["end"] - cur["start"] <= target_seconds:
            cur["end"] = seg["end"]
            cur["text"] += " " + text
        else:
            out.append(cur)
            cur = {"start": seg["start"], "end": seg["end"], "text": text}
    if cur:
        out.append(cur)
    return out


def to_txt(segments: Iterable[Segment], target_seconds: float = 25.0) -> str:
    return "\n".join(f"[{ts(s['start'])}] {s['text']}" for s in merge(segments, target_seconds))


def window(segments: Iterable[Segment], start: float = 0.0, end: float | None = None) -> list[Segment]:
    """Segments overlapping [start, end)."""
    return [s for s in segments if s["end"] > start and (end is None or s["start"] < end)]


def chunks(segments: list[Segment], minutes: float = 10.0) -> list[dict]:
    """Split the transcript into fixed-length windows for map-reduce summarising."""
    if not segments:
        return []
    size = minutes * 60
    total = segments[-1]["end"]
    out = []
    n = int(total // size) + 1
    for i in range(n):
        lo, hi = i * size, (i + 1) * size
        part = [s for s in segments if lo <= s["start"] < hi]
        if not part:
            continue
        out.append(
            {
                "index": len(out),
                "start": lo,
                "end": min(hi, total),
                "start_ts": ts(lo),
                "end_ts": ts(min(hi, total)),
                "text": to_txt(part),
            }
        )
    return out
