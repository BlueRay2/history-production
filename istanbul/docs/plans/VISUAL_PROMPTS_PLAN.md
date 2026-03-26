# Visual Prompts Plan — Istanbul: The Port Between Two Worlds

**Video:** Istanbul — The Port Between Two Worlds (15-17 min)
**Channel:** Cities Evolution
**Date:** 2026-03-25

---

## 1. Model Selection Strategy ("Premium Start")

### Temporal Quality Rule

The first ~3 minutes of the video (hook + context + Era 1 opening) use PREMIUM models exclusively. After the 3-minute mark, the pipeline shifts to ECONOMY models, with Sora 2 reserved only for hero human shots.

### Premium Tier (0:00 - ~3:00)

| Scene Type | Model | Resolution | Rationale |
|---|---|---|---|
| Human faces/bodies (fisherman close-ups) | **Sora 2 Quality** | 1080p 10s | Best photorealistic humans; Cameo for fisherman consistency |
| Harbor establishing shots, Bosphorus water | **Flow Veo 3.1 Quality** | 1080p 8s | Flow excels at atmospheric water/nature; 100 cr/output |
| Complex camera (crane reveal of Golden Horn) | **Kling Professional** | 1080p 10s | Best camera motion control; 70 cr/10s |
| Default (any other premium scene) | **Flow Veo 3.1 Quality** | 1080p 8s | High quality at reasonable credit cost |

### Economy Tier (~3:00 - end)

| Scene Type | Model | Resolution | Rationale |
|---|---|---|---|
| Hero human shots (merchant key moment, craftsman hero) | **Sora 2 Quality** | 1080p 10s | Exception to economy rule for essential face scenes |
| Complex camera (orbit around Hagia Sophia, Suleymaniye) | **Kling Standard** | 1080p 10s | Camera motion at economy pricing; 10 cr/5s |
| All other footage (B-roll, establishing, architecture, water) | **Flow Veo 3.1 Fast** | 1080p 8s | FREE on Ultra subscription — default economy choice |
| Static overlays / maps / diagrams | **Static image (Imagen 4)** | — | Free on Ultra; add motion in CapCut if needed |

### Fallback Chains

| Primary | Fallback 1 | Fallback 2 | Last Resort |
|---|---|---|---|
| Sora 2 Quality | Kling Professional | Flow Quality | Stock footage |
| Kling Professional/Standard | Flow Quality/Fast | Sora 2 | Stock footage |
| Flow Quality/Fast | Kling Standard | Sora 2 | Stock footage |

**Fallback rules:**
- Switch after 2-3 failed generations (not more)
- Adapt prompt syntax to target service (see Section 5 of video-gen-prompts cross-reference)
- Stock footage is last resort only; prefer AI-generated per channel policy

---

## 2. Visual Continuity Plan

### Cross-Service Style Line

Every prompt across ALL three services must include this style anchor to ensure visual coherence:

```
Warm taupe, sandy brown, warm umber, cream white.
Shot on 35mm film, shallow depth of field, visible film grain.
Warm golden tones, aged parchment feel, candlelight warmth.
Desaturated warmth with golden undertones.
```

This style line is appended as a suffix to every visual prompt, regardless of service. It is the primary mechanism for visual consistency when mixing Sora 2, Kling, and Flow footage in the same video.

### Bosphorus as Recurring Visual Motif

The Bosphorus strait serves as the visual anchor connecting all three eras. To create effective match cuts:

- **Fixed framing angle:** All Bosphorus shots use the same camera position — wide shot from an elevated coastal point, looking across the strait toward the Asian shore, slightly right-of-center composition
- **Time-of-day variation by era:**
  - Greek Byzantion: early morning, soft dawn light on the water, fishing boats
  - Byzantine Constantinople: midday, busy commercial shipping, golden sunlight
  - Ottoman Istanbul: late afternoon/golden hour, mosque silhouettes on the horizon
- **Consistent elements:** Water surface always visible, distant shore always in frame, sky occupying upper third
- **Service assignment:** Flow (Quality for premium, Fast for economy) — atmospheric water is Flow's strongest category

### Era-Specific Palette Adjustments

All within the warm taupe/golden base palette:

| Era | Palette Shift | Lighting Character | Key Textures |
|---|---|---|---|
| **Greek Byzantion** (Era 1) | Cooler morning tones within warm range — more cream, pale gold | Dawn light, soft diffused | Rough stone, fishing nets, weathered wood, salt spray |
| **Byzantine Constantinople** (Era 2) | Richer golden tones — amber, deep gold, purple-gold accents | Interior candlelight, mosaic glow, midday market sun | Marble, silk fabric, gold leaf mosaics, ceramic tile |
| **Ottoman Istanbul** (Era 3) | Warm umber dominance — terracotta, copper, deep brown | Late afternoon sun through arched windows, construction dust in air | Iznik ceramic blue (accent only), carved stone, scaffolding wood, hammered copper |

---

## 3. Shot Diversity Matrix

### Consecutive Clip Variety Rule

**No two consecutive clips may share BOTH the same shot type AND the same camera movement.** At least one axis must change between adjacent clips.

### Rotation Guidelines

#### Shot Type Cycle (rotate through these)
1. Extreme wide / establishing
2. Wide / full shot
3. Medium shot
4. Medium close-up
5. Close-up
6. Extreme close-up (hands, textures, objects)

**Target distribution per era (approx. 10-15 clips):**
- 2-3 wide/establishing shots
- 3-4 medium shots
- 2-3 close-ups
- 1-2 extreme close-ups (texture/detail)
- 1 bird's-eye / overhead (one per era maximum)

#### Camera Movement Cycle (rotate through these)
1. Static / locked-off
2. Slow dolly in
3. Slow dolly out / pull back
4. Pan left or right (note: Kling uses "tilt" for this)
5. Tilt up (note: Kling uses "pan up" for this)
6. Tracking / follow shot
7. Crane up / crane down
8. Orbit / arc shot
9. Slow drift
10. Handheld (sparingly — documentary moments only)

**Target distribution per era:**
- 2-3 static shots (for contemplative/detail moments)
- 2-3 dolly movements (emotional reveals)
- 1-2 crane shots (grand reveals — architecture, city scope)
- 1-2 tracking shots (following character action)
- 1 orbit (architectural showcase — e.g., Hagia Sophia, Suleymaniye)
- Remaining: mix of pan, tilt, slow drift

### Shot Diversity Verification Table

Use this template during prompt writing. Fill in each clip and verify no adjacent rows match on both columns:

```
| Clip # | Shot Type | Camera Movement | Service | Duration |
|--------|-----------|-----------------|---------|----------|
| 01     | Wide      | Crane down      | Flow Q  | 8s       |
| 02     | Close-up  | Static          | Sora 2  | 8s       |
| 03     | Medium    | Dolly in        | Flow Q  | 8s       |
| ...    | ...       | ...             | ...     | ...      |
```

---

## 4. Transition Architecture

### Era Transitions (3 major transitions)

| Transition | From → To | Technique | Audio | Visual |
|---|---|---|---|---|
| **Era 1 → Era 2** | Greek Byzantion → Byzantine Constantinople | **Dissolve** (2-3s) over Bosphorus match cut | J-cut: merchant's market sounds begin 2s before visual transition | Same strait framing, morning → midday, fishing boats → merchant ships |
| **Era 2 → Era 3** | Byzantine Constantinople → Ottoman Istanbul | **Dissolve** (2-3s) through Hagia Sophia interior match cut | J-cut: construction sounds (stone, hammer) begin under final Byzantine narration | Same building, cross → crescent, interior transforms |
| **Climax reveal** | Ottoman era → Timeless Bosphorus | **Slow fade** to wide Bosphorus at golden hour | Music swells, all era motifs interweave | Final wide shot echoes opening angle |

### Within-Era Transitions

| Type | Use Case | Frequency |
|---|---|---|
| **Cut** (default) | Between shots within same scene/moment | 70% of all transitions |
| **Match cut** | Same location across time within era (e.g., harbor at different moments) | 2-3 per era |
| **J-cut** | Voiceover bridges to next visual before image changes | 3-5 per era (natural with voiceover format) |
| **L-cut** | Current visual lingers while next narration segment begins | 1-2 per era (reflective moments) |
| **Jump cut** | Time passage within a character's day | 1 per era maximum |

### Character Transition Pattern

When switching between the narrator's omniscient perspective and a character's intimate perspective:
- **Into character:** J-cut — character-specific ambient sound begins, then visual of character
- **Out of character:** Dissolve or L-cut — character visual fades while narrator widens perspective

### Prohibited Transitions
- Whip pan (too energetic for documentary tone)
- Smash cut (too jarring for this content)
- Wipe (dated/unprofessional for this style)

---

## 5. Footage Duration Standards

| Clip Purpose | Duration | Rationale |
|---|---|---|
| Standard B-roll | **6-8s** | Sweet spot for pacing; matches Flow's 8s base and Sora/Kling 10s |
| Establishing / wide shots | **8-10s** | Needs time for viewer to absorb scale |
| Character close-ups | **5-8s** | Shorter to avoid AI face artifacts becoming visible |
| Texture / detail shots | **5-6s** | Brief emphasis on craftsmanship, materials |
| Transition bridge shots | **5-6s** | Quick connective tissue between major scenes |
| Climax hero shots | **8-10s** | Maximum duration for emotional weight |

**Hard rules:**
- Minimum: 5 seconds (shorter clips feel rushed in documentary format)
- Maximum: 10 seconds (longer clips risk AI temporal coherence issues)
- Default when unspecified: 8 seconds (Flow) or 10 seconds (Sora/Kling)

---

## 6. Clip Segmentation Rule

### Text-to-Clip Mapping

Each visual prompt corresponds to one clip. The mapping rule from narration text to clips:

**Rule A — Long Sentence (15+ words):** 1 clip per sentence
- If a sentence describes a single visual scene, it gets one clip
- If a sentence contains a visual pivot (e.g., "he looked up and the skyline had changed"), it may split into 2 clips

**Rule B — Short Sentence Group (2-3 sentences, <15 words each):** 1 clip per group
- Adjacent short sentences sharing the same visual context are grouped under one clip
- Example: "The nets were mended. The boat was ready. Dawn broke over the harbor." = 1 clip (fishing preparation at dawn)

**Rule C — Purely Narrative/Reflective Passages:** 1 clip per 2-3 sentences
- Abstract narration without specific visual action uses atmospheric B-roll
- Clip changes aligned with sentence boundaries for clean cuts

### Segmentation Verification

After drafting clip assignments, verify:
- [ ] No clip covers more than 10 seconds of narration at normal reading speed
- [ ] No clip covers less than 3 seconds of narration (too short = visual flicker)
- [ ] Every narration sentence has a corresponding visual clip assigned
- [ ] Adjacent clips with same visual content are merged or differentiated

---

## 7. Content Filter Risk Mitigation

### High-Risk Terms for Google Flow

Flow's content filters are the most restrictive. The following terms commonly found in Istanbul's history may trigger blocks:

| Risky Term | Context | Flow-Safe Alternative | OK for Sora/Kling? |
|---|---|---|---|
| "siege" | 1453 siege of Constantinople | "the great transformation", "the final approach" | Yes |
| "conquest" | Ottoman conquest | "the city changed hands", "the transfer of power" | Yes |
| "Ottoman army" | Military context | "Ottoman forces arriving", "columns of soldiers on the march" | Yes |
| "fortress" | Rumeli Hisari | "stone stronghold", "towered fortification on the hillside" | Yes |
| "invasion" | Any military context | "arrival of the new rulers", "the great crossing" | Yes |
| "battle" | Military engagements | "the confrontation", "the decisive moment" | Yes |
| "cannon" / "bombardment" | 1453 artillery | "great machines of bronze", "the thundering approach" | Yes |
| "walls breached" | Theodosian Walls | "the ancient walls gave way", "the barrier opened" | Yes |
| "fall of Constantinople" | 1453 event | "the city's transformation", "Constantinople's third life began" | Yes |

### Mitigation Strategy

1. **Test in Flow Fast first** (free on Ultra) — discover which specific terms trigger filters before committing Quality credits
2. **Maintain dual prompt versions** — a Flow-safe version with euphemisms and a Sora/Kling version with direct historical language
3. **Route sensitive scenes to Sora/Kling by default** — military/siege scenes are better suited to Sora (human subjects) or Kling (motion) anyway
4. **Avoid combining multiple risk terms** — "Ottoman army siege cannon bombardment" will almost certainly trigger; spread terms across separate clips

### Historical Sensitivity Notes (not filter-related)

Per NICHE_STYLE_GUIDE section 9:
- Frame 1453 as transformation, not destruction
- No European-centric "fall of Constantinople" framing
- Use "the city's third reinvention" or similar
- Prohibited: "exotic", "Oriental", "mysterious East", "discovered by [Europeans]"

---

## 8. Character Rendering Strategy

### Fisherman (Greek Byzantion, Era 1 — Premium Tier)

**Model allocation:** Sora 2 Quality (close-ups), Flow Quality (environment around him)

| Shot Type | Rendering Approach | Service |
|---|---|---|
| Close-up (face, hands mending nets) | Full Sora 2 photorealism; consider Cameo for consistency across 3-5 clips | Sora 2 Quality |
| Medium shot (working at harbor) | Sora 2 with detailed character description repeated verbatim across prompts | Sora 2 Quality |
| Wide shot (small figure against Golden Horn) | Flow Quality — fisherman is small in frame, face detail unnecessary | Flow Quality |

**Character description anchor (repeat in every Sora prompt):**
```
A weathered Greek fisherman in his 50s, sun-darkened skin, short gray-flecked beard,
wearing a coarse linen tunic cinched with a rope belt, bare feet, calloused hands.
```

**Cameo consideration:** If Sora 2 Cameo is available (verified likeness recording), use it for the fisherman to ensure consistency across all Era 1 close-ups. This character appears in the premium tier and warrants the investment.

### Merchant (Byzantine Constantinople, Era 2 — Economy Tier)

**Model allocation:** Flow Fast (default), Kling Standard (complex camera), Sora 2 (one hero shot if budget allows)

| Shot Type | Rendering Approach | Service |
|---|---|---|
| Medium shot (in silk market) | Action-defined: show hands examining fabric, profile against market stalls, never front-face close-up | Flow Fast / Kling Standard |
| Wide shot (navigating crowded market) | Merchant is one figure among many; defined by distinctive garment color (deep burgundy robe) | Flow Fast |
| Over-shoulder shot (looking at Hagia Sophia) | Silhouette from behind; no face needed | Flow Fast |
| Hero shot (one key moment) | Medium close-up, 3/4 angle, Sora 2 if budget permits | Sora 2 Quality (exception) |

**Character description anchor:**
```
A Byzantine silk merchant in his 40s, wearing a deep burgundy silk robe with gold trim,
a small leather satchel at his side, dark hair visible beneath a soft cap.
```

**Economy rendering principle:** Show the merchant through his actions (weighing silk, counting coins, negotiating), his distinctive clothing, and his relationship to the environment — not through facial close-ups.

### Craftsman (Ottoman Istanbul, Era 3 — Economy Tier)

**Model allocation:** Flow Fast (default), Kling Standard (workshop detail with camera motion)

| Shot Type | Rendering Approach | Service |
|---|---|---|
| Extreme close-up (hands carving stone, shaping tile) | Hands and tools only — strongest economy approach; no face needed | Flow Fast / Kling Standard |
| Silhouette (against mosque construction scaffolding) | Backlit silhouette at golden hour, identifiable by posture and tools, not face | Flow Fast |
| Medium shot (working in workshop) | Side/back angle, defined by craft activity and environment | Flow Fast |
| Wide shot (small figure on scaffolding against Suleymaniye) | Scale contrast — tiny human vs. grand architecture | Flow Fast |

**Character description anchor:**
```
An Ottoman craftsman in his 30s, wearing a simple cotton tunic and leather apron,
sleeves rolled up, hands covered in stone dust, working beside carved marble blocks.
```

**Economy rendering principle:** The craftsman is defined entirely by his work. Hands shaping stone, silhouette against scaffolding, the curve of his back as he bends over his work. This approach simultaneously avoids AI face artifacts and creates a poetic visual metaphor — the craftsman as an extension of his craft.

---

## 9. Estimated Clip Count

### Per-Section Breakdown

| Section | Timestamp | Duration | Est. Clips | Tier |
|---|---|---|---|---|
| **Cold Hook** | 0:00-0:15 | 15s | 2-3 | Premium |
| **Context & Curiosity Gap** | 0:15-2:00 | 1:45 | 5-7 | Premium |
| **Era 1 — Greek Byzantion** | 2:00-6:00 | 4:00 | 8-12 | Premium (2:00-3:00), Economy (3:00-6:00) |
| **Era 2 — Byzantine Constantinople** | 6:00-10:00 | 4:00 | 8-12 | Economy |
| **Era 3 — Ottoman Istanbul** | 10:00-14:00 | 4:00 | 8-12 | Economy |
| **Climax & Insight** | 14:00-16:00 | 2:00 | 4-6 | Economy + 1-2 hero exceptions |
| **Conclusion & Tease** | 16:00-17:00 | 1:00 | 2-3 | Economy |
| **TOTAL** | — | 15-17 min | **37-55 clips** | — |

### Budget Allocation by Model

| Model | Estimated Clips | Credits per Clip | Total Credits | Est. Cost |
|---|---|---|---|---|
| **Sora 2 Quality** | 5-8 (fisherman CUs + 1-2 hero exceptions) | ~600 | 3,000-4,800 | Within Pro subscription |
| **Kling Professional** | 2-4 (premium tier complex camera) | ~70 | 140-280 | Within Ultra subscription |
| **Kling Standard** | 4-8 (economy complex camera) | ~10-35 | 40-280 | Within Ultra subscription |
| **Flow Veo 3.1 Quality** | 4-6 (premium establishing) | ~100 | 400-600 | Within Ultra subscription |
| **Flow Veo 3.1 Fast** | 20-30 (economy default) | 0 | 0 | FREE |
| **Static images** | 0-2 (maps/diagrams if needed) | 0 | 0 | FREE (Imagen 4) |

### Regeneration Buffer

Apply 25% regeneration buffer to credit-consuming models:
- Sora 2: 3,750-6,000 credits (within 10,000 Pro monthly allocation)
- Kling: 225-700 credits (within 26,000 Ultra monthly allocation)
- Flow Quality: 500-750 credits (within 25,000 Ultra monthly allocation)

### Scene Count Target

**14-18 scenes** total, each containing 2-4 clips. Scenes map to narrative segments (e.g., "Fisherman mending nets at dawn" = 1 scene, 2-3 clips with different framings).

---

## Appendix A: Kling Pan/Tilt Quick Reference

When writing Kling prompts, always translate standard cinematography terms:

| You Want | Write in Kling Prompt |
|---|---|
| Horizontal camera rotation (pan left) | `tilt left` |
| Horizontal camera rotation (pan right) | `tilt right` |
| Vertical camera rotation (tilt up) | `pan up` |
| Vertical camera rotation (tilt down) | `pan down` |

This reversal is Kling's single most common prompting mistake. Always double-check before submitting.

## Appendix B: Service-Specific Prompt Length Targets

| Service | Optimal Length | Format |
|---|---|---|
| Sora 2 | 50-200 words | Structured blocks: Style → Subject → Action → Environment → Camera |
| Kling | 50-80 words (T2V) | Continuous scene description: Subject+Action → Camera → Environment → Style |
| Flow | 100-150 words (3-6 sentences) | Priority order: Cinematography → Subject → Action → Context → Style |

Always include the cross-service style line as a suffix after the service-specific content.
