---
name: google-flow-prompting
description: >
  Write professional AI video generation prompts for Google Flow (powered by Veo 3.1/Veo 2).
  Use this skill whenever the user needs to create footage prompts, video generation prompts,
  visual scene descriptions, or B-roll prompts targeting Google Flow or Veo models. Also trigger
  when the user mentions "Flow", "Veo", "Google video generation", "footage prompt", "AI footage",
  or asks to generate cinematic scene descriptions for AI video tools. Covers the full prompting
  formula (cinematography + subject + action + context + style), camera movement vocabulary,
  lighting descriptors, audio prompting for Veo 3.1, credit optimization on Google AI Ultra,
  and known model strengths/weaknesses from community production testing. Essential for any
  YouTube production workflow that uses Google Flow for B-roll, establishing shots, or
  narrative footage generation.
---

# Google Flow Footage Prompting Skill

This skill enables Claude to write production-quality video generation prompts
for Google Flow (Veo 3.1 / Veo 2) within a YouTube content production pipeline.

## When to Read Reference Files

Before writing any prompts, read the relevant reference files:

- **Always read first:** `references/PROMPT_FORMULA.md` — the five-part prompt
  structure, camera/lighting/style keyword inventories, audio prompting syntax,
  and negative prompting patterns. This is the core technical reference.
- **Read for budget planning:** `references/ULTRA_PRICING.md` — credit costs per
  generation on Google AI Ultra, iteration strategies, and cost optimization.
- **Read for model selection:** `references/COMMUNITY_INSIGHTS.md` — community-tested
  strengths/weaknesses per footage type, failure modes, and multi-tool workflow
  recommendations (when to use Flow vs Sora vs Kling vs Runway).

## Core Prompt Architecture

Every Flow prompt follows a five-part formula. Order matters — the model
prioritizes elements mentioned first.

```
[Cinematography] + [Subject] + [Action] + [Context/Environment] + [Style & Ambiance]
```

**Target length:** 3–6 sentences (100–150 words). Shorter prompts produce
generic output; longer prompts cause coherence failures.

**Example:**
```
Crane shot starting low on a lone hiker and ascending high above,
revealing they are standing on the edge of a colossal, mist-filled
canyon at sunrise. The hiker wears a weathered orange jacket and
carries a heavy backpack. Wind gently moves their hair and the tall
grass around them. Epic nature documentary style, awe-inspiring scale,
soft golden morning light with volumetric god rays cutting through
the mist.
```

## Model Selection Matrix

Choose the model based on footage type and production phase:

| Phase / Need | Model | Credits (Ultra) | Rationale |
|---|---|---|---|
| Prompt iteration & drafts | Veo 3.1 Fast | **0** (Included on Ultra) | Unlimited iterations at no cost |
| Final hero footage | Veo 3.1 Quality | **100** per output | Full resolution, native audio |
| Legacy footage (no audio needed) | Veo 2 Quality | **100** per output | Stable, proven |
| Quick volume B-roll | Veo 2 Fast | **10** per output | Cheapest non-free option |
| Image-to-video remixing | Whisk Veo 3 Fast | **20** per output | Creative remixing from reference images |
| Video edits (extend/insert/remove) | — | **20** per edit | Post-generation refinement |

**Critical:** Credit cost is *per output*, not per request. Generating 4 outputs
from one prompt = 4× the listed credit cost. Always generate 1 output during
iteration, then scale to 2–4 for final selection.

## Prompt Writing Workflow

Follow this sequence for each clip that requires Flow footage:

### Step 1: Determine shot requirements from the script

Extract from the scene specification:
- Shot type (wide / medium / close-up / extreme CU)
- Camera movement (static / pan / tilt / dolly / crane / handheld)
- Subject and action
- Emotional tone and atmosphere
- Duration needed (4s / 6s / 8s — Flow generates in these increments)
- Whether audio is needed (dialogue, SFX, ambient)

### Step 2: Check the model strength matrix

Consult `references/COMMUNITY_INSIGHTS.md` to verify Flow is the right
tool for this footage type. If the scene requires:
- **Character consistency across clips** → Runway Gen-4 is stronger
- **Hyper-realistic human close-ups** → Sora 2 is stronger
- **Abstract/stylized motion graphics** → Runway Gen-4 is stronger
- **Nature, atmosphere, establishing shots** → Flow excels — proceed
- **Product shots, tech footage** → Flow excels — proceed
- **Water, fire, smoke VFX** → Flow excels — proceed

### Step 3: Write the prompt using the five-part formula

Construct the prompt following the order in `references/PROMPT_FORMULA.md`:

1. **Cinematography** — camera angle, movement, lens
2. **Subject** — who/what, described with visual specificity
3. **Action** — what is happening, described with motion verbs
4. **Context** — environment, time of day, weather, setting
5. **Style & Ambiance** — film style, lighting, color palette, mood

### Step 4: Add audio layer (Veo 3.1 only)

If the scene needs native audio:
- Dialogue: use colon syntax (`A woman says: We have to leave now.`)
- SFX: describe naturally (`The sound of thunder cracks in the distance.`)
- Ambient: describe the soundscape (`Gentle rain on leaves, distant birdsong.`)
- Music: describe mood (`A low, tense cello drone builds gradually.`)
- To suppress unwanted audio: add `No background music. No laugh track.`
- To suppress subtitles: add `No subtitles.` (can be repeated for emphasis)

### Step 5: Set generation parameters

Specify in the prompt metadata:
- **Model:** Veo 3.1 Fast (iteration) → Veo 3.1 Quality (final)
- **Aspect ratio:** 16:9 (standard) or 9:16 (vertical/Shorts, Veo 3.1 only)
- **Duration:** 8s default (maximum per generation)
- **Outputs:** 1 (iteration) → 2–4 (final selection)

### Step 6: Iterate at zero cost on Ultra

Use Veo 3.1 Fast (free on Ultra) to iterate on prompt wording, camera angles,
and composition. Once the Fast output achieves the desired framing and motion,
switch to Veo 3.1 Quality for the final render.

## Output Format

Deliver each footage prompt as a structured block:

```markdown
### Scene {NN} — Visual Prompt

**Shot type:** {wide / medium / close-up / extreme CU}
**Movement:** {static / pan L→R / tilt up / dolly in / crane / handheld / etc.}
**Model:** {Veo 3.1 Fast → Veo 3.1 Quality}
**Aspect ratio:** {16:9 / 9:16}
**Duration:** {4s / 6s / 8s}
**Outputs:** {1 for iteration / 2-4 for final}
**Credits (Ultra, final render):** {N}

**Prompt:**
"{Full prompt text following the five-part formula}"

**Audio (if applicable):**
"{Audio description — dialogue, SFX, ambient, music}"

**Negative prompt (if applicable):**
"{Elements to exclude — e.g., text, watermark, subtitles}"

**Fallback model:** {Sora 2 / Kling / Runway Gen-4 / Stock footage}
**Fallback rationale:** {Why this scene might need a different tool}
```

## Extension and Chaining

For scenes longer than 8 seconds:
- Use the **Extend** feature (20 credits per extension on Ultra)
- Each extension adds ~7 seconds
- Coherence degrades after 2–3 extensions (~16–24 seconds)
- For scenes >24 seconds, plan as multiple separate generations with
  match cuts or dissolve transitions between them
- Maximum chainable length: ~148 seconds (theoretical, quality drops sharply)

## Advanced Techniques

### Timestamp prompting (Veo 3.1)

For multi-shot sequences within one generation:
```
[00:00-00:03] Wide shot of empty city street at dawn, fog rolling between buildings.
[00:03-00:06] Medium shot, a figure in a red coat emerges from the fog, walking toward camera.
[00:06-00:08] Close-up of their face, eyes scanning the skyline with determination.
```

### First + Last Frame workflow

1. Generate keyframe images with Imagen 4 (free in Flow)
2. Use the "Frames to Video" mode with start and end frame
3. Prompt describes only the *motion* between frames — do NOT re-describe the image
4. Produces the most controlled camera movement and subject consistency

### Ingredients to Video

Supply up to 3 reference images (characters, objects, styles) + text prompt.
Best for maintaining visual consistency of specific elements across clips.
Use @ mentions to reference saved assets in your Flow library.

## What NOT to Prompt

- Avoid instructive negatives ("don't show", "no walls") — use descriptive
  alternatives in the negative prompt field instead
- Do not describe more dialogue than can be spoken in ~8 seconds
- Do not re-describe a reference image when using image-to-video mode
- Do not use quotes around dialogue (triggers unwanted subtitles) — use colons
- Do not expect character consistency across separately generated clips without
  the Ingredients workflow or verbatim character description sheets
- Do not rely on audio in image-to-video or Frames-to-Video mode (audio only
  works reliably in Text-to-Video mode)
