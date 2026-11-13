---
name: lecture-notes
description: Turn a video on a web page (LMS player, lecture, course, recording) with no subtitles into a timestamped transcript via the lecture-scribe MCP tools, then write notes, chapters or answers and remember them. Use when the user shares a lecture/video link and asks for a summary, конспект, chapters, главы, транскрипция, or "what is said at minute N".
---

# lecture-notes

Requires the MCP server `lecture-scribe` (tools `transcribe_video`, `job_status`, `get_transcript`, `get_chunks`, `list_jobs`, `save_notes`, `read_index`, `read_note`). It runs on the user's computer with Whisper inside. You never transcribe audio yourself. If the tools are missing, tell the user to register the server (see the project README) and stop.

## Workflow

1. **`read_index`** — is this lecture already covered? If yes, answer from `read_note` and only fetch `get_transcript(job_id, start_seconds, end_seconds)` for details.
2. **Find the media URL.**
   - Try the page URL itself first (works for YouTube/Vimeo/many players).
   - With browser tools on the lecture page, list embedded players: `[...document.querySelectorAll('iframe')].map(f => f.src)`. For `https://player.vimeo.com/video/<ID>` use that URL. For `<video>`: `[...document.querySelectorAll('video, video source')].map(e => e.currentSrc || e.src)`. Open edX video block: `JSON.parse(document.querySelector('.video').dataset.metadata).sources`. Otherwise read network requests and filter for `m3u8`, `mpd`, `mp4` (take the master `.m3u8`).
   - Browser tools hide query strings. If yt-dlp asks for a hash (`?h=…`), ask the user to paste the full iframe `src`.
3. **`transcribe_video(source, referer=<site origin, e.g. https://mooc.lektorium.tv/>, language="ru", title=<lecture title>)`.** If the status is not `done`, call `job_status(job_id)` repeatedly (each call waits up to 40 s; the first run also downloads the model, a lecture takes minutes). On `error`, read the message: usually a missing referer, an expired signed URL (re-grab it and use `force=true`) or missing ffmpeg/yt-dlp. Do not ask for or handle the user's passwords or cookies.
4. **Read the text.** Short video (< ~40 min): `get_transcript(job_id)`. Long video: `get_chunks(job_id, 10)`, write a mini-summary per chunk, then merge. Never paste the whole transcript back to the user.
5. **Write what was asked**, in the user's language:
   - **Конспект (default):** one-paragraph overview (what / for whom / main thesis); sections by topic with a timestamp in the heading (`### Рынок и сегментация [00:12:40]`) and bullets with definitions, numbers, examples, names; "Термины" and "Что проверить/сделать" only if the lecture really contains them.
   - **Главы:** `HH:MM:SS — title`, 5–15 chapters at real topic changes. For one chapter in detail, fetch that time window and expand.
   - **Вопрос по месту:** fetch the window around the timestamp, answer, cite `[HH:MM:SS]`.
6. **`save_notes(title, content, gist, job_id, source)`** — content is the markdown notes, gist is one sentence on what the lecture is about. This is the memory: later sessions find it through `read_index`. Saving the same title replaces the note.

If the user wants slides or formulas on screen checked, use your native video/screenshot ability for those moments only; the transcript is the source for what was said.

## Rules

- Whisper errs on names, terms and numbers: when a term looks odd, write «в транскрипте: «…»» instead of silently fixing it.
- Never invent content for gaps; if a chunk is empty or garbled, say so.
- Keep timestamps in the notes so the user can jump back to the video.
- Never store credentials, cookies or signed URLs in notes.
- Several lectures: process one at a time (the server queues them anyway), save notes for each, then compare via `read_index` / `read_note`.
