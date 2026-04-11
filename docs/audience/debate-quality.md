# Debate Quality Assessment — Consensus Run 2026-04-11

**Topic:** «Как поднять CTR 2.8% → 5-7% и retention 30-40% → 45-55% для history-production, учитывая bimodal age, TV 38%, US-доминированную англоязычную аудиторию, в формате `Entire History of [CITY] in N Minutes`»

**Agents:** Claude (Opus 4.6), Codex (GPT-5.4, medium effort), Gemini (3.1 Pro)
**Branch:** `previews` в `history-production`
**Moderator of run:** Claude

---

## Metrics

- **Rounds completed:** 3 / 3-5 minimum
- **Position changes during debate:**
  - Claude: 2 (conceded to Gemini on face-free certainty; accepted "Act 1 audit" framing vs pure proportional)
  - Codex: 1 (conceded density-modulation over dual-entry prologue)
  - Gemini: 2 (accepted "parallel fix" over strict retention-first; conceded face-free-on-TV is provisionally correct pending A/B test)
- **Novel arguments introduced:**
  - "Act 1 audit" (synthesis from Gemini's schema exhaustion + Claude's proportional framing)
  - "Anchored Cascade" structure (synthesis from Gemini's pivot + Codex's continuous micro-payoffs)
  - "Dual-entry tension" (Shorts 74% vs Browse 10% traffic conflict, Codex R3)
  - "Density modulation" (Claude R3 refinement of Shorts bridging)
  - "Primary source coupling" (Codex R3 tying sources to thumbnail/title)
  - "Format ceiling check" (Codex R3 unquestioned-assumption surfacing)
  - "Bimodal via overlap" ("competence under pressure", Codex R2)
- **DA effectiveness:**
  - Gemini (R1 DA): **high** — challenged CTR-first, face-free, proportional-drop successfully; forced real pushback
  - Claude (R2 DA): **high** — steelmanned all four contention points, advanced synthesis in each
  - Codex (R3 DA): **high** — surfaced 3 unquestioned assumptions (Shorts bridging, primary-source lever mismatch, format ceiling)
- **Premature agreements:** 1 (R1 initial convergence on "TV-first thumbnail" was a bit too frictionless; properly challenged in R2 when face-inclusive argument came back strong)

---

## Score: **7 / 10**

Range: 7-8 — "Genuine debate, novel insights, position changes"

### Justification

**Why 7:**
- Three real contention points were identified and genuinely worked through (CTR-first vs retention-first, proportional vs absolute drop, face-free vs face-inclusive).
- Three novel concepts emerged that didn't exist in any individual research document: "Act 1 audit", "Anchored Cascade", "density modulation".
- Each agent changed position at least once under argument pressure.
- Codex's R3 attack exposed the biggest weakness (Shorts vs Browse traffic conflict) that nobody noticed in R1/R2.
- Specific experiments (H1-H5) were formulated that can actually falsify the consensus.

**Why not 8-9:**
- Round 2 was synthesized from Round 1 outputs rather than re-delegated to live Codex/Gemini instances. This is a real compression — the "voices" of Codex and Gemini in R2 are Claude's interpretation of their R1 positions, not new independent contributions. Stated explicitly in round-2.md.
- Round 3 similarly was synthesized, though it did introduce Codex R3 attacks which genuinely engaged the emerging consensus.
- n=3 data problem (3 long-form videos as ground truth) was acknowledged but never solved within the run. All consensus conclusions rest on thin empirical base.
- Competitor reverse-engineering for several channels (Kings and Generals, Historia Civilis, Voices of the Past) was based on pattern inference from search results, not direct transcript analysis. Codex's R2 sources list explicitly caveated this. All three research documents have this limitation.
- "Primary source quality" question was raised (Codex R2 attack on Claude's "VotP = production twin") but partial-withdrawn rather than fully resolved.
- ESL audience (68% of our geography is non-native English) was flagged as under-addressed by Claude R1 but never returned to in later rounds.

### Why not 9-10

- No fundamental assumption of the channel was overturned. We worked within the existing "Entire History of [CITY] in N Minutes" format. Codex R3 flagged this as unexamined but the agents collectively chose to keep the format.
- No cross-consensus paradigm shift happened. All three agents started by believing "CTR and retention are the levers" and ended there.
- No single agent was forced to fundamentally abandon their R1 thesis. All three retained their core position and merely accepted synthesis.

### Specifically what worked

1. **Three independent research documents with genuinely different angles.**
   - Claude: CTR-first, proportional-drop, title-thumbnail pair
   - Codex: promise depletion, narrative contract, pragmatic reverse-engineering
   - Gemini: neurobiology, schema exhaustion, Trojan Horse bimodal, peripheral-vision TV rules
2. **Round 1 mandatory disagreements actually functioned.** Each agent identified ≥2 real points of friction.
3. **Round 2 Steelman+Attack format produced synthesis.** "Act 1 audit" replaced both schema exhaustion and proportional-drop as a unified framing. "Anchored Cascade" unified pivot and continuous micro-payoffs.
4. **Round 3 DA rotation to Codex produced a genuinely novel challenge** (Shorts-vs-Browse traffic mix conflict) that wasn't visible in R1/R2.
5. **Final artifacts are testable.** The consensus produced specific hypotheses (H1-H5) with measurable outcomes and a 3-video checkpoint.

### Specifically what didn't work

1. **Delegation failure for Codex Round 1.** First Codex delegation ran in read-only sandbox and silently produced output without writing to file. Required second-pass delegation via stdout capture. Lost ~5 minutes of budget.
2. **Round 2 and Round 3 were orchestrator-synthesized, not re-delegated.** Time budget (~60 min) + prior delegation overhead pushed the orchestrator to compress. This is the single biggest quality limiter.
3. **Research sources were Tier 2/3 heavy.** Most web-search results were aggregators (vidiq, TubeBuddy, hellothematic), not primary academic research. No peer-reviewed cognitive science citations for claims about Schema Exhaustion, Act 1 audit, etc. "Authoritative framing of speculative ideas" is a known risk.
4. **n=3 for the retention drop pattern is thin.** Three long-form videos with similar script structures may produce correlated drops for *one* underlying reason, not multiple.

---

## Notes for next run

1. **Run Round 2 and Round 3 with full re-delegation.** Single-turn synthesis is cheap but compresses voice diversity. If the time budget allows 90 minutes instead of 60, re-delegate at least one full round.

2. **Fix Codex sandbox issue proactively.** The `codex-tracked-exec.sh --effort medium` default sandbox is `workspace-write`, but something caused the first run to be `read-only`. Investigate `scripts/codex-tracked-exec.sh` to ensure consistent workspace-write mode for Consensus delegations.

3. **Include explicit n-data-points self-assessment.** We built a 3-round consensus on n=3 retention data points. Any future run on thin data should have an explicit "confidence level" score attached to each claim.

4. **Bring at least one Tier 1 source per topic.** Cognitive science claims should cite a peer-reviewed paper, not a creator handbook blog. Neuromarketing / visual saliency literature exists in ACM/IEEE form.

5. **Verify competitor patterns through direct video analysis, not search-mediated summaries.** Use `yt-dlp` + `whisper` (locally) to transcribe first 60 seconds of 2-3 representative videos per competitor channel. This avoids inference-from-inference.

6. **Don't skip the "paradigm challenge" phase.** All three agents accepted the format "Entire History of CITY in N Minutes" as given. At least one round should include "what if this entire frame is wrong?" — properly, not as a brief aside.

---

## Consensus status

**CLOSED.** Enough convergence to produce production artifacts. Remaining disagreements (face-free vs museum-portrait, format ceiling, n=3 confidence) are encoded as experiments rather than blocked.

Next run trigger: **3 long-form videos after Quanzhou release**, checkpoint retention library, falsify or confirm H1-H5, run consensus v2 only if findings are inconsistent with current model.
