# Как подключить агента

Лучший способ — **MCP-сервер**: он запускается на вашем компьютере, агент получает инструменты (расшифровать видео, прочитать текст, сохранить конспект) и работает сам, без HTTP-сервиса, туннелей и ручных файлов. Модель Whisper запускается внутри него.

## 1. Один раз: установка

```bash
cd ~/coding/lecture-scribe && source .venv/bin/activate
pip install -e .          # подтянет mcp, numpy
which lecture-scribe      # путь понадобится ниже: /Users/archi/coding/lecture-scribe/.venv/bin/lecture-scribe
```

## 2. Один раз: регистрация

**Claude Desktop / Cowork.** Откройте `~/Library/Application Support/Claude/claude_desktop_config.json` (или Settings → Developer → Edit Config) и добавьте:

```json
{
  "mcpServers": {
    "lecture-scribe": {
      "command": "/Users/archi/coding/lecture-scribe/.venv/bin/lecture-scribe",
      "args": ["mcp"],
      "env": { "LSCRIBE_MODEL": "medium", "LSCRIBE_NOTES": "/Users/archi/lecture-notes" }
    }
  }
}
```

Полностью перезапустите приложение. У агента появятся инструменты `transcribe_video`, `job_status`, `get_transcript`, `get_chunks`, `save_notes`, `read_index`, `read_note`, `list_jobs`.

**Claude Code.**

```bash
claude mcp add lecture-scribe -e LSCRIBE_MODEL=medium -- /Users/archi/coding/lecture-scribe/.venv/bin/lecture-scribe mcp
```

И скилл (необязательно, но он объясняет агенту порядок действий): `cp -r skill/lecture-notes ~/.claude/skills/`.

## 3. Использование

Пишете агенту: «Составь конспект лекции <ссылка на страницу курса>». Агент сам находит видео на странице, вызывает `transcribe_video`, ждёт, читает текст, пишет конспект и сохраняет его через `save_notes`.

Первая расшифровка долгая (скачивание модели и сама лекция), следующие обращения к той же ссылке мгновенные (кэш).

## Память агента

`save_notes` пишет в `LSCRIBE_NOTES` (по умолчанию `~/lecture-notes`) файл `<slug>.md` и строку в `INDEX.md`. `read_index` читается перед новой работой: так агент помнит, о чём шла речь в прошлых лекциях, и отвечает на вопросы по конспектам, не трогая видео. Папку подключать к агенту не нужно: чтение и запись идут через MCP-инструменты.

## Если MCP недоступен (запасной вариант)

Запустите `lecture-scribe serve`, а агенту в терминале Claude Code дайте скилл: он ходит в сервис по `localhost:8765` командами CLI. Облачному агенту без доступа к вашему компьютеру придётся передавать транскрипт файлом: `lecture-scribe get <id> > transcript.txt` в подключённую папку.

## Что может пойти не так

- Приложение запускает MCP-сервер с урезанным `PATH`; код сам добавляет `/opt/homebrew/bin` и каталог venv, чтобы нашлись `ffmpeg` и `yt-dlp`.
- Если инструменты не появились, откройте логи MCP в Claude Desktop (`~/Library/Logs/Claude/mcp-server-lecture-scribe.log`) и запустите руками `lecture-scribe mcp`, чтобы увидеть ошибку импорта.
