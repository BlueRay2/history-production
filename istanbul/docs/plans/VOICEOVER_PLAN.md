# Voiceover Plan — Istanbul: The Port Between Two Worlds

**Video:** Istanbul — The Port Between Two Worlds (15-17 min)
**Channel:** Cities Evolution
**Date:** 2026-03-25

---

## 1. Voice Selection & Settings

### Voice

**Voice:** Patrick International (per NICHE_STYLE_GUIDE section 10)

Patrick International is a warm, authoritative male voice suited for documentary narration. It aligns with the channel archetype: "documentary narrator with empathic focus — calm, confident voice leading the viewer through epochs through the eyes of a specific city inhabitant."

### ElevenLabs Settings

| Parameter | Value | Rationale |
|---|---|---|
| **Model** | `eleven_v3` | Audio tags for emotional control; best expressiveness |
| **Stability** | 0.60-0.80 | Per NICHE_STYLE_GUIDE; avoids monotone while maintaining coherence |
| **Similarity** | 0.70 | Maximum clarity without distortion artifacts |
| **Style Exaggeration** | 0.20-0.40 | Adds character and warmth without instability on long narration |
| **Speaker Boost** | ON | Enhances presence and clarity; ideal for pre-recorded YouTube content |
| **Speed** | 0.9-1.0 | Slightly slower than default for documentary authority; 0.9 for dramatic moments, 1.0 for descriptive passages |

### Settings Adjustments by Section

| Section | Stability | Speed | Rationale |
|---|---|---|---|
| Hook (0:00-0:15) | 0.65 | 0.95 | Slightly more variability for dramatic impact |
| Context/Curiosity (0:15-2:00) | 0.70 | 0.95 | Balanced — informative but engaging |
| Era narratives (2:00-14:00) | 0.70-0.75 | 0.90-0.95 | Steady storytelling pace, warm and consistent |
| Climax (14:00-16:00) | 0.60 | 0.90 | Maximum expressiveness for emotional peak |
| Conclusion (16:00-17:00) | 0.80 | 0.90 | Most stable — calm, reflective, authoritative close |

---

## 2. Emotional Arc Mapping

### Full Arc Overview

```
HOOK ──── CONTEXT ──── ERA 1 ──── ERA 2 ──── ERA 3 ──── CLIMAX ──── CONCLUSION
dramatic   curious     calm/       excited/    majestic/   narrative    calm/
/urgent    /building   intimate    building    reverent    flourish     reflective
                                                          + dramatic
                                                          pause
```

### Section-by-Section Emotional Direction

#### Hook (0:00-0:15)
**Emotion:** Dramatic, urgent — seize attention immediately
**Opening approach options:**
- **In Medias Res (1453):** `[cinematic tone]` Open on the moment of transformation — "The walls had held for a thousand years..." then pull back to promise the full story
- **Curiosity-driven:** `[documentary style]` Open on the Bosphorus as geographic destiny — "There is a narrow strip of water that changed the world..."

**Tag usage:** One primary style tag at the start. Let dramatic punctuation and CAPS do the rest.

**Example emotional texture:**
```
[cinematic tone] There is a narrow strip of water... no wider than a river
in places... that has shaped the fate of EMPIRES. [pause]
```

#### Context & Curiosity Gap (0:15-2:00)
**Emotion:** Curious, building — establish the central question
**Tone:** `[documentary style]` — authoritative but intriguing
**Key delivery:** Contrast between the small ("a fishing village") and the vast ("capital of three civilizations"). Use rising energy to establish the curiosity gap.

**Central question to plant:** "How did a Greek fishing colony become the most fought-over city in human history?"

**Tag usage:** Minimal. `[documentary style]` at opening, then let the writing carry the emotional weight. Use `...` for thoughtful pauses.

#### Era 1 — Greek Byzantion (2:00-6:00)
**Emotion:** Calm, intimate, warm — storytelling mode
**Tone:** `[storytelling tone]` — as if the narrator personally knew the fisherman
**Delivery:** Slow, measured. Morning light feeling in the voice. Gentle.
**Character voice:** When describing the fisherman's actions, voice becomes more intimate and present-tense. When pulling back to historical context, slightly more formal.

**Emotional beats within Era 1:**
1. Introduction of fisherman — `[calm]` `[storytelling tone]` warmth
2. Description of daily routine — natural delivery, no tags needed
3. Harbor and Golden Horn geography — `[documentary style]` brief contextual shift
4. Open loop ("What made this fishing village worth conquering?") — slight rise in energy, no tag, use punctuation

#### Era 2 — Byzantine Constantinople (6:00-10:00)
**Emotion:** Excited, building grandeur — the empire at its height
**Tone:** `[documentary style]` with `[excited]` at key moments
**Delivery:** Faster pace than Era 1. More energy. Bustling markets, the weight of empire.
**Character voice:** The merchant is worldly, confident. Narration reflects this — more assertive delivery.

**Emotional beats within Era 2:**
1. Time transition from Era 1 — brief `[pause]`, then energy shift upward
2. Constantinople's scale reveal — `[excited]` for the visual spectacle (Hagia Sophia, walls)
3. Silk market immersion — natural pacing, sensory details carry the emotion
4. Theodosian Walls / 1453 foreshadowing — `[dramatic pause]` before planting the open loop
5. Open loop payoff setup — tension building, voice drops slightly, `...` for weight

#### Era 3 — Ottoman Istanbul (10:00-14:00)
**Emotion:** Majestic, reverent — transformation, not destruction
**Tone:** `[cinematic tone]` — grand, sweeping, respectful
**Delivery:** Measured pace with moments of awe. The voice conveys reverence for the builders.
**Character voice:** The craftsman is quiet, defined by his work. Narration is observational — watching him rather than speaking for him.

**Emotional beats within Era 3:**
1. 1453 transition — `[cinematic tone]` payoff of the open loop, framed as transformation
2. Ottoman building program — rising energy, scale of construction
3. Craftsman introduction — `[storytelling tone]` return to intimate character focus
4. Suleymaniye Mosque construction — `[cinematic tone]` awe at the architectural ambition
5. Grand Bazaar as living organism — natural delivery, detail-rich description

#### Climax & Insight (14:00-16:00)
**Emotion:** Narrative flourish, dramatic revelation
**Tone:** `[narrative flourish]` leading to `[dramatic pause]`
**Delivery:** This is the emotional peak. The Bosphorus revelation — the same water has fed all three characters, all three civilizations. The voice should build to this insight and then pause to let it land.

**Key technique:** Build-and-release pattern:
```
[narrative flourish] And here is what makes this city unlike any other on Earth...
[dramatic pause]

[calm] The fisherman, the merchant, the craftsman...
they never met. They lived centuries apart.
But every morning... each one of them looked out at the same water.
```

#### Conclusion (16:00-17:00)
**Emotion:** Calm, reflective, open-ended
**Tone:** `[calm]` — settling after the climax
**Delivery:** Slowest pace of the entire video. Reflective. The voice is saying goodbye to these characters.
**Ending:** Leave the viewer with a lingering image and a curiosity gap for future content.

---

## 3. Tag Strategy

### Core Principle: Don't Over-Tag

ElevenLabs v3 is context-aware — it reads subtext and adjusts delivery based on the writing itself. Tags should be used only where the natural reading would miss the intended emotion.

### When to Use Tags

| Situation | Use Tag? | Example |
|---|---|---|
| Opening of a new section/era | **Yes** — set the tonal register | `[storytelling tone]` His name is lost to history... |
| Emotional shift within a section | **Yes** — if the text alone doesn't signal the change | `[excited]` But THIS was no ordinary market... |
| Dramatic pause before revelation | **Yes** — `[dramatic pause]` or `[pause]` | `[dramatic pause]` And then... everything changed. |
| Standard narration with clear emotional context | **No** — let the writing work | "The harbor was quiet. Nets hung drying in the morning sun." |
| Descriptive passages about architecture/geography | **No** — documentary delivery is the default | "The walls stretched for six kilometers..." |
| Moments requiring whispered intimacy | **Yes** — only way to signal this | `[whispers]` He never saw the city change. |

### Tag Frequency Guidelines

- **Maximum:** 1 tag per paragraph (every 3-5 sentences)
- **Minimum:** 1 tag per era transition (to reset tonal register)
- **Average across full script:** ~15-25 tags total for 15-17 minutes
- **Never stack more than 2 tags** in sequence (e.g., `[calm][storytelling tone]` is maximum)
- **Contradictory tags are forbidden** (e.g., `[excited][whispers]` = bad result)

### Recommended Tag Palette for This Video

Primary narrative tags (from NICHE_STYLE_GUIDE section 10):
- `[storytelling tone]` — character-focused intimate passages
- `[documentary style]` — factual/contextual information
- `[cinematic tone]` — grand visual moments, era transitions
- `[voice-over style]` — neutral narration bridges
- `[narrative flourish]` — climax and dramatic revelations

Supporting tags:
- `[calm]` — Era 1 fisherman, conclusion
- `[excited]` — Era 2 grandeur moments
- `[pause]` / `[dramatic pause]` — before revelations and era transitions
- `[whispers]` — one or two intimate moments only (sparingly)

Tags NOT to use in this video:
- `[angry]`, `[frustrated]`, `[sarcastic]` — wrong tone for documentary
- `[laughs]`, `[giggles]` — wrong genre
- `[shouting]` — too aggressive for this content
- Sound effect tags (`[explosion]`, `[gunshot]`) — use music/SFX in post instead

---

## 4. Pacing Strategy

### Base Pace

**Medium-slow** — documentary authority. Speed setting 0.90-0.95 as default. This is ~130-140 words per minute (standard documentary narration: 130-150 WPM).

### Pacing Variations

| Moment | Pace | Technique |
|---|---|---|
| **Hook** | Medium-fast → sudden slow | Start with momentum, then `[dramatic pause]` to create contrast |
| **Context/Curiosity** | Medium | Steady, informative, building |
| **Era introductions** | Slow | `...` pauses before character introduction; let the era breathe |
| **Action/description passages** | Medium | Natural flow, no special treatment |
| **Open loop plants** | Medium → slow | Decelerate as the question is planted; end with `...` |
| **Era transitions** | Very slow → pause → medium | `[dramatic pause]` between eras; new era starts at medium pace |
| **Climax build** | Accelerating | Sentences get shorter, pace quickens, building to revelation |
| **Climax revelation** | Sudden slow | `[dramatic pause]` then very slow delivery of the key insight |
| **Conclusion** | Slowest | Speed 0.90, long pauses, reflective |

### Punctuation as Pacing Control

| Tool | Effect | When to Use |
|---|---|---|
| `...` (ellipsis) | Extended pause, hesitation, weight, trailing off | Before revelations, between eras, when planting open loops |
| `--` (double dash) | Abrupt pause, interruption, topic shift | Mid-sentence pivots, dramatic interruptions |
| CAPS | Vocal emphasis and stress | Key words only: "This changed EVERYTHING", "THREE civilizations" |
| `!` | Increased energy | Sparingly — 2-3 per era maximum; documentary tone should rarely shout |
| `?` | Natural upward inflection | Rhetorical questions for curiosity gaps |
| Short sentences. | Punchy rhythm. Impact. | Climax moments, dramatic revelations |

### Pacing Example (Era Transition)

```
[storytelling tone] ...and the fisherman's world — small, quiet, bounded by the
harbor and the morning tide — continued as it always had. [pause]

He never knew that his village sat on the most valuable strip of water
on Earth. [dramatic pause]

...

[documentary style] Seven centuries later, that same harbor would serve
a city of half a million people.
```

---

## 5. Music Cue Design

### Overall Music Philosophy

Music is a supporting layer, never competing with narration. Volume should sit 10-15 dB below voice. Music establishes era-appropriate atmosphere and provides emotional undercurrent.

### Era-Specific Music Design

#### Era 1 — Greek Byzantion (2:00-6:00)
| Element | Description |
|---|---|
| **Lead instrument** | Solo lyre or oud — single string instrument, intimate |
| **Texture** | Sparse, contemplative, slightly melancholic |
| **Tempo** | Slow, breathing, 60-70 BPM |
| **Ambient SFX** | Harbor sounds: gentle waves lapping, distant seabirds, rope creaking, wooden hull groaning, fish splashing in nets |
| **Feel** | Early morning solitude; a man alone with the sea |

#### Era 2 — Byzantine Constantinople (6:00-10:00)
| Element | Description |
|---|---|
| **Lead instruments** | Orchestral swell — strings section, possible Byzantine chant influence (wordless choir) |
| **Texture** | Rich, layered, building complexity — reflecting the empire's grandeur |
| **Tempo** | Medium, processional, 80-100 BPM |
| **Ambient SFX** | Market bustle: merchants calling, coins clinking, fabric rustling, footsteps on stone, distant church bells |
| **Feel** | The weight of empire; opulence and ceremony |

#### Era 3 — Ottoman Istanbul (10:00-14:00)
| Element | Description |
|---|---|
| **Lead instruments** | Ottoman classical: ney (reed flute) for contemplative passages, kanun (zither) for descriptive passages |
| **Texture** | Warm, resonant, meditative — handcrafted sound matching handcrafted visuals |
| **Tempo** | Medium-slow, deliberate, 70-85 BPM |
| **Ambient SFX** | Construction sounds: stone being cut, hammer on chisel, scaffolding creaking, water from nearby fountain, muezzin call in the distance (if appropriate) |
| **Feel** | Patient creation; reverence for the act of building |

#### Climax (14:00-16:00)
| Element | Description |
|---|---|
| **Lead instruments** | Full orchestral — all eras' motifs woven together (lyre melody + choir + ney) |
| **Texture** | Crescendo build → held note → silence → resolution |
| **Tempo** | Building from 70 to 100+ BPM, then sudden drop |
| **Ambient SFX** | Water sounds from the Bosphorus — the unifying element |
| **Feel** | The revelation: three eras, one body of water, one city |

#### Conclusion (16:00-17:00)
| Element | Description |
|---|---|
| **Lead instruments** | Return to solo string instrument (echo of Era 1 lyre), but richer |
| **Texture** | Sparse, reflective, gentle resolution |
| **Tempo** | Very slow, 55-65 BPM, decelerating |
| **Ambient SFX** | Distant water, a single seabird, city hum fading |
| **Feel** | Coming full circle; peace after grandeur |

### Transition Music Cues

| Transition | Music Treatment |
|---|---|
| **Hook → Context** | Music enters softly under hook's final words; establishes base theme |
| **Context → Era 1** | Brief silence beat (1-2s of no music), then Era 1 lyre enters |
| **Era 1 → Era 2** | Lyre fades, 2-3s silence, orchestral swell enters under J-cut |
| **Era 2 → Era 3** | Choir holds a single note, crossfades into ney solo |
| **Era 3 → Climax** | Ottoman instruments gradually joined by strings and choir; continuous build |
| **Climax → Conclusion** | Full orchestra drops away, leaving single string instrument |
| **Conclusion → End** | Music fades to silence over final 15-20 seconds |

### Music Source Recommendations

- **Royalty-free libraries:** Epidemic Sound, Artlist (both have period-appropriate collections)
- **AI music generation:** Udio or Suno for custom era-specific cues if library options feel generic
- **Avoid:** Overly recognizable Middle Eastern music cliches; aim for authenticity not stereotype

---

## 6. Segment Splitting Strategy

### ElevenLabs v3 Constraints

- **Character limit:** 5,000 characters per segment (~5 minutes of narration at standard pace)
- **Audio tags** are NOT counted toward the character limit
- **Estimated total narration:** 15-17 minutes = ~18,000-22,000 characters (at ~130-140 WPM, ~1,200-1,300 chars/min)
- **Waste factor:** 1.2x for re-takes = ~21,600-26,400 effective characters needed

### Segment Division

Target: **4-5 segments** of ~4,000-4,500 characters each (staying under 5,000 limit with buffer).

| Segment | Content | Approx. Duration | Est. Characters | Split Point |
|---|---|---|---|---|
| **Segment 1** | Hook + Context + Era 1 (first half) | ~3.5 min | ~4,200 | Split at a natural pause in Era 1 narrative |
| **Segment 2** | Era 1 (second half) + Era 1→2 transition | ~3.5 min | ~4,200 | Split at Era 2 opening (after transition beat) |
| **Segment 3** | Era 2 (full) | ~4.0 min | ~4,800 | Split at Era 2→3 transition |
| **Segment 4** | Era 3 (full) | ~4.0 min | ~4,800 | Split at Era 3→Climax transition |
| **Segment 5** | Climax + Conclusion | ~2.0-3.0 min | ~2,400-3,600 | End of video |

### Splitting Rules

1. **Always split at paragraph boundaries** — never mid-sentence or mid-paragraph
2. **Prefer splitting at era transitions** — natural tonal resets align with segment boundaries
3. **Include 1-2 sentences of overlap context** — the last sentence of segment N can be repeated at the start of segment N+1 to help ElevenLabs maintain tonal continuity (delete the duplicate in post)
4. **Tag reset at segment start** — each segment should begin with a narrative style tag (`[documentary style]`, `[storytelling tone]`, etc.) to re-establish tone, since v3 has no memory across API calls
5. **Keep climax in one segment** — do not split the climax revelation across segments; the emotional build needs continuous context
6. **Character count verification** — count characters EXCLUDING audio tags `[...]` before confirming segment length

### Post-Production Assembly

1. Generate each segment as a separate audio file
2. Import all segments into CapCut timeline
3. Trim overlap sentences from the segment boundaries
4. Crossfade 50-100ms between segments for seamless joins
5. Verify timing against visual clips — adjust speed in CapCut if any segment runs long/short
6. Generate 2-3 takes per segment; select best take for each

### ElevenLabs Cost Estimate

| Plan | Characters Included | Script Characters (with waste) | Sufficient? |
|---|---|---|---|
| Creator ($22/mo) | 100,000 | ~24,000 | Yes — ~4 videos per month |
| Pro ($99/mo) | 500,000 | ~24,000 | Yes — ~20 videos per month |

Recommended: **Creator plan** is sufficient for 2-4 videos per month at this script length.
