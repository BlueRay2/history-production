# CTA Placement — Nagasaki v2

**Phase 5.4a deliverable (marketer, after re-reading AUDIENCE_PERSONA.md + SCRIPT.md).**
Cadence compliance: time-based (first CTA in minute 1, every 3-4 min, no cluster <90s) + scene-based (every 4-5 scenes — here every 2 scenes, stricter).

---

## CTA-1 — Native Like/Subscribe (first minute)

- **Scene:** 2 (Context)
- **Insertion point:** after line "…at eleven oh two on a summer morning."
- **Time:** ~0:50
- **Type:** `like_subscribe`
- **Exact wording:**
  > Before we go further — if you want to know how a secret faith survives ten generations, and what happens to it when it meets an atomic weapon, subscribe. The bells of Nagasaki deserve the hour I'm going to spend telling you this.
- **Rationale:**
  - **Persona trigger:** "Unexpected historical continuity" (the persona's primary emotional trigger) — the CTA promises both parts of the dual-reveal hook. Not a cold insert.
  - **Scene beat:** comes at the narrative pivot point right before Act I opens — the natural "buy-in" moment.
  - **Language register:** "deserve the hour" matches the reverent, spacious BBC register; no clickbait language.
- **Avoid if:** retention prediction >85% at this timestamp already (audience locked in) — in that case delay CTA-1 to 1:45 at Dejima dawn establishing shot, wrapped as "…subscribe to walk across this bridge with me." (Unlikely — hook curve usually needs reinforcement at 45-60s.)

---

## CTA-2 — Engagement question (Act I body)

- **Scene:** 4 (250-year secret)
- **Insertion point:** final paragraph, after "…mutated into something half-Portuguese, half-Japanese, half-song."
- **Time:** ~3:15
- **Type:** `comment_prompt`
- **Exact wording:**
  > Stop and think about that for a second. How do you keep a faith alive for ten generations with no priests, no printed books, no public ritual? If you've ever kept a family tradition going through hard times, tell me in the comments — what did it take?
- **Rationale:**
  - **Persona trigger:** "Human-scale narratives" + Need for Cognition (high) — invites genuine reflection, not a drive-by comment.
  - **Scene beat:** comes at the completion of the kakure kirishitan portrait — the emotional peak of Act I, where the viewer has just absorbed the scale of what was accomplished. Asking the reflection question here converts curiosity to engagement.
  - **Language register:** "Stop and think about that for a second" signals narrator breaking fourth wall gently — matches BBC-documentary register.
  - **Specificity:** question is tied directly to the scene content ("for ten generations", "no priests…no books…no ritual") — makes it impossible to answer without engaging with the story, which is the CTA's actual purpose.
- **Avoid if:** the narrator's voice is too close to a "hansai" moment right here (emotional weight too heavy for comment interruption) — if post-prod feels the Orasho chorale cue at 2:55 carries more weight than planned, push CTA-2 to scene 5 opening at ~3:35 with "before we go through that door with them — if this is landing, tell me."

---

## CTA-3 — Native Like/Subscribe (pre-payoff weld)

- **Scene:** 6 (9 August 1945)
- **Insertion point:** after "He chose the valley with the most distinct landmark visible through the clouds: a twin-towered brick cathedral." AND BEFORE "At eleven oh two…"
- **Time:** ~6:20
- **Type:** `like_subscribe` (but framed quietly, as a moral moment not an ad break)
- **Exact wording:**
  > What comes next is the hardest part of the story. If you've made it here, like this and stay with me — it matters that people hear it.
- **Rationale:**
  - **Persona trigger:** "Moral complexity over clean heroes/villains" + the persona's value of intellectual honesty — this CTA doesn't say "smash that like button"; it says "this story deserves to be heard", which aligns with the persona's sense of civic seriousness.
  - **Scene beat:** lands at the precise moment of narrative pivot — bombardier chose the target, next line is detonation. Pre-payoff weld technique per CTA STRATEGY doc — welded to the rhetorical peak so the algorithm signal is caught at max emotional tension.
  - **Language register:** "it matters that people hear it" is the quietest possible CTA — no exclamation, no hype. Consistent with Nagai-inspired reverent tone.
- **Avoid if:** test viewers in post-prod feel the CTA breaks the cathedral→bomb sonic bridge (i.e., the Shepard-tone bell chime flows too continuously from cathedral to detonation) — then move CTA-3 back 30s to "The bombardier, Kermit Beahan…" line; keep wording the same.

---

## CTA-4 — Closing question (mandatory)

- **Scene:** 7 (Conclusion)
- **Insertion point:** after the coda narration "…every year it rings for a community that refused, three times, to disappear."
- **Time:** ~8:40
- **Type:** `comment_prompt` (mandatory direct-question final CTA per new rules)
- **Exact wording:**
  > Which piece of this story stayed with you the most — the two hundred and fifty years of hiding, the forty-three seconds, or the bell that still rings? Tell me in the comments below.
- **Rationale:**
  - **Persona trigger:** reflection-inviting (High Need for Cognition), three-option question respects audience intelligence (they can pick which thread spoke to them).
  - **Scene beat:** comes AFTER the coda's Shepard-tone resolution ("three continents of time") — the emotional high of the video is already landed; CTA is the reflective dismount.
  - **Language register:** "Tell me in the comments below" — conventional but necessary for first-time viewer algorithm-signal clarity. YouTube's engagement model rewards literal direct address.
  - **Specificity:** three options tied directly to the three Acts. No generic "what did you think?" — audience must pick a thread, which forces substantive comments.
- **Avoid if:** none — this CTA is MANDATORY per new rules (§6 of NICHE_STYLE_GUIDE and Phase 7 gate). If wording feels too formulaic after listening in post-prod, options are:
  - (a) re-gender the three options: "the silence, the flash, or the bell still ringing"
  - (b) shorten: "two hundred fifty years, forty-three seconds, or the bell that still rings — which stayed with you? Tell me below."
  - Keep the three-option structure; that's the core retention/engagement device.

---

## Cadence audit

| Rule | Status |
|---|---|
| First CTA in first minute | ✅ CTA-1 at 0:50 |
| Every 3-4 minutes thereafter | ✅ CTA-1 → CTA-2 = 2:25 gap (<4min, safe side); CTA-2 → CTA-3 = 3:05 gap; CTA-3 → CTA-4 = 2:20 gap |
| Alternating comment_prompt vs like_subscribe | ✅ L/S → comment → L/S → comment |
| Final CTA is direct question | ✅ CTA-4 |
| No clustering <90s | ✅ all gaps ≥2:20 |
| Every 4-5 scenes | ✅ every 2 scenes (stricter; safer for engagement volume) |

---

## Editor integration note (T5.4b)

For T5.4b splice into SCRIPT.md: the four CTAs are already welded into SCRIPT.md inline with ⟨CTA-N⟩ markers at the specified insertion points. Editor's task here is mostly validation (tone continuity check when read aloud), not re-insertion.

If editor's read-aloud pass reveals any CTA breaks the scene's voice or tonal continuity → flag back to marketer for rewrite per T5.4b rule (no silent edits). Keep the scene_number + cta_type constants; only exact_wording is negotiable.

---

## Proofreader checklist (for T6.5 validation)

- [ ] Each CTA `exact_wording` is grammatically clean and matches narrator register.
- [ ] Each CTA's insertion_point in SCRIPT.md exactly matches the time specified here.
- [ ] Read-aloud test: each CTA flows from preceding line without audible "gear change".
- [ ] Closing CTA-4 is unambiguously a direct question with ≥2 options and ends with "comments" directive.
- [ ] Time-stamps pass cadence rules above.
- [ ] No forbidden-words (`NICHE_STYLE_GUIDE §4`) appear in any CTA.
