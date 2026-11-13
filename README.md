# lecture-scribe

MCP-сервер для Claude: расшифровывает видео из плееров без субтитров (LMS, курсы, лекции) локальным Whisper и ведёт память конспектов. Агент сам находит видео на странице, получает транскрипт, пишет конспект и запоминает, о чём была лекция.

```
вы: «составь конспект лекции <ссылка>»
        │
        ▼
агент (Claude Desktop / Cowork / Claude Code)
  ├─ браузер: находит ссылку на видео на странице
  └─ MCP lecture-scribe (работает на вашем компьютере)
        ├─ transcribe_video  → yt-dlp → ffmpeg → faster-whisper
        ├─ get_transcript / get_chunks → текст с таймкодами
        └─ save_notes / read_index / read_note → память конспектов
```

Всё считается на вашем компьютере. Аудио наружу не уходит, агент получает только текст.

## Требования

- macOS или Linux, Python **3.10–3.13** (на самых новых версиях Python у зависимости `av` может не быть готовой сборки). На маке: `brew install python@3.12`.
- `ffmpeg` и `yt-dlp`: `brew install ffmpeg yt-dlp`.
- Около 1,5 ГБ на модель `medium` (скачивается сама при первой расшифровке).

## Установка

```bash
git clone https://github.com/ArtiomVlasov/lecture-scribe ~/coding/lecture-scribe
cd ~/coding/lecture-scribe
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .
which lecture-scribe        # понадобится путь, например /Users/you/coding/lecture-scribe/.venv/bin/lecture-scribe
```

## Подключение к Claude

**Claude Desktop / Cowork.** Откройте Settings → Developer → Edit Config (файл `~/Library/Application Support/Claude/claude_desktop_config.json`) и добавьте блок `mcpServers` на верхний уровень, рядом с остальными ключами:

```json
{
  "mcpServers": {
    "lecture-scribe": {
      "command": "/Users/you/coding/lecture-scribe/.venv/bin/lecture-scribe",
      "args": ["mcp"],
      "env": {
        "LSCRIBE_MODEL": "medium",
        "LSCRIBE_NOTES": "/Users/you/lecture-notes"
      }
    }
  }
}
```

Полностью перезапустите приложение (Cmd+Q) и разрешите агенту вызовы инструментов (лучше «Always allow»).

**Claude Code.**

```bash
claude mcp add lecture-scribe -e LSCRIBE_MODEL=medium \
  -- /Users/you/coding/lecture-scribe/.venv/bin/lecture-scribe mcp
```

Папки агенту подключать не нужно: заметки пишет сам MCP-процесс.

## Как пользоваться

Напишите агенту:

> Составь конспект лекции https://…/courseware/…
> Видео во встроенном плеере без субтитров. Используй lecture-scribe: сначала `read_index`, затем `transcribe_video` (с referer — адресом сайта), потом конспект с таймкодами и `save_notes`.

Дальше агент работает сам. Первый запуск долгий: скачивается модель, потом идёт расшифровка. Повторный запрос по той же ссылке мгновенный (кэш). Пока идёт расшифровка, не давайте компьютеру засыпать.

Типичные просьбы:

- «Сделай главы лекции с таймкодами».
- «Что говорят на 25-й минуте про сегментацию?»
- «Какие лекции мы уже разбирали? Сравни, что в них сказано про X» (агент читает `read_index` и `read_note`).
- «Разбери все лекции главы 1 по очереди» (каждая лекция отдельная задача, индекс собирает их вместе).

Опционально скопируйте `skill/lecture-notes` в `~/.claude/skills/` (Claude Code): скилл объясняет агенту порядок действий и формат конспекта.

## Инструменты MCP

| инструмент | что делает |
|---|---|
| `transcribe_video(source, referer?, language?, title?, force?, wait_seconds?)` | ставит видео на расшифровку (страница, `player.vimeo.com/video/<id>`, `.m3u8`/`.mp4`, локальный файл), ждёт до `wait_seconds`, возвращает статус |
| `job_status(job_id, wait_seconds?)` | статус `queued → downloading → transcribing → done / error`, прогресс |
| `list_jobs()` | все задачи |
| `get_transcript(job_id, start_seconds?, end_seconds?)` | текст `[ЧЧ:ММ:СС] …`, можно окном по времени |
| `get_chunks(job_id, minutes?)` | транскрипт кусками для длинных лекций |
| `save_notes(title, content, gist, job_id?, source?)` | сохраняет конспект и обновляет `INDEX.md` |
| `read_index()` | `INDEX.md`: что уже разобрано |
| `read_note(slug)` | конспект одной лекции |

## Где что лежит

- Задачи и транскрипты: `~/.lecture-scribe/jobs/<id>/` (`LSCRIBE_DATA`).
- Конспекты: `~/lecture-notes/` (`LSCRIBE_NOTES`): `INDEX.md` и по файлу `<slug>.md` на лекцию.
- Модели Whisper: `~/.cache/huggingface/hub`.

## Настройки (переменные `env` в конфиге)

| переменная | по умолчанию | зачем |
|---|---|---|
| `LSCRIBE_MODEL` | `medium` | `tiny/base/small/medium/large-v3`; для проверки хватает `small` |
| `LSCRIBE_DEVICE` | `auto` | `cpu` / `cuda` |
| `LSCRIBE_COMPUTE_TYPE` | `int8` | на GPU можно `float16` |
| `LSCRIBE_NOTES` | `~/lecture-notes` | папка конспектов |
| `LSCRIBE_DATA` | `~/.lecture-scribe` | задачи и транскрипты |
| `LSCRIBE_COOKIES_FROM_BROWSER` | — | `chrome`, `firefox`… для видео за логином |
| `LSCRIBE_COOKIES_FILE` | — | cookies.txt (Netscape) вместо браузера |

## Видео в LMS (Open edX и т.п.)

Плеер на странице курса обычно встроен через iframe (Vimeo, YouTube). Агент находит его адрес через браузер: например `https://player.vimeo.com/video/<id>`. Такой ролик разрешён к показу только на сайте курса, поэтому нужен `referer` (адрес сайта, например `https://mooc.lektorium.tv/`). Логин и cookie для Лекториума не потребовались.

Проверить вручную: `yt-dlp --referer "https://mooc.lektorium.tv/" -F "https://player.vimeo.com/video/<id>"`.

Если yt-dlp просит hash, возьмите полный `src` iframe вместе с `?h=…`. Для видео за логином запускайте с `LSCRIBE_COOKIES_FROM_BROWSER=chrome`. DRM-защищённые видео не поддерживаются.

## Если что-то не работает

| симптом | что делать |
|---|---|
| у агента нет инструментов `lecture-scribe` | проверьте JSON (блок `mcpServers` на верхнем уровне, запятые), полностью перезапустите приложение, смотрите лог `~/Library/Logs/Claude/mcp-server-lecture-scribe.log` |
| `pkg-config is required for building PyAV` при установке | слишком новый Python: пересоздайте venv на Python 3.12 |
| `ffmpeg not found` / `yt-dlp not found` | `brew install ffmpeg yt-dlp` (код сам добавляет `/opt/homebrew/bin` в `PATH`) |
| yt-dlp: видео приватное / 403 | передайте `referer`; для Vimeo при необходимости полный адрес iframe с `?h=` |
| «ссылка протухла» | ссылки на поток часто подписаны и живут недолго: возьмите свежую и повторите с `force=true` |
| много ошибок в терминах | `LSCRIBE_MODEL=large-v3` или `medium`, повторить с `force=true`; в конспекте сомнительные места помечаются |
| после правки кода без изменений | перезапустите приложение: MCP-процесс код сам не перечитывает |

Проверка сервера вручную: `lecture-scribe` (без аргументов запускается и ждёт по stdio, выход Ctrl+C).

## Разработка

```bash
pip install -e .[dev] && pytest
LSCRIBE_BACKEND=fake lecture-scribe   # заглушка вместо Whisper, для проверки интеграции
```

## Ограничения

- Одна расшифровка за раз (Whisper тяжёлый), остальные ждут в очереди.
- Диаризации (кто говорит) нет.
- Whisper ошибается в именах и терминах.

MIT
