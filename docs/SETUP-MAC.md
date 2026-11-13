# Установка и первый запуск на macOS (как это ставилось по-настоящему)

Проверено на MacBook с Apple Silicon, Homebrew, Python 3.12, модель `small`, видео с Vimeo внутри Open edX (Лекториум).

## 1. Что должно быть в системе

```bash
which ffmpeg yt-dlp python3
brew install ffmpeg yt-dlp python@3.12     # чего не хватает
```

Whisper отдельно ставить не нужно. Старые `openai-whisper`, `whisper.cpp` и файлы вроде `~/.cache/whisper/base.pt` сервису не подходят: ему нужны модели faster-whisper, он скачивает их сам в `~/.cache/huggingface`.

## 2. Установка проекта

```bash
cd ~/coding/lecture-scribe
/opt/homebrew/bin/python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .
```

Используйте именно Python 3.12 (3.13 тоже должен подойти). На самых новых версиях Python (3.14) у пакета `av`, который тянет faster-whisper, нет готовой сборки. Тогда pip пытается собрать его из исходников и падает с `pkg-config is required for building PyAV`.

## 3. Запуск сервиса

```bash
source .venv/bin/activate
LSCRIBE_MODEL=small lecture-scribe serve      # http://127.0.0.1:8765
```

Окно остаётся занятым, всё остальное делайте во втором терминале (там тоже `source .venv/bin/activate`).
Первый запуск скачивает модель: `small` ≈ 500 МБ, `medium` ≈ 1,5 ГБ. Предупреждение про `HF_TOKEN` и подсказку про `device="mps"` можно игнорировать.

## 4. Видео с Лекториума (Open edX → Vimeo)

Плеер на странице курса — это iframe `https://player.vimeo.com/video/<ID>`. Найти ID: открыть страницу в браузере, DevTools → Elements → искать `player.vimeo.com`, или выполнить в консоли страницы
`[...document.querySelectorAll('iframe')].map(f => f.src)`.

Ролик разрешён к показу только на сайте курса, поэтому нужен Referer. Логин и cookie не потребовались.

```bash
yt-dlp --referer "https://mooc.lektorium.tv/" -F "https://player.vimeo.com/video/<ID>"   # проверка

lecture-scribe submit "https://player.vimeo.com/video/<ID>" \
  --referer "https://mooc.lektorium.tv/" --language ru --title "1.1 Название" --wait
lecture-scribe get <job id> > transcript.txt
```

Если yt-dlp пишет, что видео приватное или нужен hash, возьмите в iframe полный `src` вместе с `?h=...`.

## 5. Ошибки, которые встречались

| Симптом | Причина | Что делать |
|---|---|---|
| `pkg-config is required for building PyAV` | слишком новый Python, нет колеса `av` | venv на Python 3.12 |
| `open() got an unexpected keyword argument 'metadata_errors'` | faster-whisper декодирует аудио через `av`, а версия `av` не подходит | исправлено в коде: wav читается напрямую (`_read_wav` в `transcribe.py`). Дополнительно можно `pip install -U av faster-whisper` |
| после правки кода ошибка осталась | сервис не перечитывает код | остановить (Ctrl+C) и запустить `serve` заново |
| повторный `submit` по тому же адресу мгновенный | кэш по хэшу источника, аудио уже скачано | `--force`, если нужно скачать или распознать заново (удаляет и аудио) |

## 6. Куда что кладётся

- `~/.lecture-scribe/jobs/<id>/` — `meta.json`, `audio.wav`, `transcript.json`.
- Модели — `~/.cache/huggingface/hub`.
- Конспекты агента — см. `docs/AGENT.md`.

## 7. Качество

`small` годится для проверки конвейера. Для лекций берите `LSCRIBE_MODEL=medium` (или `large-v3`, если хватает памяти) и запускайте задачу с `--force`.
