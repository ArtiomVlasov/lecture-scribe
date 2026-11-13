---
name: lecture-notes
description: Turn a video on a web page (LMS player, lecture, course, recording) into a timestamped transcript via a local transcription service, then write notes, chapters or answers from it. Use when the user shares a video/lecture link that has no subtitles and asks for a summary, конспект, chapters, главы, транскрипция or "what is said at minute N".
---

# lecture-notes

Videos with no subtitles are handled by a **local service** (`lecture-scribe`, Whisper inside) that returns a timestamped transcript. You never transcribe audio yourself: you find the media URL, ask the service, then read text.

## 0. Check the service

```bash
curl -s http://127.0.0.1:8765/health
```

If it is not running, ask the user to start it in a terminal (`lecture-scribe serve`) — it needs their machine's CPU/GPU and cookies. Do not try to install Whisper in the sandbox. If you are working in the user's own shell, you may start it in the background yourself.

## 1. Find the media URL

Prefer, in this order:

1. **Page URL itself** — works for YouTube/Vimeo and many players (yt-dlp handles it). Try it first.
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

## Rules

- Whisper makes mistakes on names, terms and numbers. When a term looks odd, say "в транскрипте: «…»" instead of silently "fixing" it, or check it against slides.
- Never invent content for gaps; if a chunk is empty/garbled, say so.
- Keep timestamps in the notes so the user can jump back to the video.
- Transcripts live in `~/.lecture-scribe/jobs/<id>/` on the user's machine; `lecture-scribe rm <id>` deletes one.
