# Flow / Veo 3.1 — April 2026 Update

**As of 2026-04-18.** Supersedes older pricing in `ULTRA_PRICING.md`.

## New Model Variant: Veo 3.1 Lite (launched 2026-03-31)

Google's cheapest Veo 3.1 tier, targeting bulk / iterative / draft generation.

| Parameter | Value |
|---|---|
| **API cost** | **$0.05 / second** (720p) |
| **Resolution** | 720p |
| **Audio** | Native audio included |
| **Max duration per clip** | 8 seconds (same as Fast/Standard) |
| **Image-to-video** | Yes |
| **4K upscale** | No (use Fast or Standard for 4K) |
| **Best use** | Draft iterations, B-roll, atmospheric shots where 720p is enough |

## Veo 3.1 Fast — Price Cut (effective 2026-04-07)

Price dropped 14-33%. New rate approximately:
- **~$0.10 / second** at 720p (previously $0.15)
- **4K upscale** supported, **reference images** supported, **video
  extension** supported — Fast is now much closer to Standard for
  most production use-cases.

Recommendation: Default to Fast unless you specifically need Standard's
audio fidelity or deeper cinematic rendering.

## Veo 3.1 Standard / Quality — Unchanged

- **~$0.40 / second** (API, with audio)
- 4K native
- Highest cinematic fidelity
- Still Ultra-subscription-gated in Flow UI

## Subscription Tiers (Gemini / Google AI)

| Plan | Monthly cost | Veo 3.1 Fast videos included | Notes |
|---|---|---|---|
| Google AI Pro | $19.99 | 90 Fast videos | Basic tier, Gemini app access |
| Google AI Plus | ~$49.99 | ~200 Fast videos | Mid-tier |
| Google AI Ultra | $249.99 | ~2,500 Fast videos | Full Flow access, 4K upscale, 25K credits (see ULTRA_PRICING.md) |

## Major News: OpenAI Sora Exited the Market

Per Decrypt/Yahoo tech (April 2026), OpenAI's Sora has exited the
consumer video-generation market. This validates our decision to
remove `sora-2-pro-prompting` skill and shift to Seedance 2.0 +
Veo 3.1 + Kling as our three-model lineup.

## Tier Decision Matrix (Flow-only)

| Use case | Tier | Cost (8s clip) |
|---|---|---|
| B-roll, atmospheric, establishing | Veo 3.1 Lite | $0.40 |
| Narrative action, character close-ups, payoff shots | Veo 3.1 Fast | ~$0.80 |
| Hero clips, 4K finished, audio-critical | Veo 3.1 Standard | ~$3.20 |

For the broader "which model entirely" decision (Flow vs Kling vs
Seedance), see `ai-service-selector` skill.

## Prompt-best-practices (unchanged but re-verified)

The 5-layer formula in `PROMPT_FORMULA.md` remains canonical. Veo 3.1
improvements over 3.0 are in audio sync and character consistency, not
prompt syntax changes.

## Sources

- Google blog announcement: `blog.google/innovation-and-ai/technology/ai/veo-3-1-lite/`
- Decrypt article (Sora exit): `decrypt.co/363077/google-veo-3-1-lite-cuts-api-costs-half-openai-sora`
- testingcatalog.com: `testingcatalog.com/google-launches-veo-3-1-lite-at-half-price-of-veo-3-1-fast/`
- API pricing calculator: `costgoat.com/pricing/google-veo` (last cross-checked 2026-04-18)
