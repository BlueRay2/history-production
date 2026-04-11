# Конкуренты — топ-7 англоязычных каналов deep-history

**Источник:** consensus run 2026-04-11, research фазы Claude / Codex / Gemini + web search 2025-2026.
**Ограничение:** только англоязычные каналы (по указанию Ярослава). Русскоязычные конкуренты не исследовались.
**Назначение:** reverse-engineering приёмов для копирования в production history-production.

## Краткая сводка — роль каждого конкурента для нас

| Канал | Подписчики | Подходит нам как | Замечания |
|---|---|---|---|
| **Kings and Generals** | ~4.1M | Stake-framing + бимодальный safe tone | Не копировать медленный ритуальный ramp |
| **Historia Civilis** | ~1.1M | Thesis-first opening line | Square-man анимация не копируется |
| **Tasting History** | ~2.7M | "Familiar → overturn" шаблон | НЕ копируем — зависит от личности Max'а |
| **OverSimplified** | ~10.5M | Velocity + компрессия | НЕ копируем комедию — высокий риск для 45-64 |
| **Real Engineering** | ~4.1M | Mechanism-led curiosity + "textbook vs reality" reveal | Высокая совместимость, близко к нам |
| **Tom Scott** | ~6.3M | Place-grounded immediate question | Не копируем персоналити; копируем структуру |
| **Voices of the Past** | ~1.8M | **Стилистическая модель primary-source beats** | Наш ближайший production-twin по формату |

(Подписчики — приблизительные оценки на основе открытых источников 2025-2026; точность ±10%.)

---

## 1. Kings and Generals (KnG)

**Ниша:** военная история, битвы, кампании, стратегия.

**Формат:** 10-30 мин видео, 2D анимация с картами и перемещением войск, глубокий голос, драматический нарратив.

**Видимый CTR:** устойчивый для их топ-видео (оценочно 6-10% по нашим признакам виральности; точных цифр нет).

**AVD pattern:** высокий для их ниши — ценят факт-плотность и карту-анимацию, которые держат внимание через визуальное отслеживание.

**Стиль превью (3-5 правил):**
1. Дух «древний манускрипт/фреска» — сепия, охра, бронза, иногда красные акценты.
2. Одна-две исторические фигуры + карта или символ сражения.
3. Заголовок в нижней/верхней части, крупный serif шрифт, 2-5 слов.
4. Тёплые тона, низкая насыщенность, высокий contrast.
5. Часто без эмоциональных «кричащих» лиц; сдержанно, почти документально.

**Стиль хука (первые 60 сек):**
- 0:00-0:15 — установочный кадр и определение масштаба («An empire at its height...»).
- 0:15-0:45 — «However...» — появление угрозы / противника.
- 0:45-1:00 — стейкинг: что будет потеряно / что на кону.

**Что у них работает чего нет у других:** авторитетный голос + macro-strategic clarity. Они не торопятся, но каждая секунда служит введению в strategic problem.

**Что мы можем украсть:**
- Stake-framing в 0:15-0:30 («empires fought over this city for 1,000 years»).
- Сдержанный тёплый палитрный стиль превью (авторское впечатление серьёзности).
- Сюжет через **проблему**, а не через хронологию.

**Что НЕ копируем:**
- Медленный ceremonial ramp первых 20 секунд — мы не можем его позволить (у нас 99.5% новых viewer'ов, а у них лояльная база).
- Square-war-game анимации — не подходит city-history.

---

## 2. Historia Civilis

**Ниша:** Античность (Рим, Греция), отдельные эпизоды 19 века.

**Формат:** 10-25 мин, минималистичная анимация с цветными квадратами (Sullivan-style), формальный voiceover, без музыкальной экзальтации.

**Видимый CTR:** высокий для образовательной ниши, их thesis-first openings собирают вирусные pickups.

**AVD pattern:** очень высокий — их ценят за intellectual density; viewers watch till end.

**Стиль превью:**
1. Минимализм, square-man стилистика как signature.
2. Жёлтое/оранжевое на тёмном фоне.
3. 1-2 слова заголовка.
4. Никаких лиц — только абстракция.
5. Очень узнаваемая branding.

**Стиль хука:**
- 0:00-0:20 — тесис-first statement, часто провокационный («We work too much.»).
- 0:20-0:50 — раскрытие, что статiment означает.
- 0:50-1:00 — title card.

**Что работает:** thesis-first opening как один из самых эффективных способов мгновенно задать конфликт (viewer должен узнать, почему тесис True).

**Что украсть:**
- **Thesis-first opening line** как обязательный приём для hook'а. Примеры для нас: «Cities do not become great by accident», «This city survived by changing what it was».
- Сдержанный, формальный voiceover.

**Что НЕ копируем:**
- Square-man стилистику (уникальная IP).
- Сверхмедленное начало (мы не можем себе позволить).

---

## 3. Tasting History with Max Miller

**Ниша:** исторические рецепты + история через кулинарный объект.

**Формат:** 15-25 мин, Max на камеру, разделено на «cook» и «Time for History» сегменты.

**Видимый CTR:** очень хороший; их topic idea unique.

**AVD pattern:** сильный — сегментированная структура держит внимание через смену регистров.

**Стиль превью:**
1. Max в кадре с едой/блюдом.
2. Тёплые тона, food photography aesthetic.
3. 2-4 слова заголовка.
4. Центральный focal point — еда или Max.
5. Часто один объект в крупном плане.

**Стиль хука:**
- 0:00-0:15 — «Today we are making...» + визуал ингредиента.
- 0:15-0:45 — исторический якорь (к какой эпохе/моменту привязана еда).
- 0:45-1:00 — обещание execution.

**Что работает:** personal authority + concrete sensory object. Low-friction entry, viewer сразу чувствует «что будет происходить».

**Что украсть:**
- **«Familiar reference → overturn» паттерн** — открыть с чего-то знакомого о городе, немедленно перевернуть. Пример: «Everyone thinks Quanzhou is a small Chinese port town. In 1271 it was the largest port in the world.»

**Что НЕ копируем:**
- Всё, что зависит от persona / face-on-camera. У нас нет presenter.
- Cooking / demo элементы.

---

## 4. OverSimplified

**Ниша:** упрощённая история с юмором (войны, революции, большие события).

**Формат:** 15-45 мин, stick-figure анимация, юмористический narrator (один голос для всех персонажей).

**Видимый CTR:** виральный (часто 8-15%+) благодаря thumbnail'ам с экспрессивной stick-анимацией и заголовкам с юмором.

**AVD pattern:** выдающийся — 70% retention от part 1 к part 2 на 20+ мин видео.

**Стиль превью:**
1. Stick-figure персонажи с экспрессивными лицами.
2. Яркие насыщенные цвета, высокий contrast.
3. 2-4 слова заголовка.
4. Узнаваемый «мультяшный» стиль.
5. Композиция часто action-пригружена.

**Стиль хука:**
- 0:00-0:20 — sight gag в stick-animation стиле.
- 0:20-0:45 — эскалация абсурда.
- 0:45-1:00 — «а потом умерли миллионы» с контрастом к мультяшке.

**Что работает:** velocity + humor-driven compression + бренд узнаваемости.

**Что украсть:**
- **Velocity** (плотность информации в первые 60 секунд). Не темп монтажа, а плотность фактов.
- **Rapid stakes escalation** — каждые 45 секунд следующая стадия («они поссорились» → «город горит» → «империя рушится»).

**Что НЕ копируем:**
- Юмор. Он не совместим с нашим тоном и отталкивает Persona B.
- Stick-figure стилистику.
- «Абсурдистскую редукцию».

---

## 5. Real Engineering

**Ниша:** инженерия, технологии, военная и аэрокосмическая история через техническую призму.

**Формат:** 10-20 мин, narrator + 3D/2D graphics + B-roll, академичная подача.

**Видимый CTR:** сильный — их «contrarian claim» thumbnail pattern работает.

**AVD pattern:** высокий — смещение к System-2 engagement держит educated audience.

**Стиль превью:**
1. Один объект (самолёт / деталь / чертёж) + технический callout.
2. Контрастный цвет + тёмный фон.
3. 2-4 слова заголовка, часто с числом.
4. Очень «engineering journal» aesthetic.
5. Почти никогда не face-based.

**Стиль хука:**
- 0:00-0:20 — общепринятое «фактическое» утверждение.
- 0:20-0:50 — teardown: почему это утверждение неверно с точки зрения физики/инженерии.
- 0:50-1:00 — обещание «here is how it actually worked».

**Что работает:** **mechanism-led curiosity** — "textbook vs reality" reveal. Мгновенно вовлекает System 2, удерживает audience с high education.

**Что украсть (очень много):**
- **«Textbook vs reality» reveal** как центральный приём. Примеры: «The textbook says Quanzhou was a Chinese port. The primary sources say it was a city where nobody was truly native.»
- Clean, mechanism-focused narrator tone.
- Face-free thumbnails с одним объектом.

**Что НЕ копируем:**
- Hard engineering focus — не наша ниша.

---

## 6. Tom Scott

**Ниша:** bite-size образование, места, странные факты, geography, tech.

**Формат:** 4-7 мин, Tom один в кадре, чаще на локации, один непрерывный дубль.

**Видимый CTR:** стабильно отличный, простые thumbnails с Tom'ом в месте.

**AVD pattern:** высокий благодаря брошенным интро, zero fluff, прямому движению к ответу.

**Стиль превью:**
1. Tom в кадре + узнаваемое место.
2. Красная футболка = brand consistency.
3. 3-5 слов заголовка, часто в вопросительной форме.
4. Минимум текста поверх.
5. Composition — single focal point (Tom).

**Стиль хука:**
- 0:00-0:10 — «I'm standing in [Location]...» — physical presence credibility.
- 0:10-0:30 — «...and behind me is [Something mundane]».
- 0:30-1:00 — revelation почему mundane thing на самом деле important / dangerous / historic.

**Что работает:** zero intro tax, place-grounded credibility, сразу к сути.

**Что украсть:**
- **Place-grounded immediate question** — «Here is the thing that makes this city strange...» Открыть с конкретного визуального места + немедленно артикулировать почему это странно.
- Zero intro tax principle.
- Ощущение «on-the-ground documentary» — у нас достигаем через grounded AI footage.

**Что НЕ копируем:**
- Tom as persona — мы без presenter.
- Короткую длину (мы long-form).

---

## 7. Voices of the Past (VotP) — наш production-twin

**Ниша:** primary-source driven history — чтение первоисточников с атмосферными визуалами.

**Формат:** 15-40 мин, voiceover + ambient historical visuals + soundtrack, никакого presenter.

**Видимый CTR:** средний-высокий, их thumbnails обманчиво простые.

**AVD pattern:** экстремально высокий — viewers buy into the primary-source reading и смотрят до конца.

**Стиль превью:**
1. Крупный исторический image (портрет / картина / текст).
2. Тёплая палитра, often сепия.
3. 3-5 слов заголовка, часто с quote.
4. Minimalist composition.
5. Atmosphere > information.

**Стиль хука:**
- 0:00-0:40 — нет intro. Сразу начинается чтение primary source / eyewitness account (часто outsider perspective: римлянин описывает варвара, японский монах описывает европейца).
- 0:40-1:00 — contextualization: кто говорит, когда, при каких обстоятельствах.

**Что работает:** primary-source immersion — обходит «history lesson» filter, бросает viewer сразу в human narrative.

**Что украсть (максимально):**
- **Primary source immersion** как opening device для отдельных видео где source strong.
- **Ambient visuals + voiceover** — это буквально наша production модель. Мы делаем то же самое.
- **Outsider-perspective hook** — особенно мощно для Quanzhou (персидский купец, арабский путешественник, итальянский миссионер описывают Quanzhou).
- Atmospheric музыкальное sound design.

**Что НЕ копируем буквально:**
- Primary-source-as-full-format — нам нужен narrative scaffold вокруг sources.
- Полное отсутствие нарратора-проводника — у нас narrator более активный.

---

## Cross-channel patterns — что общего у всех 7 у первых 60 секунд

По Codex R1: сильные первые минуты у всех семи делают **четыре вещи быстро**:
1. Установить **конкретный образ**.
2. Обозначить **напряжение / парадокс**.
3. Намекнуть на **скрытый механизм**.
4. Обещать **удовлетворяющее объяснение**.

Слабые первые минуты:
- Начинают с общего overview.
- Перефразируют заголовок.
- Тратят время на «welcome back».
- Frontload chronology до stakes.

---

## Что мы можем украсть — консолидированный список для history-production

### Обязательно (Tier 1 — внедрить немедленно)

1. **Thesis-first opening line** (от Historia Civilis)
2. **Stake-framing 0:15-0:30** (от Kings and Generals)
3. **«Textbook vs reality» reveal** (от Real Engineering)
4. **Place-grounded immediate question** (от Tom Scott)
5. **Primary source immersion на 4-5 минуте + 10-12** (от Voices of the Past)
6. **Single dominant subject thumbnail** (от VotP + Real Engineering)

### Желательно (Tier 2)

1. **Familiar-reference → overturn** (от Tasting History) — для хорошо известных городов
2. **Rapid stakes escalation каждые 45 сек** (velocity от OverSimplified)
3. **Warm palette thumbnail consistency** (от Kings and Generals)

### НЕ копировать (Tier 0)

1. **Юмор и comedic tone** (OverSimplified).
2. **Personality-driven formats** (Tasting History, Tom Scott).
3. **Уникальные визуальные IP** (square-man Historia Civilis, stick figures OverSimplified).
4. **Медленные ceremonial ramps** (Kings and Generals) — не можем позволить.
5. **Screaming / shock face thumbnails** — отталкивают нашу Persona B.

---

## Наш production-compatible стиль (итог)

Мы находимся в пересечении **Voices of the Past** (атмосфера, primary sources, voiceover + ambient) и **Real Engineering** (mechanism curiosity, textbook vs reality) с **Kings and Generals** stake-framing. Это **наша триада**. Тон — serious, authoritative, но density-rich; pace — medium-fast (145-160 wpm narration); первый минут — thesis + stake + mechanism promise, не chronology.

**Anti-identity** (явно не мы): OverSimplified, Tasting History, Tom Scott personality model.
