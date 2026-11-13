---
name: lecture-notes
description: Turn a video on a web page (LMS player, lecture, course, recording) into a timestamped transcript via a local transcription service, then write notes, chapters or answers from it. Use when the user shares a video/lecture link that has no subtitles and asks for a summary, конспект, chapters, главы, транскрипция or "what is said at minute N".
---

# lecture-notes

Videos with no subtitles are handled by a **local service** (`lecture-scribe`, Whisper inside) that returns a timestamped transcript. You never transcribe audio yourself: you find the media URL, ask the service, then read text.

## MCP mode (preferred, fully autonomous)

If tools named `transcribe_video`, `job_status`, `get_transcript`, `get_chunks`, `save_notes`, `read_index`, `read_note` are available (MCP server `lecture-scribe`, running on the user's machine), use them and ignore the CLI/HTTP parts below; no files need to be moved by hand.

1. `read_index` — is this lecture already covered? If yes, answer from `read_note` and stop.
2. Find the media URL (step 1 below), then `transcribe_video(source, referer=<site origin>, language="ru", title=...)`. If the status is not `done`, call `job_status(job_id)` repeatedly (it waits up to 40 s per call; a lecture takes minutes).
3. `get_transcript(job_id)` for short videos, `get_chunks(job_id, 10)` for long ones; `get_transcript(job_id, start_seconds, end_seconds)` for a specific moment.
4. Write the notes (step 4 below), then `save_notes(title, content, gist, job_id, source)` — this is the memory; later sessions find it via `read_index`.

## 0. Check the service (CLI/HTTP mode, when no MCP tools exist)

```bash
curl -s http://127.0.0.1:8765/health
```

If it is not running, ask the user to start it in a terminal (`lecture-scribe serve`) — it needs their machine's CPU/GPU and cookies. Do not try to install Whisper in the sandbox. If you are working in the user's own shell, you may start it in the background yourself.

**No access to localhost** (cloud/sandboxed agent, the service runs on the user's Mac): use the file handoff. Give the user the two commands (`lecture-scribe submit ... --wait`, then `lecture-scribe get <id> > <connected-folder>/transcript.txt`), then read the file and continue from step 4. Everything else is the same.

## 1. Find the media URL

Prefer, in this order:

1. **Page URL itself** — works for YouTube/Vimeo and many players (yt-dlp handles it). Try it first.
   Many LMS pages (Open edX / Лекториум) embed a **Vimeo or YouTube iframe**: look at `[...document.querySelectorAll('iframe')].map(f => f.src)`; for `https://player.vimeo.com/video/<ID>` submit that URL with `--referer "<site origin>/"`. If yt-dlp asks for a hash, the iframe `src` carries `?h=…`: browser tools hide query strings, so ask the user to paste the full iframe src.
2. **Browser tools** (Claude in Chrome / built-in browser), with the lecture page open and the video started:
   - JS in the page (also try inside the player iframe):
     ```js
     [...document.querySelectorAll('video, video source')].map(e => e.currentSrc || e.src).filter(Boolean)
     ```
   - Open edX players keep sources in metadata:
     ```js
     JSON.parse(document.querySelector('.video').dataset.metadata).sources
     ```
   - Otherwise read network requests and filter for `m3u8`, `mpd`, `mp4`. Take the master `.m3u8` (not a single `.ts` segment).
3. Ask the user for the link or a downloaded file if none of the above works (DRM, login wall).

Remember the page URL: pass it as `--referer`, many LMS CDNs reject requests without it.

## 2. Submit and wait

```bash
lecture-scribe submit "<media-or-page-url>" --referer "<page-url>" --language ru --title "<lecture title>" --wait
```

- Prints the **job id** on success. Same URL again = instant cache hit.
- A 1-hour lecture takes minutes on CPU (`medium`), faster on GPU. `--wait` prints progress to stderr; for very long runs omit `--wait` and poll `lecture-scribe status <id>`.
- Login-protected video: the user sets `LSCRIBE_COOKIES_FROM_BROWSER=chrome` (or `LSCRIBE_COOKIES_FILE`) when starting the service. Never ask for or handle their password/cookies yourself.
- On `error`, read `status <id>` → `error`: usually a missing Referer, expired signed URL (re-grab the URL from the page and use `--force`) or no ffmpeg.

## 3. Read the transcript

```bash
lecture-scribe get <id>                          # whole thing, "[HH:MM:SS] text" lines
lecture-scribe get <id> --start 600 --end 1200   # only minutes 10–20 (seconds)
lecture-scribe chunks <id> --minutes 10          # JSON windows for long videos
```

Short video (< ~40 min): read it whole. Long video: read `chunks` one by one, write a mini-summary per chunk, then merge. Don't paste the whole transcript back to the user.

## 4. Produce what the user asked for

**Конспект (default)** — in the user's language:

- one-paragraph overview (what / who for / main thesis);
- sections by topic, each with a heading carrying a timestamp, e.g. `### Рынок и сегментация [00:12:40]`, bullets with definitions, numbers, examples, names;
- "Термины" and "Что проверить/сделать" lists only if the lecture actually contains them.

**Главы (chapters)** — list `HH:MM:SS — title`, 5–15 chapters, boundaries at real topic changes. If the user wants one chapter in detail: `get --start/--end` for that range and expand.

**Вопросы по месту** — fetch the window around the timestamp, answer, cite `[HH:MM:SS]`.

If the user asks you to *watch* the video too (slides, formulas on screen), use your native video/screenshot ability for those moments only; the transcript is the source for what was said.

## 5. Remember it (notes memory)

After writing a конспект, save it so future sessions know what the lecture was about.

- Notes dir: `$LSCRIBE_NOTES`, else `~/lecture-notes/` (or `./notes/` inside a connected folder when you cannot write to home). Create it if missing.
- File `<slug>.md` with frontmatter `title, source (page url), media (url used), job_id, duration, language, model, date`, then: one-paragraph summary, chapters with timestamps, key terms, open questions / things to verify.
- Update `INDEX.md`: one line per lecture — `- [<title>](<slug>.md) — <one-sentence gist> (job <id>, <duration>)`. Replace the line if the lecture is already there.
- **Before** starting work on a lecture link: read `INDEX.md`. If the lecture is already there, answer from its note and only call `lecture-scribe get <id> --start/--end` for details. When the user asks about "the lecture on X" or compares lectures, search `INDEX.md` and the notes first.
- Keep notes factual and in the user's language; never store credentials, cookies or signed URLs.

## Rules

- Whisper makes mistakes on names, terms and numbers. When a term looks odd, say "в транскрипте: «…»" instead of silently "fixing" it, or check it against slides.
- Never invent content for gaps; if a chunk is empty/garbled, say so.
- Keep timestamps in the notes so the user can jump back to the video.
- Transcripts live in `~/.lecture-scribe/jobs/<id>/` on the user's machine; `lecture-scribe rm <id>` deletes one.
