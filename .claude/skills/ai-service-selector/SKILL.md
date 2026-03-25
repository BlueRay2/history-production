---
name: ai-service-selector
description: |
  Decision matrix для выбора сервиса генерации (Sora 2 / Kling / Flow) для каждой сцены
  скрипта на основе типа контента, присутствия людей, сложности движения, длительности
  и бюджета. Background knowledge для prompt-engineer.
user-invocable: false
---

# AI Service Selector — Decision Matrix

Decision matrix для выбора оптимального сервиса видеогенерации на каждую сцену
YouTube-скрипта. Учитывает: тип контента, таймстамп в видео, присутствие людей,
сложность движения, бюджет.

**Сервисы:** Sora 2 Pro, Kling AI, Google Flow (Veo 3.1 / Veo 2).
**Не используем:** Runway, Hailuo, Midjourney, Flux.

---

## 1. Профили сервисов

### Sora 2 Pro
- **Best for:** Реалистичные люди, сложная физика (вода, ткань, дым, отражения), кинематографическое качество, нативный аудио-sync
- **Worst for:** Бюджетные итерации (дорого), volume B-roll, абстрактные визуалы
- **Cost tier:** 5/5 (самый дорогой)
- **Subscription:** $200/mo, 10K credits. 1080p 10s = ~600 credits
- **Free iteration:** Relaxed mode (3–30 мин ожидания, $0 marginal)
- **Unique:** Storyboard mode (multi-scene control), Cameo (character likeness)
- **Detail skill:** `.claude/skills/sora-2-pro-prompting/SKILL.md`

### Kling AI
- **Best for:** Motion-heavy camera work, стилизованный/абстрактный контент, cyberpunk/tech эстетика, character consistency (Elements feature), длинные клипы (extension chains до ~3 мин)
- **Worst for:** Фотореалистичные человеческие лица (ниже Sora), бюджетные итерации (нет бесплатного режима)
- **Cost tier:** 3/5 (средний)
- **Subscription:** Ultra $180/mo, 26K credits. Professional 10s = 70 credits (~$0.49)
- **Free iteration:** Нет
- **Unique:** Reversed pan/tilt, Start/End frame control, Kling 3.0 multi-shot
- **Detail skill:** `.claude/skills/kling-video-prompting/SKILL.md`

### Google Flow (Veo 3.1 / Veo 2)
- **Best for:** Атмосферные/environmental шоты, establishing shots, volume B-roll, бесплатные итерации, 4K upscale
- **Worst for:** Точный рендеринг лиц, длинные клипы (8s base limit), precise camera control
- **Cost tier:** 2/5 (самый экономичный благодаря бесплатному Fast)
- **Subscription:** Ultra $249.99/mo, 25K credits. Veo 3.1 Fast = FREE. Quality = 100 cr
- **Free iteration:** Да — Veo 3.1 Fast бесплатно на Ultra
- **Unique:** Native audio prompting (Veo 3.1), 4K upscaling (Ultra exclusive), Imagen 4 keyframes
- **Detail skill:** `.claude/skills/google-flow-prompting/SKILL.md`

---

## 2. Temporal Quality Strategy — "Premium Start"

**КЛЮЧЕВОЕ ПРАВИЛО для оптимизации бюджета и retention:**

### Первые ~3 минуты (hook + intro + context)

Использовать **PREMIUM** модели:
- **Sora 2 Quality** — для сцен с людьми и сложной физикой
- **Kling Professional** — для motion-heavy и стилизованных сцен
- **Flow Veo 3.1 Quality** — для атмосферных и establishing шотов

**Почему:** Первые 3 минуты — зона максимального оттока зрителей. YouTube Analytics
показывает, что 40–60% зрителей уходят в этом окне. Качество визуала напрямую
влияет на retention — viewer decision point находится в первых секундах каждой
новой сцены.

### После ~3 минут (основной контент)

Переход на **ECONOMY** модели. Приоритет:
1. **Flow Veo 3.1 Fast** — бесплатно на Ultra подписке (DEFAULT для economy tier)
2. **Kling Standard** — 10 cr/5s, хорошее качество для B-roll
3. **Flow Veo 2 Fast** — 10 cr/output, альтернатива если нужен другой стиль
4. **Sora 2 Quality** — ТОЛЬКО для hero-сцен с людьми после 3-минутной отметки

**Почему:** Зритель, прошедший 3-минутную отметку, уже вовлечён в контент.
Допустимо небольшое снижение quality ceiling ради оптимизации бюджета.
Narration и retention devices становятся главными драйверами удержания,
визуал — поддерживающим элементом.

---

## 3. Decision Tree

```
Для каждого клипа сцены (сцена содержит несколько клипов — по 1 на длинное предложение или группу коротких):

1. TIMESTAMP CHECK
   └─ Scene timestamp < 3 min? ──→ PREMIUM TIER (go to step 2P)
   └─ Scene timestamp >= 3 min? ─→ ECONOMY TIER (go to step 2E)

2P. PREMIUM TIER MODEL SELECTION
   ├─ Human faces/bodies prominent? ──→ Sora 2 Quality (1080p)
   ├─ Complex camera motion / stylized? → Kling Professional (1080p)
   ├─ Atmospheric / establishing shot? ─→ Flow Veo 3.1 Quality
   ├─ Abstract / conceptual? ───────────→ Kling Professional
   └─ Default ──────────────────────────→ Flow Veo 3.1 Quality

2E. ECONOMY TIER MODEL SELECTION
   ├─ Human faces (hero scene)? ────────→ Sora 2 Quality (exception)
   ├─ Complex camera motion required? ──→ Kling Standard
   ├─ Any other video need? ────────────→ Flow Veo 3.1 Fast (FREE)
   └─ Static overlay / diagram? ────────→ Static image (Imagen 4 / design tool)

3. SPECIAL CASES
   ├─ Photorealism critical, AI artifacts unacceptable? → Stock footage
   ├─ Text rendering needed? ───────────────────────────→ Static image (post-production)
   ├─ Duration > 10s single shot? ──────────────────────→ Kling extension chain
   ├─ Audio sync needed in footage? ────────────────────→ Sora 2 or Flow Veo 3.1
   └─ Iteration / drafting phase? ──────────────────────→ Flow Veo 3.1 Fast (FREE)
```

---

## 4. Decision Matrix Table

| Scene Type | Timestamp | Human? | Motion | Budget | Recommended | Fallback |
|---|---|---|---|---|---|---|
| Hook / opening | < 3 min | Yes | Any | Premium | Sora 2 Quality | Kling Professional |
| Hook / opening | < 3 min | No | High | Premium | Kling Professional | Flow Quality |
| Hook / opening | < 3 min | No | Low | Premium | Flow Veo 3.1 Quality | Kling Professional |
| Hero scene | >= 3 min | Yes | Any | Exception | Sora 2 Quality | Kling Professional |
| Action/motion | >= 3 min | No | High | Economy | Kling Standard | Flow Fast |
| B-roll / atmosphere | >= 3 min | No | Low | Economy | Flow Veo 3.1 Fast (FREE) | Kling Standard |
| Establishing shot | Any | No | Static/slow | Varies | Flow (Quality or Fast) | Stock footage |
| Abstract/conceptual | Any | No | Varies | Varies | Kling (Professional or Standard) | Flow |
| Product shot | Any | No | Slow | Varies | Kling Professional | Sora 2 |
| Text/diagram | Any | No | None | Minimal | Static image | — |

---

## 5. Fallback Chains

Если primary сервис не даёт acceptable результат после 2–3 итераций:

| Primary | Fallback 1 | Fallback 2 | Last Resort |
|---|---|---|---|
| Sora 2 | Kling Professional | Flow Quality | Stock footage |
| Kling | Flow Quality/Fast | Sora 2 | Stock footage |
| Flow | Kling Standard | Sora 2 | Stock footage |

**Правила fallback:**
- Переключение после 2–3 неудачных генераций (не больше)
- При переключении — адаптировать промпт под синтаксис нового сервиса
  (см. `.claude/skills/video-gen-prompts/SKILL.md` секция 5)
- Stock footage — крайний случай; искать на Pexels, Pixabay, Coverr

---

## 6. Budget Profiles

### Budget (минимальные расходы)
- **Стратегия:** Flow Veo 3.1 Fast (бесплатно) для ВСЕХ сцен
- **Подписка:** Google AI Ultra $249.99/mo
- **Cost per video:** ~$0 (только подписка)
- **Компромисс:** Ограниченное качество, нет human faces, 8s clips

### Standard (оптимальный баланс)
- **Стратегия:** Premium first 3 min + Economy after
- **Подписки:** Google AI Ultra + Kling Ultra ($180/mo)
- **Расклад:** Sora 2 / Kling Professional для первых 3 мин (5–8 сцен),
  Flow Fast + Kling Standard для остальных
- **Cost per video (20 scenes):** ~$430/mo subscriptions + credits
- **Рекомендуемый профиль для большинства YouTube каналов**

### Premium (максимальное качество)
- **Стратегия:** Sora 2 Quality / Kling Professional для ВСЕХ сцен
- **Подписки:** Sora Pro ($200/mo) + Kling Ultra ($180/mo) + Google AI Ultra ($249.99/mo)
- **Cost per video (20 scenes):** ~$630/mo subscriptions
- **Для:** Каналы с высоким CPM, где качество визуала = конкурентное преимущество

---

## 7. Интеграция с NICHE_STYLE_GUIDE

**Section 10 NICHE_STYLE_GUIDE.md** определяет операторские предпочтения:
- `PRIMARY_VIDEO_MODEL` — предпочтительный сервис оператора
- `BUDGET_PROFILE` — Budget / Standard / Premium
- `ALLOW_STOCK_FOOTAGE` — разрешён ли stock footage
- `MAX_SORA_SCENES` — лимит на количество Sora 2 сцен (бюджетный контроль)

**Правило:** Если NICHE_STYLE_GUIDE указывает конкретный PRIMARY_VIDEO_MODEL,
этот сервис используется по умолчанию для economy tier вместо Flow Fast.
Decision matrix всё равно применяется для premium tier и special cases.

**Конфликт приоритетов:**
1. NICHE_STYLE_GUIDE constraints (highest priority — operator's explicit preferences)
2. Temporal Quality Rule ("Premium Start")
3. This decision matrix (default recommendations)
