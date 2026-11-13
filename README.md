# lecture-scribe

Локальный сервис транскрибации + скилл для Claude. Для видео в плеерах без субтитров (LMS, курсы, лекции): агент находит ссылку на видео, просит у сервиса расшифровку и пишет по ней конспект, главы или отвечает на вопросы «что говорят на 25-й минуте».

```
страница с плеером ──► агент достаёт URL потока (DevTools / браузерные тулзы)
                              │
                              ▼
        lecture-scribe (localhost): yt-dlp ─► ffmpeg ─► faster-whisper
                              │
                              ▼
        "[00:12:40] текст…"  ──► агент: конспект / главы / ответы с таймкодами
```

Всё работает у вас на машине: аудио и текст никуда не уходят, пока вы сами не отдадите транскрипт агенту.

## Установка

Нужны Python ≥ 3.10 и ffmpeg (`brew install ffmpeg`).

```bash
git clone <this-repo> && cd lecture-scribe
pip install -e .
lecture-scribe serve        # http://127.0.0.1:8765
```

При первом запуске faster-whisper скачает модель (`medium` ≈ 1.5 ГБ).

Подробное руководство по установке на macOS с разбором ошибок: [docs/SETUP-MAC.md](docs/SETUP-MAC.md). Подключение агента и память конспектов: [docs/AGENT.md](docs/AGENT.md).

## Скилл для Claude

Скопируйте папку `skill/lecture-notes` в каталог скиллов (Claude Code: `~/.claude/skills/lecture-notes`, либо `.claude/skills/` в проекте). Дальше просто пишите агенту: «составь конспект по лекции <ссылка>».

## CLI

```bash
lecture-scribe submit "<url|file>" --referer "<страница>" --language ru --wait   # → job id
lecture-scribe get <id>                          # текст с таймкодами
lecture-scribe get <id> --start 600 --end 1200   # окно, секунды
lecture-scribe get <id> --format srt             # srt | vtt | json | txt
lecture-scribe chunks <id> --minutes 10          # JSON-куски для длинных видео
lecture-scribe status [id]
lecture-scribe rm <id>
```

## HTTP API

| метод | путь | что делает |
|---|---|---|
| POST | `/jobs` | `{source, language?, model?, referer?, headers?, title?, force?}` → job (кэш по хэшу источника) |
| GET | `/jobs`, `/jobs/{id}` | статус: `queued → downloading → transcribing → done / error`, `progress` |
| GET | `/jobs/{id}/transcript?format=txt&start=&end=` | расшифровка или её окно |
| GET | `/jobs/{id}/chunks?minutes=10` | расшифровка кусками |
| DELETE | `/jobs/{id}` | удалить |

## Настройки (переменные окружения)

| переменная | по умолчанию | зачем |
|---|---|---|
| `LSCRIBE_MODEL` | `medium` | `tiny/base/small/medium/large-v3` |
| `LSCRIBE_DEVICE` | `auto` | `cpu` / `cuda` |
| `LSCRIBE_COMPUTE_TYPE` | `int8` | на GPU можно `float16` |
| `LSCRIBE_PORT` / `LSCRIBE_HOST` | `8765` / `127.0.0.1` | не выставляйте наружу, авторизации нет |
| `LSCRIBE_DATA` | `~/.lecture-scribe` | где лежат задачи и транскрипты |
| `LSCRIBE_COOKIES_FROM_BROWSER` | — | `chrome`, `firefox`… для видео за логином |
| `LSCRIBE_COOKIES_FILE` | — | cookies.txt (Netscape) вместо браузера |

## Видео за логином (Open edX и т.п.)

1. Откройте лекцию в браузере под своей учётной записью, запустите видео.
2. Агент (через браузерные инструменты) или вы вручную возьмёте адрес потока `.m3u8`/`.mp4` из DevTools → Network.
3. Если CDN требует авторизацию, запустите сервис с `LSCRIBE_COOKIES_FROM_BROWSER=chrome`; Referer передаётся флагом `--referer`.
4. Ссылки на поток часто подписаны и живут недолго: при ошибке возьмите свежую и добавьте `--force`.

Для DRM-защищённых видео это не сработает.

## Разработка

```bash
pip install -e .[dev] && pytest
LSCRIBE_BACKEND=fake lecture-scribe serve   # без Whisper, с заглушкой — для отладки интеграции
```

## Ограничения

- Одна задача за раз (очередь из одного воркера), Whisper тяжёлый.
- Whisper ошибается в именах и терминах; скилл велит агенту это помечать.
- Диаризации (кто говорит) нет.

MIT
