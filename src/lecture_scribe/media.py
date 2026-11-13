"""Get audio out of a URL (page, HLS/MP4 stream) or a local file."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from . import config


class MediaError(RuntimeError):
    pass


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout)[-1500:]
        raise MediaError(f"{cmd[0]} failed (exit {proc.returncode}):\n{tail}")


def fetch_audio(
    source: str,
    out_dir: Path,
    referer: str | None = None,
    headers: dict[str, str] | None = None,
) -> Path:
    """Return path to a 16 kHz mono wav in out_dir.

    `source` may be a local path, a direct media URL (.m3u8/.mp4), or any page
    yt-dlp understands (YouTube, Vimeo, many LMS players...).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    wav = out_dir / "audio.wav"
    if wav.exists() and wav.stat().st_size > 0:
        return wav

    if not shutil.which("ffmpeg"):
        raise MediaError("ffmpeg not found in PATH (brew install ffmpeg / apt install ffmpeg)")

    local = Path(source).expanduser()
    if local.exists():
        raw = local
    else:
        if not shutil.which("yt-dlp"):
            raise MediaError("yt-dlp not found in PATH (pip install yt-dlp)")
        cmd = [
            "yt-dlp",
            "--no-playlist",
            "-f", "bestaudio/best",
            "-o", str(out_dir / "raw.%(ext)s"),
        ]
        if referer:
            cmd += ["--referer", referer]
        for k, v in (headers or {}).items():
            cmd += ["--add-header", f"{k}:{v}"]
        if config.COOKIES_FROM_BROWSER:
            cmd += ["--cookies-from-browser", config.COOKIES_FROM_BROWSER]
        elif config.COOKIES_FILE:
            cmd += ["--cookies", config.COOKIES_FILE]
        cmd.append(source)
        _run(cmd)
        candidates = sorted(out_dir.glob("raw.*"))
        if not candidates:
            raise MediaError("yt-dlp finished but produced no file")
        raw = candidates[0]

    _run(["ffmpeg", "-y", "-i", str(raw), "-vn", "-ac", "1", "-ar", "16000", str(wav)])
    if raw.parent == out_dir:
        raw.unlink(missing_ok=True)  # keep only the small wav
    return wav
