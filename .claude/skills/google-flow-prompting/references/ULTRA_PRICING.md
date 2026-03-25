# Google Flow Credit Economics — Google AI Ultra

> Last verified: 7 March 2026. Sources: Google Flow Help Center,
> Google One AI Credits page, hands-on production testing.
> All figures below apply exclusively to the Google AI Ultra plan.

## Ultra Plan Overview

| Parameter | Value |
|---|---|
| **Monthly price** | $249.99 (introductory: $124.99/mo for first 3 months) |
| **Monthly credits** | 25,000 |
| **Credit expiry** | Unused monthly credits do NOT roll over |
| **Top-up credits** | Available; valid for 12 months from purchase |
| **Storage** | 30 TB |
| **Google Cloud credits** | $100/month (can offset Vertex AI API costs) |
| **Exclusive features** | 4K upscaling, Veo 3.1 Quality access, highest Gemini limits |

## Per-Generation Credit Costs on Ultra

**CRITICAL: Costs are per output, not per request.** A single request
can generate 1–4 outputs. Generating 4 Quality outputs = 400 credits.

#### Flow (Video Generation)

| Model | Credits per output | Max outputs / month (25,000 cr) |
|---|---|---|
| **Veo 3.1 Fast** | **0 (Included)** | **Unlimited** (rate-limited only) |
| **Veo 3.1 Quality** | **100** | 250 |
| **Veo 2 Fast** | **10** | 2,500 |
| **Veo 2 Quality** | **100** | 250 |
| **Video edits** (Extend, Insert/Remove Object) | **20** | 1,250 |
| **1080p** | **0 (Included)** | Included |

#### Whisk (Image/Video Remixing)

| Model | Credits per output | Max outputs / month (25,000 cr) |
|---|---|---|
| **Veo 3 Fast** | **20** | 1,250 |

#### Other

| Product | Credits per output | Max outputs / month |
|---|---|---|
| **Image generation** (Imagen 4 / Nano Banana Pro) | **0** | Unlimited |
| **4K upscaling** | **0** | Ultra exclusive |

### Key pricing notes

1. **Veo 3.1 Fast is free on Ultra.** This changed in August 2025.
   Previously cost 20 credits. Community reports note slight quality
   decrease after the switch to free, but it remains the essential
   iteration tool.

2. **Dual-generation caveat.** Flow may produce 2 videos per request
   by default. A single click on "Generate" with Veo 3.1 Quality can
   consume 200 credits (2 × 100), not 100. Control this by setting
   output count to 1 during iteration.

3. **Extension costs.** Each Extend operation = 20 credits. Chaining
   3 extensions to reach ~29 seconds = 100 (initial) + 60 (3 × 20) =
   160 credits total for a single Quality clip with extensions.

## Effective Cost Per Output

| Scenario | Credits | Cost at $249.99/mo | Cost at $124.99/mo (intro) |
|---|---|---|---|
| 1× Veo 3.1 Fast | 0 | $0.00 | $0.00 |
| 1× Veo 3.1 Quality | 100 | $1.00 | $0.50 |
| 4× Veo 3.1 Quality (one request) | 400 | $4.00 | $2.00 |
| 1× Quality + 3 extensions | 160 | $1.60 | $0.80 |
| 1× Veo 2 Fast | 10 | $0.10 | $0.05 |
| 1× video edit | 20 | $0.20 | $0.10 |
| 1× Whisk Veo 3 Fast | 20 | $0.20 | $0.10 |

**Calculation:** $249.99 ÷ 25,000 credits = $0.01 per credit.
At introductory price: $124.99 ÷ 25,000 = $0.005 per credit.

## Production Budget Planning

### Monthly capacity at typical production volumes

| Production profile | Credits consumed | Videos |
|---|---|---|
| **Light** (5 Quality + 20 Fast iterations/week) | ~2,000/mo | ~20 final clips |
| **Medium** (3 Quality/day + unlimited Fast) | ~9,000/mo | ~90 final clips |
| **Heavy** (8 Quality/day + edits) | ~25,000/mo | ~240 final clips |
| **YouTube script** (~20 scenes, 3 iterations each) | ~6,000–8,000 | 1 full video |

### Cost optimization strategies

1. **Iterate on Fast, render on Quality.** With Veo 3.1 Fast free on
   Ultra, run unlimited prompt iterations at zero cost. Only commit
   Quality credits when the Fast preview matches your vision.

2. **Generate 1 output during iteration.** Switch to 2–4 outputs only
   for the final Quality render to get selection options.

3. **Use Imagen 4 for keyframes.** Image generation is free. Create
   reference frames with Imagen, then use Frames-to-Video for more
   controlled generation.

4. **Reserve Extend for essential scenes.** At 20 credits per extension,
   costs compound. Design most scenes within the 8-second limit.

5. **Top-up for overflow.** At $0.01/credit (matching subscription rate),
   top-up credits last 12 months — buy when running low near cycle end.

## Vertex AI API Pricing (for automated pipelines)

For developers using the API directly:

| Model | Per-second cost | 8-second clip cost |
|---|---|---|
| Veo 3.1 Fast (Gemini API) | ~$0.15/sec | ~$1.20 |
| Veo 3.1 Standard (Gemini API) | ~$0.40/sec | ~$3.20 |
| Veo 2 (Gemini API) | ~$0.35/sec | ~$2.80 |
| Veo 2 (Vertex AI) | ~$0.50/sec | ~$4.00 |

Ultra subscribers receive $100/month in Google Cloud credits, offsetting
approximately 83 Fast API generations or 31 Standard API generations
per month at no additional cost.
