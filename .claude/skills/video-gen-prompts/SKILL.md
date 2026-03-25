---
name: video-gen-prompts
description: |
  Сводный справочник по трём сервисам генерации видео (Sora 2, Kling, Google Flow).
  Сравнительная таблица, гайд по адаптации generic промптов под каждый сервис, ссылки
  на детальные скиллы. Background knowledge для prompt-engineer.
user-invocable: false
---

# Video Generation Prompts — Cross-Service Reference

Сводный справочник для prompt-engineer. Объединяет ключевые характеристики трёх
сервисов AI-видеогенерации, используемых в продакшен-пайплайне. Для детальных
гайдов по каждому сервису — переходи к соответствующему скиллу.

---

## 1. Сводная таблица сервисов

| Parameter | Sora 2 Pro | Kling AI (Ultra) | Google Flow (Ultra) |
|---|---|---|---|
| **Max Duration** | 25s (storyboard) | ~3 min (extension chains) | 8s (single gen), ~29s (with extensions) |
| **Max Resolution** | 1080p (UI) / 1024p (API) | 1080p Professional | 1080p + 4K upscaling (Ultra) |
| **Aspect Ratios** | 16:9, 9:16, 1:1 | 16:9, 9:16, 1:1 | 16:9, 9:16, 1:1 |
| **Strengths** | Photorealistic humans, physics simulation, native audio, storyboard mode, Cameo | Camera motion control, abstract/stylized content, character consistency (Elements), multi-shot 3.0 | Atmospheric/environmental footage, free Fast iterations (Ultra), 4K upscale, native audio (Veo 3.1) |
| **Weaknesses** | Expensive per clip, no free tier, degrades >200 words | Reversed pan/tilt terminology, inconsistent face quality on realism, credit-hungry audio mode | 8s clip limit, less precise human rendering, prompt order sensitivity |
| **Subscription** | Pro $200/mo (10K credits) | Ultra $180/mo (26K credits) | Ultra $249.99/mo (25K credits) |
| **Free Iteration** | No (Relaxed mode = $0 marginal, but slow) | No | Yes — Veo 3.1 Fast = FREE on Ultra |
| **Prompt Length Sweet Spot** | 50–200 words | 50–80 words (T2V), 20–40 words (I2V) | 100–150 words (3–6 sentences) |
| **Prompt Formula** | Style declaration first → Subject → Action → Environment → Camera | Subject+Action → Camera → Environment+Lighting → Style/Texture | Cinematography → Subject → Action → Context/Environment → Style & Ambiance |

---

## 2. Sora 2 Pro — краткие принципы

**Детальный скилл:** `.claude/skills/sora-2-pro-prompting/SKILL.md`
**Архитектура промптов:** `.claude/skills/sora-2-pro-prompting/references/PROMPT_ARCHITECTURE.md`
**Стоимость:** `.claude/skills/sora-2-pro-prompting/references/COSTS_AND_LIMITS.md`

Ключевые правила:
1. **Style declaration first** — первая фраза задаёт визуальный стиль всего клипа
   (`Cinematic film shot in 35mm, shallow depth of field`)
2. **One camera move + one subject action per shot** — совмещение нескольких движений вызывает визуальный хаос
3. **50–200 words** — оптимальная длина; свыше 200 слов качество деградирует
4. **Structure in blocks**: Style → Subject → Action → Environment → Camera → Negative
5. **Concrete visual language** — "golden hour sun through blinds" вместо "beautiful lighting"
6. **Relaxed mode** (Pro) — бесплатная генерация после исчерпания credits, 3–30 мин ожидания
7. **Draft at 480p** (25 cr/5s) → final at 1080p (600 cr/10s) — экономия 76%

**Best for:** Сцены с людьми, сложная физика (вода, ткань, дым), кинематографическое качество, hero-шоты.

---

## 3. Kling AI — краткие принципы

**Детальный скилл:** `.claude/skills/kling-video-prompting/SKILL.md`
**Камеры:** `.claude/skills/kling-video-prompting/references/CAMERA_REFERENCE.md`
**Библиотека промптов:** `.claude/skills/kling-video-prompting/references/PROMPT_LIBRARY.md`

Ключевые правила:
1. **Формула:** Subject+Action → Camera Movement → Environment+Lighting → Style/Texture
2. **50–80 words** (T2V), 20–40 words (I2V — описывать только движение, не повторять содержимое изображения)
3. **CRITICAL — REVERSED PAN/TILT:**
   - Kling "pan" = вертикальное движение (стандартный "tilt")
   - Kling "tilt" = горизонтальное движение (стандартный "pan")
   - Для горизонтального поворота камеры пишем `tilt left` / `tilt right`
4. **Continuous scene description** — не список ключевых слов, а описание как сцена развивается
5. **Конкретные источники света** — `neon signs reflecting in wet asphalt`, не `dramatic lighting`
6. **Texture = credibility** — grain, lens flares, reflections, condensation, smoke
7. **Image-to-Video** рекомендуется для продакшена — даёт больше контроля над композицией
8. **Версии:** 2.5 Turbo для B-roll, 3.0 для hero-шотов, 2.6 только для нативного аудио

**Best for:** Motion-heavy камера, стилизованный контент, абстрактные визуалы, cyberpunk/tech эстетика.

---

## 4. Google Flow (Veo 3.1 / Veo 2) — краткие принципы

**Детальный скилл:** `.claude/skills/google-flow-prompting/SKILL.md`
**Формула промптов:** `.claude/skills/google-flow-prompting/references/PROMPT_FORMULA.md`
**Стоимость Ultra:** `.claude/skills/google-flow-prompting/references/ULTRA_PRICING.md`
**Community insights:** `.claude/skills/google-flow-prompting/references/COMMUNITY_INSIGHTS.md`

Ключевые правила:
1. **Формула:** Cinematography → Subject → Action → Context/Environment → Style & Ambiance
2. **100–150 words** (3–6 предложений). Короче — generic результат; длиннее — потеря когерентности
3. **Order matters** — модель приоритизирует элементы, упомянутые первыми
4. **Veo 3.1 Fast = FREE** на Ultra подписке — используй для неограниченных итераций
5. **Veo 3.1 Quality** = 100 credits/output — для финальных hero-клипов
6. **Per-output billing** — 4 output за 1 запрос = 4× стоимость; при итерации генерируй 1 output
7. **Audio prompting** (Veo 3.1) — можно описать звуковое сопровождение в промпте
8. **8s clip limit** — проектируй сцены в рамках 8 секунд, extension = 20 cr каждый

**Best for:** Атмосферные фоны, establishing shots, volume B-roll (бесплатно на Fast), итерации промптов.

---

## 5. Гайд по адаптации промптов

### Generic → Service-Specific конвертация

Начни с generic-промпта из шаблона сцены, затем адаптируй:

**Generic шаблон:**
```
[Shot type] [Camera movement] of [Subject] [Action] in [Environment].
[Lighting]. [Style/mood]. [Texture/details].
```

**→ Sora 2 адаптация:**
```
[Style declaration first]. [Subject description]. [Single action].
[Environment with concrete light sources]. [Single camera movement].
[Negative prompt separately if needed].
```
- Переставь style declaration в начало
- Убедись что одно движение камеры + одно действие субъекта
- Добавь конкретные визуальные детали (film grain, lens type)
- Не превышай 200 слов

**→ Kling адаптация:**
```
[Subject + Action] → [Camera movement with REVERSED pan/tilt] →
[Environment + specific light sources] → [Style/texture modifiers].
```
- Kling "pan" = вертикальное! Для горизонтального: `tilt left/right`
- Сократи до 50–80 слов
- Опиши как сцена развивается во времени (beginning → end)
- Добавь физические текстуры (grain, reflections, smoke)

**→ Flow адаптация:**
```
[Cinematography/camera first]. [Subject description]. [Action unfolding].
[Context/environment]. [Style, ambiance, mood].
```
- Самое важное — первым (model prioritizes early elements)
- Расширь до 100–150 слов (3–6 предложений)
- Включи ambient audio description если нужен звук (Veo 3.1)
- Не используй keyword lists — пиши полными предложениями

### Подводные камни при адаптации

| Ловушка | Сервис | Последствие | Решение |
|---------|--------|-------------|---------|
| Reversed pan/tilt | Kling | Камера двигается в неправильном направлении | Всегда проверяй: Kling pan=vertical, tilt=horizontal |
| Длинный промпт (>200 слов) | Sora 2 | Деградация качества, игнорирование поздних элементов | Сократи, приоритизируй ключевые элементы |
| Слишком короткий промпт (<80 слов) | Flow | Generic/скучный результат | Расширь до 100–150 слов с деталями |
| Несколько движений камеры | Sora 2 | Визуальная инкогерентность | Одно движение камеры на один шот |
| Keyword list вместо описания | Kling, Flow | Низкое качество, нет motion narrative | Пиши непрерывное описание сцены |
| Описание изображения в I2V | Kling | Конфликт с source image, артефакты | Описывай только движение в I2V mode |
| Важный элемент в конце промпта | Flow | Элемент игнорируется или недоработан | Перемести ключевые элементы в начало |

---

## 6. Справочник общих style keywords

Эти формулировки эффективны на **всех трёх** сервисах:

### Lighting
- `golden hour sunlight`, `blue hour ambient`, `neon-lit`, `overcast diffused`
- `rim lighting`, `backlit silhouette`, `volumetric god rays`, `chiaroscuro`
- `flickering firelight`, `cold fluorescent`, `warm tungsten`

### Camera
- `wide establishing shot`, `medium shot`, `close-up`, `extreme close-up`
- `slow dolly in`, `tracking shot`, `crane ascending`, `handheld`
- `shallow depth of field`, `deep focus`, `rack focus`

### Mood & Atmosphere
- `tense`, `melancholic`, `euphoric`, `eerie`, `contemplative`
- `urgent`, `serene`, `oppressive`, `dreamlike`, `raw/gritty`

### Color & Grade
- `desaturated teal and orange`, `high contrast`, `muted earth tones`
- `vibrant neon palette`, `monochromatic`, `warm golden tones`
- `crushed blacks`, `lifted shadows`, `cinematic color grade`

### Texture & Film
- `shot on 35mm film`, `16mm grain`, `anamorphic lens flare`
- `bokeh highlights`, `lens distortion`, `film grain`
- `4K`, `photorealistic`, `hyperrealistic detail`

> **Совет:** Поддерживай единую style line (набор style keywords) для всех сцен одного видео
> независимо от сервиса. Это обеспечивает визуальную когерентность при использовании
> нескольких генераторов в одном проекте.
