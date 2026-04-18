# Jimeng (Seedance 2.0) — Pricing & Budget Planning

**Source:** Jimeng webapp subscription page screenshot (2026-04-18).
All costs in CNY (¥). Convert: ¥1 ≈ $0.14 USD (check live rate if budgeting
in USD).

## Current Plan (used by our team)

### 高级会员 (Premium Member) — best-value tier
- **Price:** ¥499 / month (~$70 USD)
- **Credits:** 15,000 积分 / month
- **Effective rate:** ¥3.33 per 100 credits
- **Generation capacity:**
  - Up to **60,000 images** OR
  - Up to **1,500 videos** per month (≈ 10 credits per standard video)
- **Per-video cost:** ¥0.33 (~$0.046 USD / video)

Caveats on the 1,500-video estimate (community benchmarks):
- Assumes ~5-8s clip length at standard quality.
- Longer (12-15s) or 2K-HD clips cost 1.5-2× more credits → 800-1000 clips
  instead of 1500.
- Reference-heavy multi-modal generations cost slightly more.
- Failed generations (content filter, server error) typically refund credits
  automatically, but verify per-generation.

## Cost Comparison (per 8-second clip at production quality)

| Service | Cost per clip | 2K? | Native audio? | Multi-ref? |
|---|---|---|---|---|
| **Jimeng Seedance 2.0** (高级会员) | ~¥0.33 / $0.046 | ✅ | ✅ | ✅ (9 img + 3 vid + 3 audio) |
| **Google Flow Veo 3.1 Lite** (API) | $0.40 (8s × $0.05) | 720p | ✅ | ❌ |
| **Google Flow Veo 3.1 Fast** (API, post-Apr-7 cut) | ~$0.80-1.20 / clip | 720p/4K | ✅ | Image only |
| **Google Flow Veo 3.1** (Standard, API) | ~$3.20 / clip ($0.40/s) | 4K | ✅ | Image only |
| **Kling 2.5 Turbo** (5s @ 1080p, Pro) | ~$0.20-0.30 | 1080p | ❌ | Image only |
| **Kling 2.6 Pro** (5s @ 1080p, with audio) | ~$0.35-0.50 | 1080p | ✅ | Image only |

**Bottom line:** Seedance via Jimeng is ~10× cheaper than Veo 3.1 Standard
and comparable to Kling Turbo, while offering the most sophisticated
multi-modal reference system and longest max duration (15s).

## Budget Planning for a Typical Cities Evolution Video

For a 7-10 minute long-form video with ~80-120 clips:
- If we use **Seedance for premium 3-min opening** (~30 clips) + Flow Lite
  for background B-roll (~60 clips): credit cost ≈ 30 × 10 = 300 credits
  from Jimeng + ~$12-15 on Flow Lite. Well within monthly budget.
- If **all-Seedance** (100 clips × 10 credits = 1000 credits): uses ~7% of
  monthly allowance. Essentially free at our scale.
- **Shorts** (15-30 sec, 3-5 clips): ~30-50 credits per short. Can do
  300+ shorts/month on one subscription.

## Credit Math Reference

| Credit cost (typical) | What it buys |
|---|---|
| 5 credits | Short image generation (1024×1024, 1 img) |
| 10 credits | Standard 5-8s video clip (1080p, no audio) |
| 15-20 credits | 10-12s clip OR 2K clip OR audio-enabled clip |
| 25-30 credits | 15s clip at 2K with audio + reference cluster |
| +5 credits | Each additional reference asset beyond 3 |

Use `compare_keywords` in production-cost-estimator skill for per-video
amortization.

## Outages / Rate Limits

- Jimeng does NOT rate-limit credits (you have 15K/month, burn freely).
- Server-side generation queue can slow under load (evenings China time
  14:00-22:00 CST) — batch work during off-peak if speed matters.
- Periodic UI maintenance windows — watch for 服务维护 banner.

## When NOT to use Jimeng

- **Client deliverable with English-only team:** Jimeng UI is Chinese.
  Non-Chinese-reading teammates need browser translate or hand-holding.
  Consider Flow for self-serve pipelines.
- **API-required workflows:** No public API. If you need programmatic
  generation, use Flow or Kling API instead.
- **Budget-unconstrained premium work requiring 4K native:** Seedance caps
  at 2K; Flow Standard offers native 4K.
- **Content that might trip Chinese content policy** (political, certain
  historical figures): move to Flow or Kling to avoid silent filter.
