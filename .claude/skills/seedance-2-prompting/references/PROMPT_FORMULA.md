# Seedance 2.0 (Jimeng) — Prompt Formula

## Prompt Structure

Jimeng prompts work best with a **layered, multi-modal** structure. Unlike
Flow/Kling which use a single text block, Seedance 2.0 combines:
1. Uploaded reference assets (images, videos, audio) bound with `@name`.
2. Core prompt text describing scene + style + camera.
3. Optional negative prompt.

### Five-Layer Prompt Template

```
[@ReferenceBinding] + [Subject] + [Action] + [Context/Setting] + [Camera] + [Audio/Mood] + [Style]
```

Example (English):
```
@FisherPortrait as main character first frame.
@AncientHarborVideo reference camera dolly move.
@GuzhengAmbient for background music.

A Ming-era Quanzhou fisherman (@FisherPortrait) mending nets at dawn,
standing knee-deep in the harbor shallows. The camera slowly dollies in
from a wide establishing shot to a tight waist-up, following the rhythm
from @AncientHarborVideo. Warm golden-hour light, visible morning mist,
gulls in the background. Mood: quiet, contemplative, human-scale against
vast harbor. Audio: guzheng melody fades in with first dolly move.
Style: cinematic documentary, BBC nature tone, shallow DOF.
```

## @-Reference Syntax

| Reference | Purpose | Notes |
|---|---|---|
| `@Image1 as first frame` | Lock opening composition | Most common pattern |
| `@ImageX as character reference` | Identity lock (face, costume, build) | Pair with motion description |
| `@VideoX reference camera language` | Copy camera movement | Seedance transfers pan/dolly/arc |
| `@VideoX reference motion style` | Copy character movement style | For running, dancing, gestures |
| `@AudioX for background music` | Rhythm + mood anchor | Seedance syncs visual cuts to beats |
| `@AudioX for ambient sound` | Environmental audio bed | Gulls, wind, crowd, etc. |

Custom names work: `@Fisherman`, `@HarborVideo`, `@GuzhengTrack` are fine —
use descriptive names that match your asset library.

## Camera Language

Seedance handles these natively (no preset buttons like Kling):

- **Movement:** dolly in / dolly out, pan left/right, tilt up/down, orbit
  around subject, crane up/down, handheld (stabilized), arc shot, zolly
  (dolly-zoom combination).
- **Shot scale:** extreme wide, wide, medium, medium close-up, close-up,
  extreme close-up.
- **Lens language:** wide-angle (distortion), standard 50mm feel, telephoto
  compression, anamorphic widescreen bokeh.
- **DoF:** shallow / deep focus. Rack focus transitions work but use
  sparingly — can introduce artifacts.

Seedance interprets **natural language camera direction**. You don't need
cinematographic jargon — "camera starts wide and slowly pushes in as he
mends the net" works as well as "dolly in from XWS to MS on subject".

## Identity Locking + Motion Transfer

The killer feature. Combine:
- `@Character as reference cluster` — face, body, costume bound.
- "running through the market" / "dancing" / any large-motion verb.

Seedance keeps face stable where Flow and Kling historically broke at
frame ~60 in dynamic motion. Use this when the clip shows a recurring
protagonist across scenes — upload the same reference image to each
generation for visual continuity.

## Audio Prompting

If `@Audio1` is uploaded:
- "sync visual cuts to @Audio1's beat at 0:02, 0:05, 0:09" — Seedance
  honors explicit timestamps.
- "fade audio @Audio1 in with camera dolly start" — couples A/V events.

If no audio reference:
- Describe desired audio in prompt: "background: slow guzheng melody,
  ambient: harbor sounds, gulls, distant waves. Dialogue: none."
- Seedance generates audio from description — quality varies; for hero
  clips prefer reference-driven audio.

## Negative Prompting

Append after main prompt:
```
Negative: modern elements, tourists with cameras, plastic objects,
text overlays, watermarks, warped hands, 6-finger hands, distorted
faces in motion.
```

Common Seedance failure modes to preempt:
- Hand artifacts in medium-close shots → always add "no warped hands"
- Text/signage in Chinese or English can hallucinate → "no readable
  text in background" unless you want signage
- Face drift across long clips → reinforce with "maintain @Character's
  face identity throughout"

## Clip-Length Tuning

- **3-5s**: minimum useful. Good for cuts, pattern interrupts.
- **6-8s**: sweet spot for narrative beats (matches Flow's cap, so
  interchangeable in montage).
- **9-12s**: Seedance-exclusive territory — use for long dolly moves,
  full narrative action, music-video choreography.
- **13-15s (max)**: use sparingly — generation time and credit cost grow,
  quality occasionally softens at the tail.

## Prompt Language

- **Chinese** (准确度最高 / highest adherence): Jimeng is trained on Chinese
  first. If a team member is comfortable in Chinese, deliver in Chinese.
- **English**: works, slightly lower prompt-adherence (~85% of Chinese
  baseline based on community benchmarks). Fine for our workflow.
- Don't mix languages in one prompt unless referring to Chinese-specific
  cultural nouns (keep them in original pinyin + parenthetical gloss).
