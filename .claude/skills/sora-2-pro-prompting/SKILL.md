---
name: sora-2-pro-prompting
description: >
  Generate production-quality AI video footage prompts for OpenAI Sora 2 Pro.
  Use this skill whenever the user needs to create video generation prompts for Sora 2,
  write visual prompts for AI footage, generate B-roll descriptions, create storyboard
  prompts, or produce scene-by-scene video generation briefs. Also trigger when the user
  mentions Sora, OpenAI video, AI footage prompts, text-to-video prompts, cinematic
  AI video, or asks to write prompts for any AI video generation platform — Sora is
  the default unless another model is specified. Covers text-to-video, image-to-video,
  storyboard, remix, and extend workflows. Includes credit cost awareness, aspect ratio
  selection, and cinematographic prompt architecture.
---

# Sora 2 Pro Prompting Skill

## Purpose

This skill enables Claude to write prompts that produce **cinematic, consistent, production-ready footage** from OpenAI's Sora 2 Pro video generation model. It encodes the official OpenAI prompting guide, community-validated best practices, cost optimization strategies, and a structured prompt architecture developed from hundreds of real-world generations.

The core philosophy: **prompt Sora like you're briefing a cinematographer who has never seen your storyboard.** Concrete visual language beats abstract adjectives every time.

## When to Read Reference Files

Before writing any Sora prompt, read `references/PROMPT_ARCHITECTURE.md` — it contains the prompt template, camera vocabulary, style keywords, lighting patterns, and worked examples. Read `references/COSTS_AND_LIMITS.md` when the user asks about pricing, credit budgets, duration/resolution selection, or cost optimization.

---

## Core Prompting Principles

These five rules produce the highest-quality output. Violating any one of them measurably degrades generation quality.

### 1. One Camera Move + One Subject Action Per Shot

The single most impactful rule. Combining multiple simultaneous movements (e.g., "handheld zooming panning") causes visual incoherence. Instead: "slow handheld dolly left" — one camera behavior, clearly stated.

### 2. Set the Style Declaration First

The opening phrase is the most powerful lever for controlling output. Begin every prompt with a format/style anchor:
- `Cinematic film shot in 35mm, shallow depth of field`
- `90s documentary-style interview, 16mm grain`
- `IMAX-scale establishing shot, anamorphic 2.0x lens`

This shapes everything downstream — lighting, color, motion, composition.

### 3. Structure Prompts in Distinct Blocks

Organize information into clearly separated concerns:

```
[STYLE & FORMAT] — Film format, lens, grade, aspect ratio
[SCENE DESCRIPTION] — Characters, costumes, environment, weather
[CINEMATOGRAPHY] — Camera shot type, movement, angle
[ACTION] — 1–3 specific beats the subject performs
[LIGHTING] — Quality, direction, color temperature, practical sources
[PALETTE] — 3–5 named colors repeated across sequence prompts
[DIALOGUE] — (if applicable) Speaker-labeled lines with timing cues
```

### 4. Name Concrete Visual Details, Not Abstract Qualities

Bad: "A beautiful sunset scene with a person looking thoughtful"
Good: "Golden hour, sun 15° above horizon. A woman in a navy wool coat stands at a weathered wooden pier railing, fingers tracing the grain. Warm amber light rakes across her face from camera-left; cool blue fill from the water below."

### 5. Keep Prompts 50–200 Words for Optimal Results

Very short prompts (<30 words) produce inconsistent results. Very long prompts (>300 words) cause the model to ignore later instructions. The sweet spot is 50–200 words with high information density.

---

## Prompt Generation Workflow

When the user requests a Sora prompt, follow this sequence:

### Step 1: Gather Scene Intent

Determine from the user's request:
- **Subject**: What/who is in the frame?
- **Action**: What happens? (1–3 beats maximum)
- **Mood/Tone**: Emotional register of the scene
- **Use case**: YouTube B-roll, hero shot, social media, narrative?
- **Technical constraints**: Duration, resolution, aspect ratio, budget

If any are ambiguous, ask — but default to: 10s, 1080p, 16:9, cinematic photorealism.

### Step 2: Select Technical Parameters

Based on use case, recommend parameters:

| Use Case | Duration | Resolution | Aspect Ratio |
|---|---|---|---|
| YouTube B-roll | 8–10s | 1080p | 16:9 |
| Hero cinematic shot | 5s | 1080p | 16:9 |
| TikTok/Shorts | 5–10s | 1080p | 9:16 |
| Draft/iteration | 5s | 480p | 1:1 |
| Storyboard sequence | 5s per card | 720p | 16:9 |

### Step 3: Write the Prompt

Consult `references/PROMPT_ARCHITECTURE.md` for the full template, camera vocabulary, and style keywords. Apply the five core principles. Output the prompt in a clean code block labeled with technical parameters.

### Step 4: Add Production Notes

Below each prompt, include:
- **Estimated credits**: Based on resolution × duration (see `references/COSTS_AND_LIMITS.md`)
- **Generation tips**: Any relevant warnings (e.g., "faces work best at front or 45° angle")
- **Iteration strategy**: Suggest generating 3–5 variations, or drafting at 480p first

---

## Output Format

Always present Sora prompts in this structure:

```
═══ SORA 2 PRO PROMPT ═══
Model: sora-2-pro | Duration: 10s | Resolution: 1080p | Aspect: 16:9

[Prompt text here — 50-200 words, structured per the block format]

═══ PRODUCTION NOTES ═══
Credits: ~600 (Pro subscription) | API cost: ~$5.00
Tip: [Relevant generation advice]
Iteration: [Cost-saving recommendation]
```

For multi-shot sequences (storyboards), present each shot as a numbered card with consistent palette anchors and character descriptions repeated across all cards.

---

## Known Strengths and Limitations

Leverage Sora's strengths; work around its weaknesses.

**Excels at:**
- Photorealistic environments: oceans, forests, cityscapes, interiors
- Physics simulation: water, smoke, fire, reflections, fabric
- Camera movements: dolly, pan, tilt, crane, tracking, FPV
- Native audio sync: dialogue with lip-sync, ambient sound, SFX
- Lighting response: golden hour, practical lights, volumetric atmosphere

**Struggles with:**
- Human body dynamics: walking gait, athletic movements, dancing
- Text rendering: ~5% readable text success rate — avoid text in frame
- Multiple simultaneous speakers or complex crowd interactions
- Rapid camera movements: fast whip pans, quick zooms
- Consistent character identity across separate generations
- Hand and finger details at close range

**Workarounds:**
- For character consistency: repeat exact character descriptions across prompts, use image-to-video with a reference frame, or use the Cameo feature for verified likenesses
- For text: add text in post-production (DaVinci Resolve, Premiere), never in the prompt
- For complex actions: break into 2–3 shorter clips and cut in editing
- For iteration: always draft at 480p/5s first, then render finals at target spec

---

## Cost Awareness

Every prompt recommendation should be budget-conscious. Key numbers to internalize:

- **1080p 10s widescreen** = ~600 credits ($12 effective at Pro, $5 API)
- **480p 10s widescreen** = ~50 credits ($1 effective)
- **Remix of existing clip** = ~30–50% of new generation cost
- **Square 1:1** = 30–50% cheaper than 16:9 at same resolution
- **Pro relaxed mode** = unlimited generation at full quality, 3–30 min wait

Always suggest the cheapest viable option for iteration, and reserve high-res priority generation for final renders.

For full cost tables, API pricing, and competitive comparisons, read `references/COSTS_AND_LIMITS.md`.
