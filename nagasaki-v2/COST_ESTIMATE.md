# COST_ESTIMATE — Nagasaki v2

**Phase 5.5 deliverable.** Production cost breakdown for 7-10 min video.

---

## Footage generation

### Seedance 2.0 (Jimeng, ¥499/mo subscription, ¥3.33 per 100 credits)

| Clip | Duration | Est. credits | Est. cost (¥) |
|---|---|---|---|
| 01A, 02A, 03A, 03B, 03F, 04E, 04H, 04J, 05A, 05B, 05C, 05F, 06A, 06B, 06G, 06I, 06J, 06L, 06M, 07A, 07D, 07F | 3-12s each | 10-25 credits | ¥0.33-0.83 each |
| **Subtotal: 22 hero clips** | avg 8s, 2K, audio | **~300 credits** | **~¥10 ($1.40)** |

Well under monthly subscription (15K credits/mo = 1500 videos). Single video uses ~2% of monthly allowance.

### Kling 2.6 Pro + 2.5 Turbo (Ultra $180/mo, 26K credits/mo)

| Version | Clips | Credits each | Subtotal |
|---|---|---|---|
| 2.6 Pro (audio) | 5 clips @ 5-8s | 35-56 | ~225 credits |
| 2.5 Turbo | 2 clips @ 5s | ~25 (Turbo = 30% cheaper) | ~50 credits |
| **Subtotal** | **7** |  | **~275 credits (~$1.90)** |

### Google Flow / Veo 3.1

| Tier | Clips | Sec | $/sec | Subtotal |
|---|---|---|---|---|
| Veo 3.1 Fast | 8 clips @ avg 5s = 40s | 40 | $0.10 | $4.00 |
| Veo 3.1 Lite | 12 clips @ avg 5s = 60s | 60 | $0.05 | $3.00 |
| Secondary / B-roll (Lite) | 25 clips @ avg 4s = 100s | 100 | $0.05 | $5.00 |
| **Subtotal** |  |  |  | **$12.00** |

### Iteration / re-generation buffer (25%)

Rule of thumb per `production-cost-estimator`: add 25% for failed generations, prompt retries, aesthetic revisions.

| Base | 25% buffer |
|---|---|
| ~$15.30 (Kling + Flow) | $3.83 |
| ~¥10 (Seedance) | ¥2.50 |

### Footage total

- **Flow + Kling:** ~$15.30 + $3.83 = **$19.13**
- **Seedance (Jimeng):** ~¥12.50 = **$1.75** (functionally zero incremental cost — subscription anyway)
- **All footage:** **~$20-22 USD / ~¥140-155 CNY**

---

## Voiceover (ElevenLabs v3)

- Narration char count: ~6,400 chars (TELEPROMPTER.md verified)
- Free tier: 10,000 chars/mo → single video fits in free monthly limit IF no other usage
- Paid: ElevenLabs Starter $5/mo = 30K chars, Creator $22/mo = 100K chars
- **Effective cost:** $0 (fits in existing subscription tier) or $0.40 at prepaid rate
- Multiple takes / revisions: buffer 50% → $0.60 max

### VO total: **~$0-1**

---

## Music / SFX

- Using existing library + CapCut built-in + free Epidemic Sound trial content per workflow
- Bell foley (Urakami bell sound effect): can record from archival YouTube or use public-domain bell sample
- **Effective cost: $0**

---

## Editor time (not billed — Дима's in-house)

- Est. 6-10 hours editing for a 7-10 min video with 70 clips

---

## Grand total

| Line | Cost |
|---|---|
| AI footage (Seedance + Kling + Flow) | ~$20-22 |
| VO (ElevenLabs) | $0-1 |
| Music / SFX | $0 |
| Iteration buffer (already included in footage) | — |
| **TOTAL PER VIDEO** | **~$20-23** |

---

## Comparison to old Sora-era budget

Old Nagasaki (`feature/nagasaki`, 16 min, Sora 2 Pro hero clips):
- Est. Sora-2-Pro-heavy footage: ~$80-120
- Total: ~$100-140 / video

New Nagasaki-v2 (Seedance hero + Flow Lite bulk):
- ~$20-23 / video
- **~5-7× cheaper**, at shorter runtime and with equal or better character-identity quality (Seedance Identity Locking beats old Sora for recurring protagonists).

---

## Budget optimization suggestions

1. **Lean harder on Jimeng subscription** — we're using ~300 credits of 15K monthly budget for this video. Can safely route more Flow Lite clips to Seedance Lite setting (cheaper Seedance mode — consumes fewer credits) if aesthetic matches.
2. **Batch generation off-peak** — Jimeng server queue is faster 22:00-14:00 CST (China off-peak from Yaroslav's timezone).
3. **Cache @reference bundle** — Nagasaki production has 10+ recurring references (tsuji, Nagai, Midori, Urakami cathedral, hibaku Maria, bell, valley). Upload once to Jimeng media tray, reuse across all clips → saves 2-3 credits per clip × 22 clips = ~60 credits saved.
4. **VO char budget** — if splitting into shorts, each Short is ~500 chars → 12 shorts/mo fits easily in ElevenLabs Starter tier.
