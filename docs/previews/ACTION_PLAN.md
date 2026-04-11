# Action Plan — от consensus run к production

**Источник:** consensus run 2026-04-11.
**Цель:** превратить consensus findings в конкретные задания для каждой роли команды.
**Измерение успеха:** CTR с 2.8% → 5%+ (первый этап) и long-form AVD% с 30-40% → 45%+ (первый этап) в течение 3 следующих long-form релизов.

---

## Распределение ролей в команде

- **Ярослав (Lead / scriptwriter / decision maker)** — утверждает всё ключевое, переписывает outlines под Cascade структуру
- **Настя (Designer / thumbnails)** — превью согласно PREVIEW_SYSTEM.md, A/B тесты
- **Дима (Footage + Montage)** — visual pacing, интеграция primary source beats, ретач первых 7 минут
- **Claude (Lead агент)** — ревизия скриптов, coordination, A/B анализ
- **Codex** — prompt-engineering для footage, proofreading #1
- **Gemini** — research, competitor monitoring, proofreading #2

---

## Для Насти — designer / thumbnail work

### Срочно (в течение недели)

**1. Прочитать `docs/previews/PREVIEW_SYSTEM.md`** — это твой новый референс. Hard rules 1-8 non-negotiable.

**2. Для Quanzhou (ближайший релиз) — создать ТРИ варианта thumbnail:**

- **Version A (рекомендован):** landmark silhouette, no face. Профиль старого китайского порта (пагода + джонки в силуэте), Burnt Stone palette + jade accent, text `QUANZHOU` либо `1271 A.D.` 15% height, cream на тёмном. Один маленький элемент арабской вязи в нижнем углу (15% площади).
- **Version B:** museum-style portrait — персидский купец / арабский путешественник в стиле исторической миниатюры, desaturated warm palette, text `QUANZHOU` 13% height. Лицо contemplative, НЕ screaming.
- **Version C (experimental):** текст-dominant — большое слово `QUANZHOU` на full-thumbnail, тонкий силуэт порта сзади, Amber Dusk palette. Для проверки title-thumbnail coupling.

**Запусти YouTube Test & Compare на все три** при публикации. Минимум 72 часа, цель — 10-14 дней.

**3. Для Amsterdam / Istanbul / New York — переделать thumbnails**
Текущие AVD 30-40% частично связаны с thumbnail mismatch — viewer кликнул на одно, получил другое. Нужен **alt-thumbnail** под каждое существующее long-form по TV-first правилам.

- Amsterdam: silhouette dutch gables + sailing ship, Amber Dusk
- Istanbul: Hagia Sophia silhouette + flame, Crimson Frontier
- New York: vintage skyline silhouette (1910-1920 era, не современная!), Amber Dusk

Заменить текущие через Test & Compare.

### Средний срок (2-4 недели)

**4. Создать design system file** — `docs/previews/design-tokens.md` с точными hex-кодами палитр, шрифтами, sizing. Использовать по всем будущим thumbnails.

**5. Вести design log** — `docs/previews/design-log.md` — после каждого A/B фиксируй:
- Версия A / B / C показатели
- Победитель, с каким margin
- Hypothesis до теста
- Результат после теста
- Обучение на следующий раз

**6. Изучить наш COMPETITORS.md раздел про Voices of the Past и Kings and Generals thumbnails** — они наш эталон. Регулярно (раз в 2 недели) смотри их новые релизы для референса.

### Что НЕ делать

- Не делай screaming/shock faces.
- Не делай collages из 4+ элементов.
- Не добавляй красные круги / стрелки даже «для акцента».
- Не используй neon / acid colors.
- Не верь «+42% faces» статистике для нашего niche без A/B подтверждения.

---

## Для Димы — footage + montage

### Срочно (в течение недели)

**1. Прочитать `docs/audience/debate/round-3.md`** — особенно раздел "Anchored Cascade" структура. Это твой новый каркас для монтажа long-form.

**2. Для Quanzhou (ближайший релиз) — ретач первых 7 минут под Cascade:**

- **0:00-0:30** — density modulation. 3-5 shots, одна major payload, пасta tonally continuous с body. **НЕ добавляй faster-cut фаззу MTV-style**. Плотность — информационная, не монтажная.
- **0:30-2:00** — primary hook delivery, 1 payoff каждые 30-45 сек. Плавнее пэйс.
- **2:00-4:00** — trust-building, micro-payoffs каждые 45-75 сек.
- **4:00-5:00** — **SECOND THESIS beat** — визуально пометь: здесь видео должно «измениться». Новый визуальный регистр, новый кусок ambient sound, смена palette в visuals.
- **5:00-8:00** — payoffs против new thesis, тот же ритм.
- **8:00-12:00** — **REVERSAL CLUSTER** — 2-3 трансформации close together. Огонь / завоевание / переворот / indoor→outdoor. Быстрее cuts допустимы здесь — это high-energy section.
- **12:00-end** — externalization (beyond-city stakes) + callback на opening image.

**3. Primary source beats**
Если в сценарии есть чтение primary source (letter/chronicle/diary), **обеспечь на минуте 4-5 И минуте 10-12** atmospheric ambient visuals без fast cuts — manuscript / document / city at dusk / candlelight scene. 20-30 сек ambient shot, Voices of the Past style. ElevenLabs TTS читает text, визуал держит настроение.

**4. Shorts-bridging visuals**
Первые 15 секунд long-form должны включать **один визуальный элемент знакомый из наших Shorts** про тот же город (если Short на тему уже есть). Это primes 74% traffic source на comfortable transition.

### Средний срок

**5. Rebuild первых 7 минут Amsterdam / Istanbul / New York** — тот же принцип Cascade. Re-publish? Вопрос к Ярославу; при нашем объёме impressions может иметь смысл «relaunch» чтобы YouTube взял свежие engagement signals.

**6. Создать footage prompt library** под Cascade structure — какие типы promptов работают для trust-building phase, thesis-reveal phase, reversal cluster phase. Дополнение к текущему ALL_CLIPS.md.

### Что НЕ делать

- Не делай fast-cuts каждые 2 секунды в минутах 0-4 — это Shorts pacing, viewer ждёт long-form density.
- Не используй «slow cinematic» 6-8 секундные planы в минутах 8-12 — там reversal cluster, должно быть дыхание.
- Не открывай ambient footage без narrative payload (≥10 секунд ambient без voiceover = risk drop).
- Не игнорируй primary source beats — они ключевые для retention.

---

## Для Ярика — scriptwriter / lead

### Срочно (в течение недели)

**1. Прочитать все артефакты consensus run:**
- `docs/audience/analytics/SNAPSHOT_2026-04-11.md` (already read)
- `docs/audience/PERSONA.md` — две персоны, их сильные recognition patterns
- `docs/audience/COMPETITORS.md` — роль каждого конкурента для нас
- `docs/audience/HOOKS_DEPLOYMENT.md` — матрица хуков под персоны
- `docs/audience/debate/round-3.md` — commited consensus
- `docs/previews/PREVIEW_SYSTEM.md` — TV-first правила

**2. Переписать outline Quanzhou под Anchored Cascade:**

Conceptual structure:
- **0:00-0:30** — Option A hook из HOOKS_DEPLOYMENT: «In 1271, a Persian merchant wrote a letter from a Chinese port. That letter tells us more about the medieval world than any European source. The city he wrote from is where half the world met — and almost no one today remembers its name.»
- **0:30-2:00** — раскрытие: кем был merchant, что он увидел, почему его letter matters.
- **2:00-4:00** — geographic + economic setup: почему именно Quanzhou, почему именно 1271, roadmap conflict.
- **4:00-5:00** — **SECOND THESIS**. Пример: «But here's the thing the merchant didn't know. The reason Quanzhou could host half the world's religions wasn't tolerance — it was tax policy. And that same tax policy was about to kill the city.»
- **5:00-8:00** — раскрытие этого второго тесиса (tax system, merchant networks, why foreigners paid taxes that locals didn't).
- **8:00-12:00** — **REVERSAL CLUSTER**: Mongols, plague, Ming closure, silk road collapse, Portuguese arrival. Три-четыре transformation beats.
- **12:00-end** — externalization (how Quanzhou's decline reshaped world trade) + callback на merchant's letter.

**3. Title A/B test** — подготовь 2-3 варианта title для Quanzhou:

- **Version 1:** `Entire History of QUANZHOU in 17 Minutes` (baseline template)
- **Version 2:** `The Largest Medieval Port You've Never Heard Of` (mechanism hook)
- **Version 3:** `QUANZHOU — The City Where Half the World Met` (primary quote hook)

Или формально другие варианты под Option A/B/C из HOOKS_DEPLOYMENT.

### Средний срок

**4. Переписать outline следующих 2 long-form** с первого раза под Cascade. Не ретачить старые — начать со свежих.

**5. Утвердить наше «triad» positioning** (Voices of the Past + Real Engineering + Kings and Generals элементы). Это определяет наш **brand voice**:
- Tone: serious, authoritative, но не formal — «educated friend explaining», не «professor lecturing»
- Density: 145-160 wpm, payoff каждые 30-60 секунд
- Primary sources integrated
- Mechanism-first, not chronology-first
- NO personality / presenter face
- NO humor as primary device
- NO explicit educational signalling («today we'll learn»)

**6. Добавить pinned comments** — две на каждое видео:
- **Pin 1:** system-analysis angle (для Persona A). Пример: «Fun fact: Quanzhou's tax records show 40% of merchants were foreign-born in 1271 — higher than any Italian port of the same era.»
- **Pin 2:** biographical / emotional angle (для Persona B). Пример: «The merchant whose letter I quoted is buried in Quanzhou's Islamic cemetery — still there today.»

### Что НЕ делать

- Не используй clickbait title patterns.
- Не открывай с «hi guys welcome back».
- Не ссылайся на previous videos в hook (99.5% new viewers).
- Не пиши «let me take you on a journey».
- Не используй «you were taught wrong» без смягчения.

---

## Metrics — что трекать и через какое окно

### Primary metrics (по каждому long-form релизу)

| Метрика | Baseline | Target (1st cycle) | Target (3 cycles) | Окно измерения |
|---|---|---|---|---|
| **CTR** | 2.8% | 5.0% | 5.5-7.0% | 14-28 дней |
| **AVD%** | 30-40% | 45% | 50%+ | 28 дней |
| **Retention at 25%** | N/A | >80% | >85% | 14 дней |
| **Retention at 33%** | ~drop point | >75% | >80% | 14 дней |
| **Retention at 50%** | ~25-30% | >55% | >65% | 14 дней |

### Secondary metrics

- Subscribers gained per long-form video (baseline +4-5, target +15+)
- Session watch-time (проверяем через Analytics, не должен падать после CTR lift — Gemini's warning)
- Browse features traffic share (текущий 10%, хотим lift to 15%+ через thumbnail consistency)
- Comments по Persona A language markers vs Persona B markers (ratio индикатор что обе cohorts engaged)

### Checkpoints

- **После 1-го Cascade видео (Quanzhou):** проверить 25%, 33%, 50% retention marks. Cascade работает? Если retention at 33% <60% — Cascade не landed, анализ.
- **После 3-х Cascade видео:** если average retention plateaus at ~45%, это **format ceiling signal** (Codex R3 warning). Revisit format.
- **После 6-и Cascade видео:** достаточно данных для confirming «proportional 33% drop» vs «absolute minute 6-7 drop» гипотез.

---

## A/B тесты для валидации consensus гипотез

1. **Hypothesis H1:** TV-first thumbnail (Version A) outperforms mobile-first (Version B) for device-stratified users.
   - **Test:** ship both through Test & Compare for Quanzhou, Amsterdam rerun, Istanbul rerun. Analyze device-split if available.
   - **Measurable:** CTR delta ≥ 0.5 percentage points для winner.

2. **Hypothesis H2:** Anchored Cascade structure lifts retention above 45% by fixing Act 1 audit point.
   - **Test:** ship Quanzhou + 2 more with Cascade structure. Measure retention at minute 4, 5, 6, 7.
   - **Measurable:** retention at 25-33% runtime stays >75% (vs current ~50-60%).

3. **Hypothesis H3:** Primary source beats lift retention in minute 4-5 specifically.
   - **Test:** include primary source beat at minute 4:30 in Quanzhou. Measure retention delta at minute 4:30 vs control (no primary source beat).
   - **Measurable:** local retention curve shows no drop at 4:30, possibly a re-engagement spike.

4. **Hypothesis H4:** Title rotation (3 variants) outperforms template («Entire History of CITY in N Minutes») baseline.
   - **Test:** Quanzhou ships with title A/B/C rotation via Test & Compare.
   - **Measurable:** winning title ≥ 0.3 percentage points CTR lift over template version.

5. **Hypothesis H5:** Bimodal double-pin comments lift engagement from both age cohorts.
   - **Test:** pin 2 comments from consensus script; measure reply ratio and like-counts per pin.
   - **Measurable:** each pin attracts distinct audience segment (different commenter language markers).

---

## Timeline

**Week 1 (2026-04-11 to 2026-04-18):**
- Ярик: переписать outline Quanzhou под Cascade
- Настя: 3 варианта thumbnail для Quanzhou
- Дима: реструктурировать existing Quanzhou montage под Cascade
- Claude: review всех трёх, final approval
- Relaunch thumbnails Amsterdam / Istanbul / NY (alt versions via Test & Compare)

**Week 2:**
- Release Quanzhou с new structure
- Immediate metric monitoring (24-72h для CTR signal)

**Week 3-4:**
- Checkpoint Quanzhou retention curves
- Если Cascade работает → второй video in pipeline под ту же структуру
- Если нет — diagnosis: какой beat не landed?

**Month 2 (6 weeks total):**
- 2-3 new Cascade videos released
- Accumulate data для H1-H5
- Refine artifacts if any finding overturns consensus

**Month 3:**
- Either: consensus confirmed, Cascade becomes permanent template → iterate on specific beats
- Or: format ceiling evidence → consensus run v2 для alternative format

---

## Decision log location

Все решения по A/B тестам, metric checkpoints, и production retach фиксировать в:
- `docs/audience/decisions.md` — chronological log of decisions
- `docs/previews/design-log.md` — design-specific decisions (Настя)
- `docs/audience/analytics/retention-library.md` — growing dataset retention curves per video (Claude maintains)

---

## Если что-то не сработает

1. **CTR не двигается после thumbnail redesign** → проблема в title. Rotate titles. Если титульное A/B тоже fails — проблема в topic-market fit (не Cascade).
2. **CTR растёт, но retention падает** → Gemini's warning materialized. Откатить CTR fix, приоритизировать retention restructure.
3. **Retention plateaus at ~45% после 3-х Cascade видео** → format ceiling. Revisit «Entire History of CITY in N Minutes» template.
4. **Retention падает в минуте 2-4** → Shorts-bridging провалился. Density modulation слишком разный. Переделать first 30 секунд на pure Shorts-style.
5. **Retention падает in reversal cluster (8-12)** → reversals слишком много / слишком быстро / не связаны. Уменьшить до 1 major reversal instead of 2-3.

---

## Final reminder

Consensus build — это **гипотеза**, не истина. Данные (Quanzhou + следующие 2-3 релиза) дадут реальный ответ. Если что-то провалится — не blame execution, revisit assumptions. Consensus Mode existence вообще in that the right answer can only come from data после того как grounded thinking задаст правильные experiments.
