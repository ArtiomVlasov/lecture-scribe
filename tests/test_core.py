import pytest

from lecture_scribe import config, formats

SEGS = [{"start": i * 10.0, "end": i * 10.0 + 9, "text": f"фраза {i}"} for i in range(36)]


def test_ts():
    assert formats.ts(3725) == "01:02:05"


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
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "JOBS_DIR", tmp_path / "jobs")
    monkeypatch.setattr(config, "NOTES_DIR", tmp_path / "notes")
    monkeypatch.setattr(config, "BACKEND", "fake")
    from lecture_scribe import jobs

    def fake_fetch(source, out_dir, referer=None, headers=None):
        out_dir.mkdir(parents=True, exist_ok=True)
        p = out_dir / "audio.wav"
        p.write_bytes(b"x")
        return p

    monkeypatch.setattr(jobs, "fetch_audio", fake_fetch)
    return jobs


def test_job_error_is_reported(env, monkeypatch):
    from lecture_scribe import mcp_server as m

    def boom(*a, **k):
        raise RuntimeError("no media")

    monkeypatch.setattr(env, "fetch_audio", boom)
    st = m.transcribe_video("bad", wait_seconds=10)
    assert st["status"] == "error" and "no media" in st["error"]
    with pytest.raises(ValueError):
        m.get_transcript(st["id"])


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


def test_unknown_job():
    from lecture_scribe import mcp_server as m

    with pytest.raises(ValueError):
        m.get_transcript("nope")


def test_slug_and_traversal(env):
    from lecture_scribe import notes

    assert notes.slugify("  A/B: C!! ") == "a-b-c"
    with pytest.raises(FileNotFoundError):
        notes.read_note("../../etc/passwd")
