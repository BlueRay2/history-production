# Knowledge Summary — Istanbul: The Port Between Two Worlds

**Produced by:** Team Lead (Phase 0 — Knowledge Ingestion)
**Date:** 2026-03-25
**Based on:** Paris Part 1 knowledge base (2026-03-07), adapted for Istanbul production

---

## 1. Retention Technique Inventory (from RETENTION_STRATEGY.md)

### Part 1: Starting Hooks (first 5-15 seconds)
| # | Technique | Core Mechanism | Application |
|---|-----------|---------------|-------------|
| 1 | **Synergy (Thumbnail-Title-Hook)** | First words confirm what viewer saw on thumbnail/title | Prevents bait-and-switch; builds instant trust |
| 2 | **Double Hook** | Instant attention grab (shock/visual) + deep value promise | Sells the idea of watching the entire video in first 5s |
| 3 | **In Medias Res** | Start with the most emotionally charged scene/climax | Creates incompleteness effect; viewer watches to understand context |
| 4 | **Curiosity Gap + Hyper-Specificity** | Show impressive result without explaining process; use concrete, recognizable details | Brain can't tolerate information vacuum; specificity creates personal connection |

### Part 2: Mid-Video Retention Triggers
| # | Technique | Core Mechanism | Application |
|---|-----------|---------------|-------------|
| 5 | **Narrative Transportation** | Immerse viewer in story world with clear structure, archetypes, conflict | Reduces critical thinking, increases perceived realism; high-NFC viewers deeply engage |
| 6 | **Zeigarnik Effect (Open Loops)** | Unfinished tasks remembered better than finished ones; plant future reveals | Creates artificial anticipation; never resolve main intrigue too early |
| 7 | **Pattern Interrupt** | Regular visual/audio/narrative shifts every 30-60 seconds | Resets attention via motion bias; prevents habituation |
| 8 | **Kinetic Typography** | Animated text synchronized with speech for key terms/lists | Reduces cognitive load; leverages motion-tracking reflex |

### Part 3: Audio-Physiological Triggers
| # | Technique | Core Mechanism | Application |
|---|-----------|---------------|-------------|
| 9 | **Emotional Contagion** | Automatic emotional sync between viewer and on-screen emotion (voice, music, SFX) | Transforms passive viewing into desire to act, trust, share |
| 10 | **Shepard Tone (Infinity Illusion)** | Audio/visual illusion of endlessly ascending pitch or spiral motion | Creates continuous subconscious tension; prevents relaxation |
| 11 | **J-Cut / L-Cut** | Audio from new scene begins before video (J-cut) or extends past (L-cut) | Seamless, natural transitions; binds sections into unified narrative flow |

---

## 2. ElevenLabs v3 Tag Reference Card

### Emotion & Tone
`[sad]` `[angry]` `[excited]` `[sarcastic]` `[nervous]` `[frustrated]` `[sorrowful]` `[calm]` `[happily]` `[mischievously]` `[curious]`

### Voice Delivery
`[whispering]` / `[whispers]` `[shouting]` / `[shouts]` `[singing]` / `[sings]`

### Non-Verbal Reactions
`[laughs]` `[giggles]` `[snorts]` `[sighs]` `[exhales]` `[clears throat]` `[gulps]` `[yawning]` `[coughing lightly]` `[nervous laugh]` `[crying]`

### Pacing & Delivery
`[pause]` `[short pause]` `[long pause]` `[dramatic pause]` `[rushed]` `[slows down]` `[deliberate]` `[rapid-fire]` `[stammers]` `[drawn out]` `[hesitates]` `[breathes]` `[continues after a beat]`

### Emphasis
`[emphasized]` `[stress on next word]` `[understated]`

### Sound Effects
`[applause]` `[gunshot]` `[explosion]` `[door creaks]` `[footsteps]` `[telephone rings]` `[drumroll]` `[leaves rustling]`

### Narrative Style (useful for this channel)
`[storytelling tone]` `[documentary style]` `[cinematic tone]` `[voice-over style]` `[narrative flourish]`

### Audio Environment
`[city street]` `[rain heavy]` `[forest morning]`

### Key Rules
- Tags in square brackets, placed BEFORE text they modify
- Tags are NOT pronounced, NOT counted as characters for billing
- Combine sparingly: one primary emotion per phrase
- Contradictory tags = bad results
- System is open-ended/generative — model interprets natural language
- SSML `<break>` NOT supported in v3 — use `...` and `[pause]` instead
- CAPITALIZATION = emphasis; `...` = extended pause/weight
- v3 char limit: 5,000 (~5 min); split long scripts into segments

### Recommended YouTube Narration Preset
| Parameter | Value |
|---|---|
| Stability | 0.60-0.80 |
| Similarity | 0.70 |
| Style Exaggeration | 0.20-0.40 |
| Speaker Boost | ON |
| Speed | 0.9-1.0 |

---

## 3. AI Video Generation Prompt Patterns (per model)

### 3.1 Sora 2 Pro
**Prompt formula:** Style Declaration First → Subject → Action → Environment → Camera
**Sweet spot:** 50-200 words
**5 core rules:**
1. One camera move + one subject action per shot
2. Set style declaration first (most powerful lever)
3. Structure prompts in distinct blocks (Style/Grade/Lens/Lighting/Location/Subject/Action/Camera/Palette/Audio)
4. Name concrete visual details, not abstract qualities
5. Keep 50-200 words

**Template blocks:** `[STYLE]` → `[GRADE]` → `[LENS]` → `[LIGHTING]` → `[LOCATION]` → `[SUBJECT]` → `[ACTION]` → `[CAMERA]` → `[PALETTE]` → `[AUDIO]`

**Strengths:** Photorealistic humans, physics (water/smoke/fabric), native audio sync, storyboard mode, Cameo
**Weaknesses:** Expensive, walking gait, text rendering (~5%), multiple speakers, rapid camera, hand details
**Cost:** Pro $200/mo, 10K credits. 1080p 10s = ~600 credits (~$12 priority, $0 relaxed)

### 3.2 Kling AI
**Prompt formula:** Subject+Action → Camera Movement → Environment+Lighting → Style/Texture
**Sweet spot:** 50-80 words (T2V), 20-40 words (I2V)

**CRITICAL: Reversed pan/tilt terminology:**
- Kling "pan" = VERTICAL movement (standard "tilt")
- Kling "tilt" = HORIZONTAL movement (standard "pan")
- For horizontal camera rotation → write `tilt left` / `tilt right`

**Key rules:**
1. Continuous scene descriptions, not keyword lists
2. Describe how shot evolves over time (beginning → end)
3. Name real light sources, not abstractions
4. Texture = credibility (grain, flares, reflections, condensation)
5. I2V recommended for production — describe only motion, never redescribe image

**Versions:** 2.5 Turbo (B-roll) → 3.0 (hero shots) → 2.6 (only for native audio)
**Strengths:** Camera motion control, stylized/abstract, character consistency (Elements), multi-shot 3.0
**Weaknesses:** Reversed terminology, inconsistent face realism, credit-hungry audio
**Cost:** Ultra $180/mo, 26K credits. Professional 10s = 70 credits (~$0.49)

### 3.3 Google Flow (Veo 3.1 / Veo 2)
**Prompt formula:** Cinematography → Subject → Action → Context/Environment → Style & Ambiance
**Sweet spot:** 100-150 words (3-6 sentences)

**Key rules:**
1. Order matters — model prioritizes elements mentioned first
2. Veo 3.1 Fast = 20 cr on Ultra (unlimited iterations)
3. Per-output billing (4 outputs = 4x credits)
4. 8s clip limit; extension = 20 cr each
5. Audio only in Text-to-Video mode (not I2V)
6. Use colon syntax for dialogue (no quotes — triggers subtitles)

**Strengths:** Nature/atmosphere (best), camera control, native audio (Veo 3.1), cheap Fast mode (20 cr), physics
**Weaknesses:** Character consistency across clips, coherence degrades after 2-3 extensions, bland facial expressions, 8s limit
**Cost:** Ultra $249.99/mo, 25K credits. Veo 3.1 Fast = 20 cr (~$0.20). Quality = 100 cr (~$1.00)

### 3.4 Cross-Service Style Line (for visual coherence)

For Istanbul, maintain these style anchors across ALL services:
```
Warm taupe, sandy brown, warm umber, cream white
Shot on 35mm film, shallow depth of field, film grain
Warm golden tones, aged parchment feel, candlelight warmth
Desaturated warmth with golden undertones
```
(Derived from NICHE_STYLE_GUIDE Section 5 — identical across all Cities Evolution productions)

**Istanbul-specific visual notes:**
- Greek Byzantion era: morning light on water, fishing nets, simple stone buildings, Golden Horn harbor
- Byzantine Constantinople era: grand marble, mosaics, Hagia Sophia interior glow, Theodosian Walls, silk market
- Ottoman era: mosque construction, Suleymaniye scaffolding, Grand Bazaar lantern light, ceramic tiles
- Bosphorus (all eras): consistent framing of the strait as visual anchor — same camera angle, different centuries

---

## 4. Cinematographic Shot Type Reference

### Framing
| Type | Coverage | Use Case |
|---|---|---|
| Extreme wide | Full environment, subject tiny | Establishing shots, scale |
| Wide / full shot | Head-to-toe + environment | Scene-setting, spatial context |
| Medium | Waist up | Action, dialogue context |
| Medium close-up | Chest up | Emotional + contextual |
| Close-up | Face fills frame | Emotion, detail |
| Extreme close-up | Single feature (eye, hand, texture) | Texture, macro, drama |

### Angles
| Angle | Effect |
|---|---|
| Eye level | Neutral, natural |
| Low angle | Power, grandeur (looking up) |
| High angle | Vulnerability, overview (looking down) |
| Bird's eye / overhead | Directly above — scale, patterns |
| Dutch angle | Tilted horizon — unease, dynamism |
| Worm's eye | Extreme low, near ground |

### Camera Movements
| Movement | Effect | Best for |
|---|---|---|
| Dolly in/out | Physical forward/backward with parallax | Reveals, tension |
| Pan L/R | Horizontal rotation from fixed position | Surveying, following |
| Tilt up/down | Vertical rotation from fixed position | Reveals, scale |
| Tracking | Follows subject laterally | Following action |
| Crane up/down | Sweeping vertical + horizontal | Grand reveals |
| Handheld | Organic camera shake | Realism, urgency |
| Arc / orbit | Curves around subject | 3D presence |
| Static / locked-off | No movement | Focus on subject action |
| Slow drift | Subtle, barely perceptible | Contemplative |
| FPV drone | First-person flight | Exploration, reveals |

---

## 5. Transition Vocabulary

| Transition | Description | Narrative Use |
|---|---|---|
| **Cut** | Instant switch between shots | Default; maintains energy |
| **Match cut** | Visual/thematic similarity bridges two shots | Thematic connections across eras |
| **J-cut** | Audio from next scene starts before its video | Seamless forward pull; anticipation |
| **L-cut** | Audio from current scene continues over next video | Reflection; lingering emotion |
| **Jump cut** | Same subject, time skip | Passage of time; energy |
| **Dissolve / crossfade** | Gradual blend between shots | Temporal transitions between eras |
| **Smash cut** | Abrupt contrast between scenes | Pattern interrupt; shock |
| **Whip pan** | Fast pan creating motion blur transition | Energy; disorientation |
| **Fade to black / white** | Gradual to solid color | Chapter endings; major time jumps |

**Istanbul-specific application:**
- **Dissolves** for era transitions (Greek Byzantion → Byzantine Constantinople → Ottoman Istanbul)
- **Match cuts** for Bosphorus continuity — same strait framing, different century (key visual motif)
- **Match cuts** for architectural evolution — same location through eras (e.g., site of Hagia Sophia across periods)
- **J-cuts** for voiceover bridging between character transitions (fisherman's era ending, merchant's beginning)
- **Fade to black** between major era transitions for clear temporal separation

---

## 6. Retention Curve Benchmarks

### Key 2026 Benchmarks
- **Average YouTube retention:** 23.7% across all videos
- **Good retention:** 40-60%
- **Top-performing videos (>50% retention):** Only 16.8% of all videos
- **Critical window:** 55% of viewers lost by 60-second mark
- **Consideration window:** ~8 seconds before major drop-off risk
- **Strong 15-second value proposition:** +18% retention at 1-minute mark
- **Channel-wide retention +10pp:** correlates with 25%+ impression increase

### Target Retention Curve for Istanbul (15-17 min)
- **0-30s:** Steep initial drop (expected, unavoidable) — mitigate with Double Hook or In Medias Res (1453 siege or modern fisherman at Galata Bridge as visual anchor)
- **30s-3min:** Stabilization zone — narrative transportation kicks in; introduce fisherman character for emotional anchor
- **3-6min:** Era 1 (Greek Byzantion) — open loop: "What made this fishing village worth conquering?" maintains engagement
- **6-10min:** Era 2 (Byzantine Constantinople) — pattern interrupts via visual spectacle (Hagia Sophia, Theodosian Walls); open loop about 1453
- **10-14min:** Era 3 (Ottoman transformation) — payoff of 1453 open loop; new loop about Grand Bazaar survival
- **14-17min:** Climax (Bosphorus as eternal thread) + conclusion — slight uptick; Part 2 tease potential
- **Target average:** 45-55% (above YouTube benchmark for history content)

---

## 7. AI Service Selection — Decision Matrix Summary

### Temporal Quality Rule ("Premium Start")
- **First ~3 minutes:** PREMIUM models only (Sora 2 Quality / Kling Professional / Flow Veo 3.1 Quality)
- **After ~3 minutes:** ECONOMY models (Flow Veo 3.1 Fast [20 cr, cheapest] > Kling Standard > Sora 2 only for hero human scenes)

### Per-Scene Decision Flow
```
Timestamp < 3 min? → PREMIUM TIER
  Human faces prominent? → Sora 2 Quality
  Complex camera / stylized? → Kling Professional
  Atmospheric / establishing? → Flow Veo 3.1 Quality
  Default → Flow Veo 3.1 Quality

Timestamp >= 3 min? → ECONOMY TIER
  Human faces (hero)? → Sora 2 Quality (exception)
  Complex camera needed? → Kling Standard
  Any other video? → Flow Veo 3.1 Fast (20 cr, cheapest)
  Static overlay / diagram? → Static image
```

### Istanbul-Specific Model Allocation Guidance
- **Fisherman scenes (Era 1, first ~3 min):** Sora 2 Quality for close-ups with human face; Flow Quality for harbor establishing shots
- **Constantinople trade scenes (Era 2):** Flow Fast for architectural shots; Kling Standard for complex camera orbits around buildings
- **Ottoman transformation (Era 3):** Flow Fast for mosque construction; Sora 2 for craftsman hero shot (if budget allows)
- **Bosphorus recurring motif:** Flow Quality/Fast — atmospheric water shots are Flow's strength

### NICHE_STYLE_GUIDE Section 10 Overrides
- Primary model: Google Flow / Veo 3.1
- Secondary: Kling 3, Kling 2.5 Turbo
- Budget profile: Standard (Premium Start + Economy after)

---

## 8. Production Cost Quick Reference

### Video Generation
| Service | Plan | Monthly | Credits | Key Rate |
|---|---|---|---|---|
| Sora 2 Pro | Pro | $200 | 10,000 | 1080p 10s = 600 cr (~$12) |
| Kling AI | Ultra | $180 | 26,000 | Professional 10s = 70 cr (~$0.49) |
| Google Flow | Ultra | $249.99 | 25,000 | Veo 3.1 Fast = 20 cr (~$0.20); Quality = 100 cr (~$1) |

### ElevenLabs Voice
| Plan | Price | Characters |
|---|---|---|
| Creator | $22/mo | 100,000 |
| Pro | $99/mo | 500,000 |

### Estimation Factors
- Average 15-17-min script: ~18,000-22,000 narration characters
- [audio tags] NOT counted as characters
- Waste factor: 1.2x (re-takes)
- Video regen buffer: 25%

---

## 9. Discrepancies / Notes Requiring Attention

1. **Kling subscription pricing** — lower tiers ($6.99-25.99/mo) vs Ultra ($180/mo) used in production. No conflict — different tiers.
2. **Flow Veo 3.1 Fast** — 20 credits per output. Primary iteration and economy B-roll tool.
3. **Content policy blocks on Flow** — Istanbul content includes "siege", "conquest", "fortress", "invasion", "Ottoman army" which may trigger content filters. Mitigation: test in Fast mode (20 cr, cheap), use euphemisms ("the great transformation of 1453", "the city changed hands"), fall back to Kling/Sora for sensitive scenes.
4. **Character consistency across clips** — Istanbul uses 3 named characters (fisherman, merchant, craftsman), each within their own era. No cross-era consistency needed. Within-era consistency: use medium/wide shots to minimize face detail requirements. For fisherman (first 3 min, premium tier), Sora 2 Cameo feature could help. For merchant and craftsman (economy tier), show through action/silhouette rather than facial detail.
5. **Historical sensitivity** — The 1453 siege must be framed as transformation, not destruction. Avoid European-centric "fall of Constantinople" framing. Use "the city's third reinvention" or similar. Prohibited: "exotic", "Oriental", "mysterious East", "discovered by [Europeans]".

---

*End of Knowledge Summary*
