# ElevenLabs v3 Prompting Guide

> Last verified: March 2026. Sources: official ElevenLabs documentation, blog posts, help center.
> Applies to model `eleven_v3`. For v2 models see notes in section 5.

---

## 1. Audio Tags (v3 Exclusive)

Audio tags — square-bracket inline directives, действующие как "режиссёрские ремарки"
для AI-голоса. Они **не произносятся вслух** — модифицируют подачу или вставляют звуки.
Это флагманская фича v3, заменяющая SSML.

**Синтаксис:** `[tag]` — размещается inline в тексте в точке, где эффект должен произойти.

### 1.1 Emotion & Tone

`[sad]`, `[angry]`, `[excited]`, `[sarcastic]`, `[nervous]`, `[frustrated]`,
`[sorrowful]`, `[calm]`, `[happily]`, `[mischievously]`, `[curious]`

### 1.2 Voice Delivery

`[whispering]` / `[whispers]`, `[shouting]` / `[shouts]`, `[singing]` / `[sings]`

### 1.3 Non-Verbal / Reactions

`[laughs]`, `[laughs harder]`, `[starts laughing]`, `[wheezing]`, `[giggles]`,
`[snorts]`, `[nervous laugh]`, `[crying]`, `[sighs]`, `[exhales]`,
`[clears throat]`, `[swallows]`, `[gulps]`, `[yawning]`, `[coughing lightly]`

### 1.4 Pacing & Delivery Control

`[pause]`, `[short pause]`, `[long pause]`, `[dramatic pause]`, `[rushed]`,
`[slows down]`, `[deliberate]`, `[rapid-fire]`, `[stammers]`, `[drawn out]`,
`[hesitates]`, `[breathes]`, `[continues after a beat]`

### 1.5 Emphasis

`[emphasized]`, `[stress on next word]`, `[understated]`

### 1.6 Sound Effects

`[applause]`, `[clapping]`, `[gunshot]`, `[explosion]`, `[door creaks]`,
`[footsteps]`, `[telephone rings]`, `[drumroll]`, `[leaves rustling]`

### 1.7 Accent & Voice Modifiers

`[strong French accent]`, `[strong X accent]` (подставить любую национальность),
`[robotic]`, `[childlike tone]`, `[deep voice]`, `[pirate voice]`, `[robotic tone]`

### 1.8 Narrative / Genre Style

`[storytelling tone]`, `[voice-over style]`, `[cinematic tone]`,
`[documentary style]`, `[narrative flourish]`, `[fantasy]`, `[cyberpunk]`,
`[noir]`, `[horror narration]`, `[comedy]`, `[western]`, `[musical]`

### 1.9 Audio Processing / Effects

`[robotic modulation]`, `[glitch]`, `[vocoder]`, `[echo]`, `[reverb]`,
`[pitch shift up]`, `[pitch shift down]`, `[lo-fi]`

### 1.10 Environment / Ambient

`[forest morning]`, `[city street]`, `[office ambient]`, `[cafe ambient]`,
`[rain heavy]`, `[library ambient]`

### 1.11 Dialogue Control

`[interrupts]` / `[interrupting]`, `[overlapping speech]` / `[overlapping]`,
`[cuts in]`, `[talks over]`, `[responds quickly]`, `[responds slowly]`, `[fast-paced]`

### Комбинирование тегов

Несколько тегов можно стекать для послойного эффекта:

```
[nervously][whispers] I... I'm not sure this is going to work. [gulps] But let's try anyway.
[happily][shouts] We did it! [laughs] I can't believe we actually won!
[angry][laughing]  — produces an angry laugh
[sad][whispers]    — produces sad whispering
```

### Важные правила

- Теги **обязательно** в квадратных скобках — иначе модель произнесёт их вслух
- Теги должны соответствовать эмоциональной траектории текста — противоречивые теги
  (голос кричит + `[whispering]`) дают плохой результат
- Теги работают на всех 70+ языках v3
- Система тегов **open-ended / generative** — модель интерпретирует natural language
  описания, можно экспериментировать за пределами документированных тегов

---

## 2. Voice Settings (Sliders)

Все значения на шкале **0.0 — 1.0**.

### Stability

Контролирует вариативность между генерациями. Ниже = больше эмоций и вариаций;
выше = стабильнее и предсказуемее.

| Use Case | Recommended Range |
|---|---|
| YouTube нарратив | 0.35 — 0.40 (избегает монотонности, сохраняя когерентность) |
| Аудиокнига / long-form | 0.50 — 0.70 |
| Character voice acting | 0.30 — 0.50 |
| Корпоративный / нейтральный | 0.70 — 0.90 |

**Warning:** Ниже 0.30 — риск нестабильного и непредсказуемого output.

### Similarity Boost (Clarity + Similarity Enhancement)

Контролирует соответствие output оригинальному voice sample. Высокие значения
также усиливают clarity. Очень высокие значения могут вносить артефакты.

| Use Case | Recommended Range |
|---|---|
| General / safe default | 0.75 |
| Maximum clarity (нарратив) | 0.70 — 0.80 |
| Character flexibility | 0.60 — 0.70 |

**Warning:** Выше 0.80 возможны distortion artifacts.

### Style Exaggeration

Усиливает естественный speaking style голоса. Добавляет computational load и latency.

| Use Case | Recommended Range |
|---|---|
| Default / safe | 0.00 |
| YouTube нарратив | 0.10 — 0.50 |
| Dramatic character voice | 0.70 — 1.00 |
| Корпоративный / нейтральный | 0.00 — 0.20 |

**Warning:** Extreme style + low stability + high similarity = нестабильно на длинных скриптах.

### Speaker Boost

Binary enhancement — увеличивает clarity и presence. Добавляет latency.
Лучше для pre-recorded контента (YouTube). Не подходит для real-time.

### Speed Control

Range: **0.7 — 1.2** (default 1.0). API parameter. Контролирует скорость речи без влияния на pitch.

### Рекомендуемый пресет для YouTube нарратива

| Parameter | Value |
|---|---|
| Stability | 0.60 — 0.80 |
| Similarity | 0.70 |
| Style Exaggeration | 0.20 — 0.40 |
| Speaker Boost | ON |
| Speed | 0.9 — 1.0 |

---

## 3. Punctuation Effects on Delivery

v3 интерпретирует пунктуацию как prosodic cues:

| Punctuation | Effect |
|---|---|
| **Точка (.)** | Natural sentence-ending pause, falling intonation |
| **Запятая (,)** | Brief pause, slight continuation intonation |
| **Многоточие (...)** | Extended pause — hesitation, weight, trailing off. **Основной механизм пауз в v3** |
| **Тире (--)** | Abrupt pause, interruption, topic shift. В dialogue mode сигнализирует interruptions |
| **Восклицательный (!)** | Increased energy, louder delivery, rising intensity |
| **Вопросительный (?)** | Natural upward inflection |
| **КАПИТАЛИЗАЦИЯ** | Emphasis and stress. "This is AMAZING!" — vocal intensity на capitalized words |
| **Двойной восклицательный (!!)** | Even more emphatic delivery |
| **Двоеточие (:)** | Slight pause перед explanation/list |

**ВАЖНО:** SSML `<break>` tags **не поддерживаются** в v3. Используй многоточие и
audio tags `[pause]` / `[long pause]` для контроля пауз.

---

## 4. Multi-Speaker Dialogue

### Text to Dialogue API (v3 only)

Выделенный endpoint для multi-speaker conversations:
- JSON array of speaker turns (voice ID + text для каждого)
- Нет лимита на количество speakers
- Автоматическое управление transitions, overlapping speech, emotional changes, interruptions
- Все speakers разделяют conversational context

### Dialogue Mode Features

- Natural pacing с interruptions и tone shifts
- Пунктуация управляет dialogue dynamics: hyphens = interruptions, ellipses = trailing speech
- Audio tags управляют каждым голосом: `[interrupts]`, `[overlapping speech]`, `[cuts in]`

### Для YouTube скриптов (single speaker)

При использовании одного narrator voice:
- Emotional audio tags для смены тона в "цитируемой" речи
- Обработка разных character lines отдельными голосами, затем combining в post-production
- Text to Dialogue endpoint для scripted conversations

---

## 5. Models Comparison

| Model | ID | Languages | Char Limit | Latency | Audio Tags | SSML Break | Best For |
|---|---|---|---|---|---|---|---|
| **Eleven v3** | `eleven_v3` | 70+ | 5,000 (~5 min) | 1-3s | YES | NO | Expressive narration, dialogue, emotional content |
| **Multilingual v2** | `eleven_multilingual_v2` | 29 | 10,000 (~10 min) | Medium-high | NO | YES (up to 3s) | Long-form professional, consistent quality |
| **Turbo v2.5** | `eleven_turbo_v2_5` | 32 | 40,000 (~40 min) | ~250-300ms | NO | YES | Balance quality/speed |
| **Flash v2.5** | `eleven_flash_v2_5` | 32 | 40,000 (~40 min) | ~75ms | NO | YES | Real-time, bulk, 50% lower cost |
| **Turbo v2** | `eleven_turbo_v2` | EN only | 30,000 (~30 min) | ~250-300ms | NO | YES | English-only fast |
| **Flash v2** | `eleven_flash_v2` | EN only | 30,000 (~30 min) | ~75ms | NO | YES | English-only ultra-fast |

**Для YouTube нарратива:** v3 — лучший выбор для expressiveness. Multilingual v2 лучше
для very long, consistent passages или если нужен SSML break для точного контроля пауз.

---

## 6. Pronunciation Controls

### SSML Phoneme Tags (только v2 models)

Поддерживаются на: `eleven_flash_v2`, `eleven_turbo_v2`, `eleven_monolingual_v1`.
**НЕ поддерживаются на v3 и Multilingual v2.**

CMU Arpabet (recommended):
```
<phoneme alphabet="cmu-arpabet" ph="M AE1 D IH0 S AH0 N">Madison</phoneme>
```

### Pronunciation Dictionaries (All models)

XML-based `.pls` files с двумя типами правил:
1. **Phoneme rules** — IPA/Arpabet pronunciation (English only, v2 only)
2. **Alias rules** — замена слова на alternative spelling. **Работает на ВСЕХ моделях и языках, включая v3.**

### Практические техники для v3

Поскольку v3 не поддерживает SSML phoneme tags:
- **Alias rules в pronunciation dictionaries** — map tech terms к phonetic spellings
- **Phonetic respelling inline** — "Nietzsche" → "Nee-chuh"
- **Expand abbreviations** — "NASA" → "nasa" (как слово) или "N. A. S. A." (по буквам)
- **Expand numbers/symbols** — "$1,234" → "one thousand two hundred thirty-four dollars"
- **Dates** — "2024-01-01" → "January first, twenty twenty-four"

---

## 7. Best Practices for YouTube Narration

### Text Formatting

1. **Full paragraphs, не single sentences** — модель даёт более natural prosody с длинным контекстом
2. **Natural narrative style** — модель выводит pacing из quality текста
3. **КАПИТАЛИЗАЦИЯ для emphasis** — sparingly: "This changed EVERYTHING"
4. **Многоточие для dramatic pauses** — "And then... silence."
5. **Убирай stage directions после генерации** — "she said, trembling" будет произнесено вслух. Используй audio tags вместо narrative cues

### Emotional Range

6. **Audio tags для emotional shifts** — `[excited]`, `[serious]`, `[whispers]` в ключевых моментах
7. **Не перетегивай** — позволь модели выводить эмоции из контекста. Теги только там, где natural reading промахнётся
8. **Align tags с trajectory контента** — contradictory tags = плохой результат

### Pacing

9. **Speed 0.9-1.0** — чуть медленнее default звучит авторитетнее
10. **Stability 0.35-0.40** для YouTube — избегает "AI monotone"
11. **Style Exaggeration 0.2-0.4** — добавляет character без instability
12. **Длинные voice samples** при создании/клонировании голосов — избегает unnaturally fast default pacing

### Production Workflow

13. **Split long scripts на сегменты** — v3 limit 5,000 chars (~5 min). Process в chunks, combine в post
14. **Seed parameter** для reproducibility при итерациях конкретной строки
15. **Layer segments в post-production** для complex compositions
16. **2-3 takes** — модель non-deterministic, генерируй несколько вариантов и выбирай лучший

---

## 8. v3 vs Previous Versions — Key Differences

| Feature | v3 | v2 models |
|---|---|---|
| Audio tags | YES — full inline control | NO |
| SSML `<break>` | NO | YES (up to 3s) |
| SSML phoneme | NO | YES (v2 Flash/Turbo only) |
| Text to Dialogue | YES — dedicated endpoint | NO |
| Languages | 70+ | 29-32 |
| Character limit | 5,000 (~5 min) | 10,000-40,000 |
| Latency | 1-3s | 75-300ms |
| Emotional interpretation | Context-aware — reads subtext | Literal — speaks as written |
| Genre/style/environment tags | YES | NO |

---

## 9. Markup Example — YouTube Narration

```
[documentary style] In the summer of nineteen sixty-nine,
something extraordinary happened. [pause]

Three astronauts climbed aboard a rocket... and the ENTIRE world
held its breath. [dramatic pause]

[excited] The engines ignited with a roar that shook the ground
for miles! [pause]

[calm] But what most people don't know... is what happened
in the minutes BEFORE launch. [whispers] Something almost
went terribly wrong.
```

### Markup conventions для production scripts

В контексте YouTube script production pipeline, audio tags в TELEPROMPTER.md
используются следующим образом:

- `[tag]` — audio tags ElevenLabs v3 (не произносятся, управляют подачей)
- Audio tags **не считаются** как spoken characters при расчёте ElevenLabs billing
- При подсчёте characters для cost estimation — удалять все `[...]` из текста

---

## Sources

- [ElevenLabs Audio Tags](https://elevenlabs.io/blog/v3-audiotags)
- [ElevenLabs Best Practices](https://elevenlabs.io/docs/overview/capabilities/text-to-speech/best-practices)
- [ElevenLabs Models](https://elevenlabs.io/docs/overview/models)
- [ElevenLabs v3 — Emotional Context](https://elevenlabs.io/blog/eleven-v3-audio-tags-expressing-emotional-context-in-speech)
- [ElevenLabs v3 — Precision Delivery Control](https://elevenlabs.io/blog/eleven-v3-audio-tags-precision-delivery-control-for-ai-speech)
- [ElevenLabs v3 — Multi-Character Dialogue](https://elevenlabs.io/blog/eleven-v3-audio-tags-bringing-multi-character-dialogue-to-life)
- [ElevenLabs Text to Dialogue](https://elevenlabs.io/docs/overview/capabilities/text-to-dialogue)
- [ElevenLabs Pronunciation Dictionaries](https://elevenlabs.io/docs/developer-guides/how-to-use-pronunciation-dictionaries)
- [ElevenLabs v3 Launch](https://elevenlabs.io/blog/eleven-v3)
