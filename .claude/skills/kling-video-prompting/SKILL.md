---
name: kling-video-prompting
description: Generate production-quality Kling AI video generation prompts optimized for cinematic B-roll, YouTube footage, and professional content. Use this skill whenever the user mentions Kling AI, asks to create AI video prompts, needs footage generation prompts for Kling, wants cinematic B-roll descriptions, references Kling model versions (1.0–3.0), asks about camera movements for AI video, or needs visual prompts for a YouTube production script. Also trigger when the user mentions text-to-video prompting, image-to-video animation prompts, or AI footage generation for any content pipeline that includes Kling as a target model.
---

# Kling AI Video Prompting Skill

Generate production-ready prompts for Kling AI (by Kuaishou) — one of the leading AI video generators, optimized for the **Ultra subscription** tier ($180/mo, 26,000 credits).

This skill covers text-to-video, image-to-video, and video extension prompting across Kling model versions 1.6 through 3.0. It is designed for a YouTube production pipeline where Kling serves as the primary or supplementary footage generator.

## When to use this skill

- Writing `Visual` layer prompts in a production script (the `**Prompt:**` field in scene templates)
- Generating B-roll, establishing shots, abstract/conceptual footage, product shots
- Planning camera movements and shot compositions for AI generation
- Optimizing prompt structure for specific Kling model versions
- Estimating credit costs for a batch of footage prompts on Ultra

## Quick start — the universal prompt formula

Every Kling prompt follows this priority structure:

```
Subject + Action → Camera Movement → Environment + Lighting → Style/Texture
```

Write as **continuous scene descriptions**, not keyword lists. Kling generates motion — prompts must describe how the shot evolves over time (beginning → middle → end).

**Word count targets:**
- Text-to-video: **50–80 words**
- Image-to-video: **20–40 words** (motion instructions only — never redescribe the source image)

## Prompt construction workflow

### Step 1: Define the shot

Decide shot type and subject before writing anything:

| Shot type | When to use | Kling strength |
|-----------|------------|----------------|
| Wide/establishing | Scene-setting, environments | Excellent |
| Medium | Action, dialogue context | Good |
| Close-up | Emotion, detail, product | Excellent |
| Extreme close-up | Texture, macro, product ad | Excellent |
| Abstract/conceptual | Data viz, metaphors, tech | Excellent |

### Step 2: Add camera movement

Camera movement is Kling's competitive edge. Always specify movement — without it, output looks static and amateur.

**CRITICAL: Kling reverses standard cinematography terminology:**
- Kling "pan" = vertical movement (standard "tilt")
- Kling "tilt" = horizontal movement (standard "pan")

For horizontal camera rotation, write `tilt left` / `tilt right` in Kling prompts.

Full camera vocabulary → see `references/CAMERA_REFERENCE.md`

### Step 3: Add environment and lighting

Name **real light sources**, not abstract qualities:
- ✅ `neon signs reflecting in wet asphalt`, `golden hour sun through blinds`, `flickering fluorescent tubes`
- ❌ `dramatic lighting`, `cinematic lighting`, `beautiful light`

### Step 4: Add style and texture modifiers

Texture = credibility. Include physical details: grain, lens flares, reflections, condensation, smoke, sweat, rain droplets.

Style modifiers that work well: `shot on 35mm film`, `anamorphic lens flare`, `shallow depth of field`, `bokeh`, `4K`, `cinematic color grade`, `desaturated teal with crushed blacks`.

### Step 5: Add negative prompt (optional)

Use the **dedicated negative prompt field** (not in main prompt). Effective negatives:
```
blur, distorted hands, extra fingers, watermark, text overlay, flickering, morphing faces, unnatural physics, jittery motion
```

Keep negatives simple and specific. Effectiveness is inconsistent — test before relying on them.

## Model version selection

| Version | Best for | Element limit | Notes |
|---------|---------|---------------|-------|
| **1.6** | Simple shots, quick iterations | 3–4 elements | Cheapest per credit |
| **2.1** | Balanced quality/cost | 4–5 elements | Good temporal stability |
| **2.5 Turbo** | Fast batches, B-roll | 5–6 elements | 40% faster, enhanced semantic understanding |
| **2.6** | Audio-visual content | 5–7 elements | Native audio generation (3–5× credit cost) |
| **3.0** | Complex multi-shot scenes | 7+ elements | Multi-shot storyboard, 15s continuous, best physics |

**Rule of thumb:** Start with 2.5 Turbo for B-roll. Use 3.0 for hero shots. Use 2.6 only when native audio is needed.

## Credit costs on Ultra ($180/mo, 26,000 credits)

| Operation | Credits | ~Videos from Ultra pool |
|-----------|---------|------------------------|
| T2V 5s Standard (720p) | 10 | 2,600 |
| T2V 5s Professional (1080p) | 35 | 742 |
| T2V 10s Professional | 70 | 371 |
| T2V 10s Pro + Audio (2.6) | 50–200 | 130–520 |
| Video extend (+5s) | 10–35 | — |
| I2V 5s Professional | 35 | 742 |

**Cost per second (Professional, no audio):** ~$0.049/s
**Cost per second (Professional + audio):** ~$0.07–$0.14/s

Failed generations consume credits with no refund. Budget 15–25% overhead for failures and iterations.

## Generation mode selection

### Text-to-Video (T2V)
Default mode. Best for abstract, environmental, and conceptual footage where exact composition isn't critical.

### Image-to-Video (I2V)
**Recommended for production work.** Upload a reference frame (from Midjourney, Flux, or Kling's own image generator), then animate with motion instructions. Provides far more compositional control and consistency than T2V.

Prompt for I2V: describe **only the motion** — camera movement, subject movement, environmental effects. Never redescribe what's already visible in the image.

### Video Extension
Chains 5-second segments up to ~3 minutes. Quality degrades after 30–60 seconds. Use the **last frame** of one generation as the **first frame** of the next for continuity.

### Start/End Frame Control (Pro feature)
Upload first and last frames — Kling interpolates between them. Excellent for controlled transitions.

## Multi-shot consistency techniques

1. **Elements feature:** Upload up to 4 reference images for character consistency across generations
2. **End-frame chaining:** Use last frame of clip N as first frame of clip N+1
3. **Style line locking:** Copy-paste identical style suffix across all prompts in a batch
4. **Explicit continuity language:** "maintain jersey #11 red throughout", "the same yellow tennis ball"
5. **Kling 3.0 character labels:** Use `[Character A]`, `[Character B]` for identity across up to 6 cuts

## Common failure modes and fixes

| Problem | Cause | Fix |
|---------|-------|-----|
| Garbled output | Too many elements | Reduce to 4–5 nouns max |
| Static/boring output | No camera direction | Always specify movement |
| Content filter rejection | Innocent word triggers | Test words individually to find the trigger |
| Stuck at 99% | Open-ended motion | Add end-state: "then settles back into place" |
| Spatial distortions | Vague positioning | Use precise spatial relationships |
| Poor text rendering | AI limitation | Never generate text in video — add in post |

## Aspect ratio and settings

- **YouTube B-roll:** Always use **16:9**
- **YouTube Shorts / TikTok:** Use **9:16**
- **Instagram:** Use **1:1**
- **Stability slider:** Use **Creative** or **Natural** for maximum tag responsiveness. **Robust** reduces expressiveness.
- **Always use Professional mode** on Ultra — the quality difference justifies the 3.5× credit premium.

## Reference files

For detailed prompt libraries and camera movement reference, read these files:

- `references/CAMERA_REFERENCE.md` — Complete camera motion vocabulary with Kling-specific syntax
- `references/PROMPT_LIBRARY.md` — Production-tested prompt templates by category (cinematic, cyberpunk, documentary, tech/finance, product, abstract)
