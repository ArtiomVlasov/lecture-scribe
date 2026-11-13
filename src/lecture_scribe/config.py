"""Runtime configuration, all overridable through environment variables."""
from __future__ import annotations

import os
from pathlib import Path

HOST = os.environ.get("LSCRIBE_HOST", "127.0.0.1")
PORT = int(os.environ.get("LSCRIBE_PORT", "8765"))
SERVER_URL = os.environ.get("LSCRIBE_URL", f"http://{HOST}:{PORT}")

DATA_DIR = Path(os.environ.get("LSCRIBE_DATA", Path.home() / ".lecture-scribe")).expanduser()
JOBS_DIR = DATA_DIR / "jobs"

# tiny/base/small/medium/large-v3 ; "medium" is a good default for Russian.
MODEL = os.environ.get("LSCRIBE_MODEL", "medium")
DEVICE = os.environ.get("LSCRIBE_DEVICE", "auto")  # auto | cpu | cuda
COMPUTE_TYPE = os.environ.get("LSCRIBE_COMPUTE_TYPE", "int8")

# Auth for sources behind a login (Open edX etc.). Pick one:
#   LSCRIBE_COOKIES_FROM_BROWSER=chrome   (yt-dlp reads the browser cookie jar)
#   LSCRIBE_COOKIES_FILE=/path/cookies.txt (Netscape format)
COOKIES_FROM_BROWSER = os.environ.get("LSCRIBE_COOKIES_FROM_BROWSER") or None
COOKIES_FILE = os.environ.get("LSCRIBE_COOKIES_FILE") or None

# Test hook: "fake" skips Whisper and returns canned segments.
BACKEND = os.environ.get("LSCRIBE_BACKEND", "whisper")
