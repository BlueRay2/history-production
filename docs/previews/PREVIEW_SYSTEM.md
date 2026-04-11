# Preview System — TV-first design standard для history-production

**Источник:** consensus run 2026-04-11 (Claude + Codex + Gemini).
**Основа:** реальные данные YouTube Studio (TV 38.2%, Mobile 37.2%, Desktop 20.6%, Tablet 3.9%).
**Главная premise:** дизайн превью под **TV lean-back mode** с fallback на mobile, **не наоборот**. Это противоположно индустриальному default'у.

## Почему TV-first, а не mobile-first

Наш канал — единственная аудитория исторического YouTube где **38% зрителей на TV**. Это аномалия — у большинства каналов TV 15-25%. У нас такой высокий процент потому что:
- Наша Persona B (45-64, 41.7%) смотрит в гостиной вечером.
- Наш формат (17-26 мин, атмосферный) — lean-back friendly.
- Мы НЕ персонаж-driven — viewer не ждёт реакции presenter'а, что позволяет ambient просмотр.

Большинство индустриальных гайдов (hellothematic, ampifire, vidiq) оптимизированы для phone viewing. Эти гайды **частично переносятся** на TV, но большинство частных рекомендаций (faces +42%, 4.5:1 контраст, яркие насыщенные цвета) — это параметры, которые были измерены на phone. На TV доминирует **peripheral vision + luminance** processing, и правила отличаются.

---

## Hard rules (non-negotiable)

### 1. Maximum 3 элемента на превью

Превью должно визуально разбираться на ≤3 компонента:
- **Background plane** (один)
- **Focal subject** (один — landmark, silhouette, объект)
- **Text lockup** (один блок из 1-3 слов, опционально)

**Anti-pattern:** collage из 4+ элементов, фотомонтажи, multi-person тумбнейлы, 3+ объекта.

**Причина:** на peripheral vision tumbnail с 4+ элементами превращается в noise. Saliency map становится «плоской» и нет dominant shape, который магноцеллюлярный путь распознаёт за <200ms.

### 2. Luminance-first, hue-second

Первичная метрика contrast = luminance (яркость), не hue (цветовой тон). Требование:

- **Luminance contrast ratio ≥ 60% между focal subject и background.**
- Warm subject (охра, амбра, золото) на тёмном cool background (глубокий синий, тёмно-зелёный, черный) — наш стандарт.
- **ИЗБЕГАТЬ:** одинакового luminance contrast (warm-on-warm, cool-on-cool), дробящих luminance patterns.

**Причина:** peripheral vision обрабатывает в основном luminance, не hue. TV viewer узнает превью по яркостной форме до того как распознает цвет.

### 3. Text: 1-3 слова, крупным кеглем

- **Максимум 3 слова** в text lockup.
- **Кегль:** минимум 12% от высоты тумбнейла (при thumbnail 1280×720 это ~86px). Идеал — 15-18%.
- **Шрифт:** тяжёлый serif (авторитет для Persona B) или condensed sans (читаемость). Никаких decorative fonts.
- **Контраст текста к фону:** ≥ 7:1 (выше WCAG AAA) — потому что TV display имеет gamma/luminance искажения которых нет у phone.
- **Outline/stroke:** обязательный, ≥4px, чёрный или тёмный контрастный.
- **Text position:** безопасные зоны — верхняя треть либо нижняя четверть. Никогда не по центру (перекроет focal subject). Избегай правого нижнего угла (там YouTube overlays длительность).

**Anti-pattern:**
- 4+ слов
- Мелкий кегль («читается только при zoom»)
- Декоративные шрифты
- Текст без stroke на сложном фоне
- ALL CAPS wall-of-text

### 4. Single focal point (один dominant shape)

На peripheral vision видна только одна dominant форма. Это должна быть:
- **Landmark silhouette** (Hagia Sophia, skyline Venice, walls Constantinople) — наш предпочитаемый вариант для city-history.
- **Historical figure silhouette** (только если inseparable от города).
- **Symbolic object** (корабль, корона, меч, ключ — один, крупный).

**Composition:** focal subject занимает **30-50% площади** тумбнейла. Слишком маленький — не распознаётся peripherally. Слишком большой — превращается в «обои» без контекста.

**Rule of thirds adapted for TV:** focal point на пересечении left-third или right-third с horizontal middle — НЕ по центру, не по углам.

### 5. Warm accent на dark/cool background

**Палитра выбора (не больше 3 primary цветов):**

**Primary palette #1 — «Amber Dusk»** (наш default):
- Background: deep navy / midnight blue (#0D1B2A или #1B263B)
- Focal: warm amber / ochre (#E8A23B, #C77D30, #B8860B)
- Accent / text: cream / off-white (#F5F1E8) либо bright gold (#FFD700)

**Primary palette #2 — «Burnt Stone»** (для древних городов):
- Background: deep forest / charcoal (#2B2D2E, #1A2320)
- Focal: terracotta / sienna (#A0522D, #8B4513)
- Accent: bone / ivory (#F5F5DC)

**Primary palette #3 — «Crimson Frontier»** (для батальных / военных historic):
- Background: deep wine / oxblood (#3C0B0B, #2F0808)
- Focal: antique gold / bronze (#CD9A38, #B87333)
- Accent: bone / cream

**Что НЕ использовать:**
- Neon / acid colors
- High-saturation primary red / green / blue (кроме deep navy)
- Washed pastels
- Pure white backgrounds
- Gradient backgrounds с >2 color stops

### 6. Без faces (default) — museum portrait только по A/B

По consensus R3:
- **Default option:** landmark silhouette, no face.
- **A/B option:** museum-style sober portrait (painted / desaturated), face disproportionately large (fills ~40% of frame). **Не шокированное лицо**. Не кричащее. Contemplative / authoritative.
- Результат A/B — canonical decision per video type.

### 7. Без fine-detail maps

Карты работают только как **bold massing shapes** — силуэт континента, крупный обрисованный регион. **Никогда не** detailed political maps / thin line routes. Peripheral vision не читает линии.

### 8. Thumbnail должен быть legible surrounded by competing rectangles

Тест: сделай mockup YouTube browse grid (6 тумбнейлов в ряд), поставь свой thumbnail среди 5 generic конкурентов (Kings and Generals, Historia Civilis, VotP и т.д.). Твой должен быть **мгновенно узнаваем**. Если он «теряется» — переделывай.

---

## Тесты перед публикацией

### Тест 1 — 5-foot test (TV viewing)
На мониторе thumbnail отображается в размере ~320×180 (типичный размер плитки в YouTube grid). Отойди на 5 футов (~1.5м). Что читаемо:
- [ ] Дом-subject распознаётся?
- [ ] Текст читается?
- [ ] Есть одна dominant shape?
- [ ] Luminance contrast работает?

Если хоть что-то **нет** — переделать.

### Тест 2 — 1-second test (peripheral detection)
Закрой монитор, открой на 1 секунду, закрой. Что запомнилось?
- Если запомнились **3+ элемента** — перегружено, упрости.
- Если запомнились **silhouette + emotion** — отлично.
- Если запомнилось **ничего конкретного** — переделать.

### Тест 3 — greyscale test (luminance isolation)
Сделай thumbnail полностью greyscale. Если он всё ещё работает — luminance hierarchy правильная. Если превращается в grey mush — добавь luminance contrast.

### Тест 4 — surrounded by competitors test
См. Hard Rule #8.

### Тест 5 — 15° peripheral angle test
На полном мониторе открой YouTube, поставь cursor НЕ на thumbnail, а в 15° сторону (≈10см на стандартном мониторе). Боковым зрением определи: можешь ли распознать тумбнейл? Если да — работает для TV browse. Если нет — слишком детальный.

---

## Что НЕ делать (anti-patterns для TV viewing)

1. **Comic-strip превью** (2-3 панели) — дробят luminance map, peripheral path не парсит.
2. **Screaming / shocked faces** — работает на engagement bait audiences, но отталкивает нашу Persona B.
3. **Красные круги + стрелки** — universal clickbait signal, mutual kill обеих персон.
4. **Neon / glow effects** — disturb luminance map, выглядит cheap на TV dynamic range.
5. **Multi-element collages** — fail peripheral vision test.
6. **Fine-line maps** — invisible peripherally.
7. **Тонкий text без stroke** — вымывается на CRT / OLED gamma curves.
8. **Tiny text блоки** (<10% height) — fail 5-foot test.
9. **Gradient backgrounds с >2 stops** — создают false saliency points.
10. **Text по центру** — перекрывает focal subject, разрушает composition.

---

## Формула дизайна (для дизайнера / AI)

```
[LANDMARK SILHOUETTE — 35-45% площади, правая или левая треть]
+
[WARM LUMINANCE на COOL/DARK background — >60% contrast]
+
[1-3 слова title text — 12-18% height, upper/lower third, heavy serif, cream/gold color, 4px dark stroke]
+
[optional: single symbolic element — flame, crescent, anchor — max 15% площади]
```

**Разрешение:** 1920×1080 для export, дизайн проверить на 1280×720 и 320×180.

---

## Палитра по типу города (suggestion, не обязательство)

| Тип города | Палитра | Justification |
|---|---|---|
| Medieval European (Венеция, Flanders) | Amber Dusk | Документальная классика |
| Ancient (Рим, Афины) | Burnt Stone | Mediterranean stone aesthetic |
| Islamic Golden Age (Багдад, Damascus) | Amber Dusk + gold accent | Manuscript / dome aesthetics |
| East Asian (Quanzhou, Kyoto, Nara) | Burnt Stone + jade accent | Stone + temple aesthetic |
| Northern Europe (Amsterdam, Hanseatic) | Amber Dusk + deep navy | Maritime atmosphere |
| Central Asian / Silk Road | Amber Dusk + copper accent | Sunset caravan |
| Military siege topic | Crimson Frontier | Immediate tension signal |

---

## Примеры формулы для конкретных видео

### Quanzhou (готовится)
- **Silhouette:** profile силуэт древнего китайского порта — пагода + лодки джонки
- **Palette:** Burnt Stone + jade accent
- **Text:** `QUANZHOU` (6 букв, 15% height, cream on dark) ИЛИ `1271 A.D.` (6 символов, для Option A с primary source hook)
- **Secondary element:** стилизованная арабская вязь (15% площади, нижний угол) — намёк на multi-language character
- **Test**: peripherally viewer должен распознать «порт, пагода, не европейский»

### Amsterdam (alt-thumbnail для rerelease)
- **Silhouette:** канал + gable houses silhouette (классические dutch skyline)
- **Palette:** Amber Dusk + navy
- **Text:** `AMSTERDAM` (9 букв, 13% height)
- **Secondary element:** один парусный корабль (silhouette)

### Istanbul (alt-thumbnail для rerelease)
- **Silhouette:** Hagia Sophia + один minaret
- **Palette:** Crimson Frontier
- **Text:** `ISTANBUL` либо `CONSTANTINOPLE` (для text-test)
- **Secondary element:** flame / smoke за куполом — stake signal

---

## Версионирование и A/B

Каждое long-form видео при запуске **должно** иметь 2-3 версии превью в YouTube Test & Compare:

1. **Version A:** landmark silhouette, no face (TV-first)
2. **Version B:** museum portrait, warm-dominant (mobile-friendly)
3. **Version C (опционально):** element swap — другое title text / другой palette

**Тест длится** минимум 72 часа, возможно 10-14 дней при нашей impression volume (~26.8K/28d → ~900/day, нужно >3000 impressions per variant для статзначимости).

**Победитель фиксируется** как canonical для данного video type. После 5+ видео мы получим datasset «что работает для каких типов городов».

---

## Checklist для финального approval

Перед public-launch thumbnail:

- [ ] Hard rules 1-8 соблюдены
- [ ] 5-foot test пройден
- [ ] 1-second test пройден
- [ ] Greyscale test пройден
- [ ] Surrounded-by-competitors test пройден
- [ ] Peripheral angle test пройден
- [ ] 2-3 варианта в Test & Compare готовы
- [ ] Text lockup на безопасной зоне (не overlap с YouTube duration badge)
- [ ] Экспорт 1920×1080, проверен на 320×180
- [ ] Палитра соответствует city type
- [ ] Нет forbidden anti-patterns

Если все ✅ — ship.
