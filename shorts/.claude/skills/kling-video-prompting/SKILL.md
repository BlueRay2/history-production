---
name: kling-video-prompting
description: Generate production-quality Kling AI video generation prompts optimized for YouTube Shorts (vertical 9:16, ≤60 sec). Use this skill whenever the user mentions Kling AI, asks to create AI video prompts, needs footage generation prompts for Kling, wants cinematic vertical footage, references Kling model versions (1.0–3.0), asks about camera movements for AI video, or needs visual prompts for a YouTube Shorts storyboard. Also trigger when the user mentions text-to-video prompting, image-to-video animation prompts, or AI footage generation.
---

# Kling AI Video Prompting Skill

Generate production-ready prompts for Kling AI (by Kuaishou) — the sole video generation service in this pipeline, optimized for the **Ultra subscription** tier ($180/mo, 26,000 credits).

This skill covers text-to-video, image-to-video, and video extension prompting across Kling model versions 1.6 through 3.0. It is designed for a **YouTube Shorts pipeline** where Kling produces all visual footage (vertical 9:16, ≤60 seconds, no voiceover).

## When to use this skill

- Writing clip prompts in a Shorts storyboard (`**Prompt:**` field in STORYBOARD.md)
- Generating vertical footage for Shorts: hooks, transitions, hero shots, loops
- Planning camera movements and compositions for **9:16 vertical** format
- Optimizing prompt structure for specific Kling model versions
- Estimating credit costs for a batch of Shorts footage on Ultra

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
For abstract, environmental, and conceptual footage where exact composition isn't critical. Secondary mode in this pipeline.

### Image-to-Video (I2V) — Single Frame
Upload a reference frame (from Nano Banana, GPT, or other image generators), then animate with motion instructions. Provides compositional control.

Prompt for I2V: describe **only the motion** — camera movement, subject movement, environmental effects. Never redescribe what's already visible in the image. **20-40 words max.**

### Start/End Frame Control — PRIMARY MODE
**This is the main production mode for Shorts in this pipeline.** Upload first frame and last frame — Kling interpolates between them, creating a realistic transition.

**How it works:**
1. Generate keyframe images in Nano Banana or GPT (detailed static scenes, 9:16 vertical)
2. Upload Start Frame (keyframe N) and End Frame (keyframe N+1) to Kling
3. Kling creates a smooth, realistic transition between the two images
4. Chain transitions: End Frame of scene N = Start Frame of scene N+1

**Prompt for Start/End Frame mode:** describe **only the transition** — what happens between the two frames. Type of transformation, camera movement direction, morphing behavior. **20-40 words.** Do NOT describe the frames themselves — Kling sees them from the uploaded images.

**Best transition types for Start/End Frame:**
| Transition | Description | Best for |
|-----------|-------------|----------|
| **Morphing** | One scene smoothly transforms into another | Transformations, metamorphosis |
| **Camera movement** | Camera moves to reveal new scene | Journeys, reveals |
| **Zoom transition** | Zoom into detail → detail becomes new scene | Escalation, deepening |
| **Time shift** | Same scene, different time/season/era | Contrast, transformation |
| **Dissolve** | Elements dissolve and reform into new scene | Soft transitions, mood |
| **Object-driven** | Object moves and "carries" camera to new scene | Dynamic transitions |
| **Rotation** | Scene rotates to reveal new angle/world | Contrast, surprise |

### Video Extension
Chains 5-second segments up to ~3 minutes. Quality degrades after 30–60 seconds. Use the **last frame** of one generation as the **first frame** of the next for continuity.

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

- **YouTube Shorts (default):** Always use **9:16** — this is the primary format for this pipeline
- **Stability slider:** Use **Creative** or **Natural** for maximum tag responsiveness. **Robust** reduces expressiveness.
- **Always use Professional mode** on Ultra — the quality difference justifies the 3.5× credit premium.

## Vertical 9:16 composition guidelines

Shorts are consumed on mobile in full-screen vertical orientation. This changes prompting fundamentally:

### Framing rules for 9:16
- **Center the subject** — viewers' eyes go to center of vertical frame
- **Use vertical space** — top-to-bottom reveals, falling/rising objects, ascending/descending cameras work great
- **Avoid wide horizontal panning** — `tilt left/right` (horizontal rotation) causes subjects to leave the narrow frame. Prefer `dolly in/out`, `pan up/down` (vertical), `orbit`, `tracking`
- **Close-ups dominate** — the tall narrow frame suits faces, hands, objects better than wide landscapes
- **Stack composition** — foreground element bottom, subject middle, sky/background top

### Best camera movements for 9:16
| Movement | Effect in vertical | Quality |
|----------|-------------------|---------|
| `slow dolly in` / `push in` | Subject grows from center — powerful hook | Excellent |
| `pan up` / `crane up` | Vertical reveal — uses the format's strength | Excellent |
| `pan down` / `descending` | Top-to-bottom reveal | Excellent |
| `orbit shot` | Subject stays centered while background rotates | Good |
| `tracking shot` / `follow` | Following subject through vertical space | Good |
| `dolly out` / `pull back` | Context reveal from detail | Good |
| `tilt left/right` (horizontal pan) | Subject leaves frame fast — use sparingly, slow speed only | Risky |
| `FPV drone` | Impressive but subject tracking is hard in 9:16 | Moderate |

### Vertical prompt suffix
Append to all Shorts prompts for consistent vertical feel:
```
vertical composition, centered subject, 9:16 aspect ratio, mobile-optimized framing
```

## Loop prompting for Shorts

The loop (seamless end→start transition) is the most powerful Shorts technique. How to prompt for it:

### End-state matching
The last clip's ending composition should match the first clip's opening. Describe the end state explicitly:
```
...camera settles on [same framing as opening clip], [same color temperature], [same subject position]
```

### Circular motion loops
Orbit/rotation shots naturally loop:
```
360-degree orbit shot around [subject], completing full rotation, ending at starting angle
```

### Color/lighting loops
Start and end at the same color temperature:
```
...lighting gradually returns to [warm golden / cool blue / etc.] matching the opening
```

## Reference files

For detailed prompt libraries and camera movement reference, read these files:

- `references/CAMERA_REFERENCE.md` — Complete camera motion vocabulary with Kling-specific syntax
- `references/PROMPT_LIBRARY.md` — Production-tested prompt templates by category (cinematic, cyberpunk, documentary, tech/finance, product, abstract)
