# Episode — Paris: How They Built the Eiffel Tower (and Almost Tore It Down)

**Channel:** Cities Evolution
**Episode codename:** `paris-eiffel`
**Status:** Research + Script complete (visual prompts deferred)
**Owner (production lead):** Claude
**Initiated:** 2026-04-28 (request from Dima — msg 8358 / 8360)

## What's here

| File | Purpose |
|---|---|
| [`RESEARCH.md`](RESEARCH.md) | Fact base with sources — Eiffel construction, Manifesto of 300, 1909 demolition rescue, 1940 Hitler lift incident, modern stats. Cross-checked against ≥2 sources where possible. |
| [`SCRIPT.md`](SCRIPT.md) | Full 7-minute Russian-language production script. 8 scenes with narration, audio cues, retention layer notes. **No visual prompts** (deferred per Dima). |

## What's NOT here yet (and why)

Dima explicitly scoped this iteration to **research + script only**. The following are deferred:

- Visual prompts per clip (Sora 2 / Kling / Flow selection)
- COST_ESTIMATE.md
- TELEPROMPTER.md (teleprompter-formatted version of narration)
- MUSIC_CUES.md (refined music sheet)
- ElevenLabs v3 audio tag pass
- Multi-agent proofread (Codex proofreader-1 + Gemini proofreader-2)

Per `docs/MULTI_AGENT_PRODUCTION.md`, the next step (when scope is unblocked) is to spawn proofreaders + visual prompt engineer in parallel.

## Hook angle chosen

**Drama — 1909 demolition deadline + 1940 Hitler lift sabotage.**

Alternative angles considered (in `RESEARCH.md` §7) but not chosen:
- Engineering wonder (1 death in 2 years)
- Controversy (Manifesto of 300)
- Entrepreneur (Eiffel's private financing)

The drama angle was chosen because it provides:
1. Two paired open loops (Cold Hook → Scene 06 → Scene 07 closure)
2. Built-in narrative arc with clear villain-by-time (the critics, then the demolition deadline, then Hitler)
3. Natural callback structure (frame and resolve)

## CTA strategy

CTA placed at **0:15–0:50** with explicit Hype button explanation:
- 3 hypes per week, free, resets Mondays
- Up to 7,500 points for small channels per hype
- 7-day window after publish
- Per YouTube Help docs (verified 2026-04-28)

CTA repeated softly in outro (6:50–7:00) as loyalty loop with next-episode hook ("Berlin Wall").

## Reference docs consulted

- `docs/TEAM_LEAD_PROMPT.md` — production framework
- `docs/ref/RETENTION_STRATEGY.md` — 11 retention techniques (applied throughout SCRIPT.md "Retention Layer" sections)
- `docs/MULTI_AGENT_PRODUCTION.md` — agent role assignments (this iteration ran lead-only; multi-agent pass deferred)

## Verified facts that may surprise

- Construction killed 1 person (lift install, not main build)
- Eiffel paid 5+ of 7.8M francs from his own pocket; received 20-year concession in exchange
- 300 of Paris's most famous artists (Gounod, Dumas fils, Sully Prudhomme) signed petition AGAINST the tower
- Tower was contractually scheduled for demolition in 1909 — saved by being repurposed as the tallest radio mast in Paris (Eiffel orchestrated this preemptively)
- Hitler did NOT ascend the tower in 1940 — French lift mechanics had cut the cables

## Open questions for Dima

If scope is later expanded to full episode pipeline, please confirm:

1. Voice configuration — same Patrick International (ElevenLabs v3, en) as Istanbul, OR ru-language voice?
2. Visual style direction — keep the "Cities Evolution" palette (warm taupe, sandy brown, 35mm film, shallow DOF) or shift for Paris-specific look?
3. Length lock — 7 min final, or open to 10–15 min extended cut?
4. Cross-validation rigor — full Codex + Gemini proofreader pass like dashboard-kpi/kpi bundle, OR lighter single-agent review?
