"""Whisper backend (faster-whisper) with a fake backend for tests."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from . import config

ProgressCb = Callable[[float], None]  # fraction 0..1

_models: dict[str, object] = {}


def _load(model_name: str):
    if model_name not in _models:
        from faster_whisper import WhisperModel

        _models[model_name] = WhisperModel(
            model_name, device=config.DEVICE, compute_type=config.COMPUTE_TYPE
        )
    return _models[model_name]


def transcribe(
    wav: Path,
    language: str | None = None,
    model: str | None = None,
    on_progress: ProgressCb | None = None,
) -> dict:
    """Returns {"language", "duration", "model", "segments": [{start,end,text}]}."""
    if config.BACKEND == "fake":
        segs = [
            {"start": float(i * 10), "end": float(i * 10 + 9), "text": f"Тестовая фраза номер {i}."}
            for i in range(36)
        ]
        if on_progress:
            on_progress(1.0)
        return {"language": language or "ru", "duration": 360.0, "model": "fake", "segments": segs}

    name = model or config.MODEL
    wm = _load(name)
    it, info = wm.transcribe(
        str(wav),
        language=language,
        vad_filter=True,
        beam_size=5,
        condition_on_previous_text=False,  # avoids hallucination loops on long lectures
    )
    segments = []
    for s in it:
        segments.append({"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()})
        if on_progress and info.duration:
            on_progress(min(1.0, s.end / info.duration))
    return {
        "language": info.language,
        "duration": info.duration,
        "model": name,
        "segments": segments,
    }
