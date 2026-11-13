import time

import pytest
from fastapi.testclient import TestClient

from lecture_scribe import config, formats

SEGS = [{"start": i * 10.0, "end": i * 10.0 + 9, "text": f"фраза {i}"} for i in range(36)]


def test_ts():
    assert formats.ts(3725) == "01:02:05"
    assert formats.ts(1.5, srt=True) == "00:00:01,500"


def test_merge_reduces_lines():
    merged = formats.merge(SEGS, 25)
    assert 0 < len(merged) < len(SEGS)
    assert merged[0]["start"] == 0 and "фраза 0" in merged[0]["text"]


def test_window():
    w = formats.window(SEGS, 100, 130)
    assert [s["text"] for s in w] == ["фраза 10", "фраза 11", "фраза 12"]


def test_chunks():
    ch = formats.chunks(SEGS, 2)
    assert len(ch) == 3 and ch[0]["start_ts"] == "00:00:00" and ch[1]["start_ts"] == "00:02:00"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "JOBS_DIR", tmp_path / "jobs")
    monkeypatch.setattr(config, "BACKEND", "fake")
    # skip real download: pretend ffmpeg/yt-dlp produced audio
    from lecture_scribe import server

    def fake_fetch(source, out_dir, referer=None, headers=None):
        out_dir.mkdir(parents=True, exist_ok=True)
        p = out_dir / "audio.wav"
        p.write_bytes(b"x")
        return p

    monkeypatch.setattr(server, "fetch_audio", fake_fetch)
    return TestClient(server.app)


def _wait(client, jid):
    for _ in range(100):
        m = client.get(f"/jobs/{jid}").json()
        if m["status"] in ("done", "error"):
            return m
        time.sleep(0.05)
    raise AssertionError("timeout")


def test_full_flow(client):
    r = client.post("/jobs", json={"source": "https://example.com/v.m3u8", "language": "ru"})
    jid = r.json()["id"]
    assert _wait(client, jid)["status"] == "done"

    txt = client.get(f"/jobs/{jid}/transcript").text
    assert txt.startswith("[00:00:00]")

    win = client.get(f"/jobs/{jid}/transcript", params={"start": 300, "end": 360}).text
    assert "фраза номер 30" in win and "номер 0." not in win

    assert "-->" in client.get(f"/jobs/{jid}/transcript", params={"format": "srt"}).text
    assert client.get(f"/jobs/{jid}/transcript", params={"format": "vtt"}).text.startswith("WEBVTT")

    ch = client.get(f"/jobs/{jid}/chunks", params={"minutes": 2}).json()
    assert len(ch["chunks"]) == 3

    # cache hit: same id, no re-run
    assert client.post("/jobs", json={"source": "https://example.com/v.m3u8", "language": "ru"}).json()["id"] == jid

    assert client.delete(f"/jobs/{jid}").status_code == 200
    assert client.get(f"/jobs/{jid}").status_code == 404


def test_not_ready_and_error(client, monkeypatch):
    from lecture_scribe import server

    def boom(*a, **k):
        raise RuntimeError("no media")

    monkeypatch.setattr(server, "fetch_audio", boom)
    jid = client.post("/jobs", json={"source": "bad"}).json()["id"]
    m = _wait(client, jid)
    assert m["status"] == "error" and "no media" in m["error"]
    assert client.get(f"/jobs/{jid}/transcript").status_code == 409
