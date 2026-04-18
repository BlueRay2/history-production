---
name: seedance-2-prompting
description: >
  Write production-quality AI video generation prompts for ByteDance's Seedance 2.0
  model accessed via Jimeng (即梦, https://jimeng.jianying.com/) webapp UI. Use this
  skill whenever the user needs footage prompts, visual scene descriptions, B-roll
  prompts, or character/motion/audio-referenced generation targeting Seedance 2.0.
  Trigger on mentions of "Seedance", "Seedance 2", "Jimeng", "即梦", "Jianying video
  AI", "ByteDance video model". Covers Jimeng's multi-modal @-reference syntax
  (image + video + audio refs), prompt structure, camera language, Identity Locking
  + Motion Transfer usage, Jimeng subscription cost planning, and known model
  strengths/weaknesses vs Flow and Kling.
---

# Seedance 2.0 (Jimeng) Footage Prompting Skill

Seedance 2.0 is ByteDance's flagship AI video model (released 2026-02-12). We
access it ONLY through the Jimeng (即梦) webapp at `https://jimeng.jianying.com/`.
There is no public API in our workflow — all generation is done through the
browser UI, so this skill documents **prompt-format + workflow conventions**,
not API calls.

## When to Read Reference Files

Before writing prompts, read:

- **Always first:** `references/PROMPT_FORMULA.md` — Jimeng prompt structure,
  multi-modal reference (@Image1/@Video1/@Audio1) syntax, camera language,
  negative-prompt patterns.
- **Budget planning:** `references/JIMENG_PRICING.md` — subscription tiers,
  credits-per-video math, cost comparison with Flow and Kling.
- **Model behavior:** `references/SEEDANCE_BEHAVIOR.md` — Identity Locking,
  Motion Transfer, where the model shines vs where it breaks down, rejection
  patterns from content filters, cross-service placement strategy.

## Key Capabilities (2026-04-18)

- **Duration:** up to 15-second clips (longer than Flow's 8s and Kling's 10s).
- **Resolution:** up to 2K.
- **Native audio:** yes — dialogue, ambient, sound effects generated alongside
  video.
- **Multi-modal reference system (unique):** accepts up to 12 input files per
  generation — 9 images + 3 videos + 3 audio. Bind each with `@name` syntax in
  the prompt:
  - `@Image1 as first frame` — lock the opening composition
  - `@Video1 reference camera language` — copy camera movement from an
    existing clip
  - `@Audio1 for background music` — match rhythm/atmosphere
  - You can name them (e.g. `@FisherPortrait as character reference`) and
    reference them throughout the prompt.
- **Identity Locking + Motion Transfer simultaneously.** Seedance 2.0 uses a
  "Reference Cluster" to hold character traits stable even through large
  motion (running, dancing) — historically the weak point of earlier models.
- **Camera language.** Comparable to professional cinematography (multi-axis
  moves, smooth interpolation, DoF shifts). Less formulaic than Flow/Kling.

## Workflow (webapp-only)

1. Open https://jimeng.jianying.com/ (Chinese UI — use browser translate if
   needed).
2. Switch to Seedance 2.0 model selector.
3. Upload reference assets (up to 9 images + 3 videos + 3 audio) in the
   media tray.
4. Paste prompt with `@references`. Set duration, aspect ratio, audio toggle.
5. Generate — ~1500 videos/mo on 高级会员 ¥499 plan (see pricing ref).
6. Download MP4 + (if enabled) separate audio stem.

## Account / Access Notes

- Jimeng is Chinese-market-first; accessing outside China may require a clean
  browser session with China-region account or a bypass path documented in
  community guides (e.g. `ZeroLu/seedance2.0-how-to` on GitHub).
- Dreamina is ByteDance's English-branded sibling for international; some
  features parity with Jimeng but not always full Seedance 2.0 access.
- No official paid API in our flow — all generation is manual via UI.

## When to Use Seedance 2.0 vs Flow / Kling

Premium-start model. Default pick when:
- Clip needs **>8 sec** continuous shot (Flow caps at 8s, Kling at 10s).
- Clip needs **strong character identity across motion** (protagonist running
  through scene, dancing, dynamic action).
- Clip needs **native audio** with tight sync to the visual rhythm.
- You have **reference footage** (video + audio) for motion/rhythm transfer.
- **2K output** is needed (Flow Fast is 720p baseline, Kling is 1080p).

Switch to Flow (Veo 3.1 Fast or Lite) when: budget-bound establishing shots,
atmospheric B-roll without character identity requirements, 720p OK.

Switch to Kling 2.6 Pro when: stylized / painterly look preferred, strong
camera-preset control needed (pan/orbit/zoom buttons), 1080p sufficient.

See `ai-service-selector` skill for the full decision matrix.

## Hard Rules

- Never fabricate `@reference` names the user didn't upload.
- If the prompt implies a character or location the user hasn't provided as
  reference, ASK before generating — Seedance's Identity Locking is
  powerful only with an anchor image, less so from text-only descriptions.
- Keep prompts ≤500 Chinese chars / ~300 English words. Jimeng truncates.
- Respect Jimeng content policy: no political figures, violence depictions
  above PG-13, explicit content. Flagged generations burn credits without
  output.
- Jimeng UI is Chinese-first. When producing copy for a team member who
  will paste it in, provide the prompt in the UI's language (Chinese
  preferred for best adherence; English works with slightly lower fidelity).

## Coordination

- Inputs from: `ai-service-selector` (decision gate), `production-cost-estimator`
  (budget fit), marketer's emotional arc (match footage mood), editor's scene
  plan (clip duration + narration segment).
- Outputs to: prompt-engineer's per-scene clip prompt files under
  `assets/footage_prompts/scene_XX_clip_YY_prompt.md`.
