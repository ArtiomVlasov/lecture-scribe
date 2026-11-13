import subprocess
import time

import pytest

from lecture_scribe import config, notes


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "JOBS_DIR", tmp_path / "jobs")
    monkeypatch.setattr(config, "NOTES_DIR", tmp_path / "notes")
    monkeypatch.setattr(config, "BACKEND", "fake")
    from lecture_scribe import server

    def fake_fetch(source, out_dir, referer=None, headers=None):
        out_dir.mkdir(parents=True, exist_ok=True)
        p = out_dir / "audio.wav"
        p.write_bytes(b"x")
        return p

    monkeypatch.setattr(server, "fetch_audio", fake_fetch)


def test_tools_flow(env):
    from lecture_scribe import mcp_server as m

    st = m.transcribe_video("https://player.vimeo.com/video/1", referer="https://x/", wait_seconds=10)
    assert st["status"] == "done"
    jid = st["id"]
    assert m.transcribe_video("https://player.vimeo.com/video/1", referer="https://x/", wait_seconds=5)["id"] == jid
    assert m.get_transcript(jid).startswith("[00:00:00]")
    assert "номер 30" in m.get_transcript(jid, 300, 360)
    assert len(m.get_chunks(jid, 2)) == 3
    assert m.list_jobs()[0]["id"] == jid

    r = m.save_notes("Лекция 1.1: Предприниматель и бизнес", "## Кратко\nтекст", "что такое предприниматель", jid, "https://p")
    assert r["slug"].startswith("лекция-1-1")
    m.save_notes("Лекция 1.1: Предприниматель и бизнес", "## Обновлено", "новая суть", jid)
    idx = m.read_index()
    assert idx.count("лекция-1-1") == 1 and "новая суть" in idx
    assert "Обновлено" in m.read_note(r["slug"])


def test_not_ready_error(env):
    from lecture_scribe import mcp_server as m

    with pytest.raises(ValueError):
        m.get_transcript("nope")


def test_slug_and_traversal(env):
    assert notes.slugify("  A/B: C!! ") == "a-b-c"
    with pytest.raises(FileNotFoundError):
        notes.read_note("../../etc/passwd")
