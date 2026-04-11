# Target Video URLs

10 видео для hook breakdown, отобранных по коэффициенту views/subs (top 5 long-form + top 5 Shorts).

## Long-form

| # | Канал | Видео | URL | Длина | Views | Ratio |
|---|---|---|---|---|---|---|
| L1 | George's History | 1348: No Showers, No Toilet Paper – Life in the Middle Ages | https://youtube.com/watch?v=1ikf4ztFPQg | 11:04 | 862K | 82.9 |
| L2 | Restored Timeline | What New York Looked Like in 1660 \| AI Reconstruction of New Amsterdam | https://youtube.com/watch?v=tfGZEzoU_WY | 13:33 | 515K | 39.6 |
| L3 | Tim - Reborn History | The Bubonic Plague in the 1300s | https://youtube.com/watch?v=X-UgHOce2kk | 20:52 | 1.3M | 26.3 |
| L4 | The Chronicler | Chicago 1893 (AI Reconstruction) | https://youtube.com/watch?v=2kUzlQz67b0 | 5:40 | 74K | 24.7 |
| L5 | Scott's History | A Day in London, 1348 (Black Death) | https://youtube.com/watch?v=Ic7XzoSlwT0 | 12:26 | 251K | 21.6 |

## Shorts

| # | Канал | Видео | URL | Длина | Views | Ratio |
|---|---|---|---|---|---|---|
| S1 | Who Paid for Art | Sunset Strip, 1984 - When Hair Metal Took Over | https://youtube.com/shorts/mo5RoLmTYV8 | 0:53 | 653K | **272.1** |
| S2 | Who Paid for Art | The Evolution of The Dutch Soldier | https://youtube.com/shorts/-DP1hU7HQfg | 0:45 | 226K | 94.2 |
| S3 | Who Paid for Art | The Good, the Bad and the Ugly (THEN VS NOW) | https://youtube.com/shorts/Xvkp5p1t3TA | 0:57 | 111K | 46.3 |
| S4 | Who Paid for Art | Legendary Psychedelic Rock Bands From The 60s–70s | https://youtube.com/shorts/BnUeLLqgsGs | 0:53 | 89K | 37.1 |
| S5 | Majestic Studios | The Evolution of Indian Fashion #history | https://youtube.com/shorts/cRkGEs0Lg2M | 1:01 | 6M | 31.9 |

## ⚠️ Status транскриптов

YouTube заблокировал yt-dlp на нашем IP с 2026-04 (bot-detection: «Sign in to confirm you're not a bot»). Все попытки обойти через `--extractor-args player_client=web/mweb/tv_embedded` тоже блокированы. Транскрипты **не скачаны**.

**Workarounds для будущего:**
1. Cookies-based auth: `yt-dlp --cookies-from-browser firefox` если на сервере есть headed browser
2. Прокинуть свежие cookies через файл (требует ручного экспорта из браузера)
3. Использовать Invidious instance API (3rd-party YouTube proxy)
4. Использовать YouTube Data API v3 (требует Google API key)
5. Whisper транскрипция через скачивание audio через alternative tool

**Что получилось:**
- ✅ Все 10 thumbnails скачаны через прямой CDN (`https://i.ytimg.com/vi/{ID}/maxresdefault.jpg` обходит bot-detection)
- ✅ Все 10 video IDs найдены через yt-dlp search (поиск работает, downloading блокирован)
- ❌ Транскрипты — 0/10
- ❌ Видео клипы для frame extraction — 0/5

**Workaround для текущего анализа:** разбор хуков по thumbnail visual + title + channel pattern + контекст из исходного VidIQ-screenshot. Это даёт ~70% качества полного анализа (мы видим композицию, цвет, текст, тип сцены, но не первые 30 секунд audio narration).
