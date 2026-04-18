# Seedance 2.0 — Model Behavior & Production Notes

## Strengths (where Seedance beats Flow / Kling)

1. **Identity Locking through motion.** Character face stays stable even in
   dynamic action (running, dancing, fighting). Use a reference image +
   explicit "maintain face" instruction.

2. **Multi-modal reference binding.** No other free/cheap model accepts
   audio refs, video refs, and image refs simultaneously. For music-video
   style cuts, fashion evolution sequences, or choreography — Seedance
   wins by a wide margin.

3. **Longest clip duration.** 15s max beats Flow (8s) and Kling (10s).
   Lets you build narrative beats within a single generation instead of
   stitching.

4. **Native 2K output.** Better than Flow Fast's 720p baseline. Matches
   Kling 2.6 Pro's 1080p and surpasses it when you need detail.

5. **Cinematic camera work.** Natural-language camera direction interpreted
   with professional-grade fluidity. No need for preset buttons — prompts
   like "camera arcs from behind the character, slowly rising to reveal
   the harbor" work.

6. **Chinese historical / cultural content.** Seedance was trained heavily
   on Chinese imagery and understands Song-Yuan, Ming, Qing aesthetics
   better than Flow/Kling — relevant for Asian-port-city focus of our
   Cities Evolution channel.

## Weaknesses / Known Failure Modes

1. **Hand artifacts in medium-close shots.** Seedance inherits the
   diffusion-model-typical hand problem. Always add negative prompt: "no
   warped hands, no 6-finger hands". For hero close-ups of hands (e.g.
   mending nets), prefer Kling 2.6 Pro which has slightly better hand
   coherence.

2. **Face drift over 12+ seconds without reference.** If no @Character
   image is pinned, faces may drift in long clips. Always pin a reference
   for any recurring protagonist.

3. **Text hallucination.** Signage, book pages, shop-banners render as
   gibberish pseudo-Chinese. If readable text is needed, generate clip
   without text and composite in post.

4. **Chinese content policy** (silent filter). The following categories
   may return no-output or heavily-censored content without explicit
   warning:
   - Political figures (any era, any country) — especially CCP-era
     Chinese leaders, Dalai Lama, Taiwanese presidents
   - Military imagery — weapons, battle scenes above PG-13
   - Religious content involving specific named deities (Christian,
     Buddhist, Islamic imagery may be filtered differently)
   - Explicit violence, blood, injury
   - Adult/sexual content (even tasteful nudity in art-history context)
   - Disputed territories (Tibet, Taiwan, Xinjiang — especially with
     politically-sensitive framing)

   When in doubt, stage the scene abstractly ("a harbor after a storm"
   instead of "the aftermath of the Taiping Rebellion bombardment") and
   add atmospheric references instead of explicit event imagery.

5. **Language-adherence asymmetry.** Chinese prompts produce ~15% more
   faithful outputs vs English prompts. For hero clips, translate the
   final prompt to Chinese before generating — even if you drafted in
   English.

6. **Audio quality ceiling.** Native audio is serviceable but not
   Hollywood-grade. For final mastering, export audio separately and
   re-mix with ElevenLabs VO + library music in CapCut.

## Cross-Service Placement Strategy (Cities Evolution pipeline)

For a typical 7-10 minute video:

| Scene type | First choice | Fallback | Rationale |
|---|---|---|---|
| Hero opening clip (0-30s) | Seedance 2.0 @2K with reference cluster | Kling 2.6 Pro | Identity + motion + longest duration |
| Character close-ups | Seedance 2.0 | Kling 2.6 Pro | Identity locking |
| Action / motion sequences | Seedance 2.0 | Kling 2.5 Turbo | Motion transfer from video ref |
| Atmospheric B-roll / establishing | Flow Lite | Seedance | Cost — Lite is cheapest per second |
| Architectural / landscape | Flow Fast (post-Apr-7 cut) | Seedance | Flow's spatial coherence |
| Transitions / pattern interrupts | Kling Turbo | Flow Lite | Preset camera moves fast |
| Period-specific Chinese historical | Seedance 2.0 | Kling | Training data advantage |

Apply this table in concert with `ai-service-selector` skill for per-clip
decisions.

## Cost Efficiency Note

Given Jimeng's ¥499/mo flat rate gives ~1500 videos and our channel
produces ~4 long-form + ~12 shorts per month (≈ 100 clips + 50 shorts-clips
= 150 clips / month from Seedance if we used it for everything), we are
**wildly under-utilizing** the subscription.

Practical recommendation: default to Seedance for most clips, fall back
to Flow Lite for cheap B-roll only when Seedance hits a quality limit or
content filter. This maximizes ROI on the ¥499 sub.

## Integration with our Pipeline

- `setup-video` skill should ask which model to default to (Seedance /
  Flow / Kling) based on video genre.
- `prompt-engineer` writes Seedance prompts with @-reference markers in
  `scene_XX_clip_YY_prompt.md`. Human operator uploads referenced assets
  to Jimeng and pastes the prompt manually.
- `production-cost-estimator` treats Seedance clips as ~10 credits each
  (¥0.33 / $0.046 USD baseline) unless the prompt specifies 2K+audio+15s
  (then ~25 credits).
