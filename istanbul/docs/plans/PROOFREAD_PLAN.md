# Proofread Plan — Istanbul: The Port Between Two Worlds

**Video:** Istanbul — The Port Between Two Worlds (15-17 min)
**Channel:** Cities Evolution
**Date:** 2026-03-25

---

## 1. Validation Scope Matrix

Proofreading operates across five domains. Each domain is evaluated independently and receives its own PASS/FAIL/WARN verdict.

### Domain A — Factual Accuracy

**Scope:** Every historical claim, date, name, geographic reference, and causal assertion in the script.

**What to check:**
- Historical dates (founding of Byzantion, 330 AD, 1453, Suleymaniye construction dates, Grand Bazaar origins)
- Geographic claims (Bosphorus width, Golden Horn geography, strait characteristics)
- Character plausibility (would a Greek fisherman of that era use those tools, wear those clothes, perform those activities?)
- Architectural claims (Hagia Sophia dimensions, Theodosian Walls length, construction methods)
- Trade route claims (Silk Road connections, what goods were actually traded, which routes existed when)
- Population and scale claims (Constantinople's population at its peak, number of markets, fleet sizes)
- Attribution of events to correct rulers/periods
- Causal claims ("the strait determined the city's fate" — is this historically defensible?)

**Verification method:**
- Cross-reference against SOURCE_MATERIALS citations provided by Research Agent
- Flag any claim not supported by at least one cited source
- For disputed claims, note the dispute and recommend softer language ("historians believe" vs. definitive assertion)

**Severity:**
- Incorrect dates/names = **ERROR** (blocking)
- Disputed claims presented as fact = **WARNING** (non-blocking, recommend hedging language)
- Minor simplifications appropriate for documentary format = **PASS** (note in report)

### Domain B — Linguistic Quality

**Scope:** Grammar, vocabulary, prohibited phrases, terminology consistency, tone register, narrative flow.

**What to check:**
- Standard English grammar (subject-verb agreement, tense consistency, dangling modifiers)
- Prohibited words and phrases (from NICHE_STYLE_GUIDE section 4 — full list below in Section 3)
- Terminology consistency (same term for same concept throughout)
- Tone register consistency (no jarring shifts between literary and colloquial)
- Sentence variety (no monotonous sentence structure; mix of long descriptive and short punchy)
- Readability at target audience level (educated adult, not academic — Flesch-Kincaid 10-12)
- Active voice preference (passive allowed for variety, but not dominant)
- Cliche detection (especially orientalist cliches)
- Paragraph/section flow — each section transitions smoothly to the next

**Severity:**
- Grammar errors in narration = **ERROR** (blocking — will be spoken aloud)
- Prohibited phrases = **ERROR** (blocking — violates channel guidelines)
- Tone register inconsistency = **WARNING** (non-blocking)
- Minor style preferences = **PASS** (note for consideration)

### Domain C — Technical Correctness

**Scope:** ElevenLabs v3 tag syntax, visual prompt completeness, AI model selection compliance, footage duration standards.

**C1. ElevenLabs v3 Tag Syntax**
- All tags in square brackets: `[tag]` not `(tag)` or `<tag>`
- Tags placed BEFORE the text they modify, not after
- No SSML `<break>` tags (not supported in v3 — use `...` and `[pause]` instead)
- No contradictory tag combinations (e.g., `[excited][whispers]`)
- No more than 2 stacked tags per position
- Tags use documented vocabulary (cross-reference with ELEVENLABS_V3_GUIDE sections 1.1-1.11)
- Tags are not embedded mid-word or mid-hyphenated-compound
- `...` used for extended pauses (not `..` or `....`)
- CAPS used for emphasis only on key words, not full sentences

**C2. Visual Prompt Field Completeness**
- Every scene has a visual prompt assigned
- Every prompt includes the cross-service style line suffix
- Prompt length within service-specific sweet spots:
  - Sora 2: 50-200 words
  - Kling: 50-80 words (T2V), 20-40 words (I2V)
  - Flow: 100-150 words
- Each prompt specifies: shot type, camera movement, subject, action, environment, style
- No prompt contains multiple simultaneous camera movements (Sora rule)
- Kling prompts use reversed pan/tilt correctly (pan = vertical, tilt = horizontal)
- Flow prompts place most important elements first (priority ordering)

**C3. AI Model Selection Compliance**
- Premium Start rule enforced: scenes before ~3:00 use premium tier models
- Economy tier (after ~3:00) defaults to Flow Fast, not premium models
- Sora 2 after 3:00 used ONLY for hero human face shots (exception documented)
- Kling used for complex camera motion scenes (not for atmospheric/establishing)
- Flow used for atmospheric/establishing (not for human close-ups)
- Fallback chains documented for each clip

**C4. Footage Duration Standards**
- Every clip duration between 5-10 seconds
- No clip shorter than 5 seconds
- No clip longer than 10 seconds
- Flow clips at 8 seconds maximum (service limit)
- Durations appropriate for scene type (establishing: 8-10s, close-up: 5-8s)

**Severity:**
- Invalid tag syntax = **ERROR** (will cause ElevenLabs to speak the tag aloud)
- Missing visual prompt for a narration segment = **ERROR** (production gap)
- Wrong model selection violating Premium Start = **WARNING** (budget impact)
- Duration out of range = **WARNING** (may need re-generation)

### Domain D — Structural Integrity

**Scope:** Scene numbering, character count targets, open loop plants and payoffs, section duration balance.

**What to check:**
- Scene numbering is sequential and gap-free
- Total character count is within 18,000-22,000 range (15-17 min at ~130-140 WPM)
- Each section falls within its target duration:
  - Hook: 10-15 seconds
  - Context: 1:30-2:00
  - Era 1: 3:30-4:30
  - Era 2: 3:30-4:30
  - Era 3: 3:30-4:30
  - Climax: 1:30-3:00
  - Conclusion: 0:45-1:15
- Every open loop planted in the script has a corresponding payoff later
- Open loops are planted at least 2 minutes before payoff (Zeigarnik effect needs time)
- No section exceeds 5 minutes without a pattern interrupt or visual shift
- Character introductions follow the established pattern (fisherman, merchant, craftsman — in order)
- The three characters do NOT interact across eras (they are separated by centuries)
- Bosphorus motif appears at least once per era (visual continuity requirement)
- The Bosphorus revelation in the climax connects all three characters explicitly

**Severity:**
- Missing open loop payoff = **ERROR** (viewer frustration)
- Section significantly over/under duration target = **WARNING** (pacing issue)
- Character count out of range = **WARNING** (may not hit target duration)
- Scene numbering gap = **WARNING** (production confusion)

### Domain E — Cross-Deliverable Consistency

**Scope:** Alignment between SCRIPT, TELEPROMPTER, and visual prompt documents.

**What to check:**
- **SCRIPT narration text = TELEPROMPTER narration text** (word-for-word match, excluding production annotations)
- Every narration segment in TELEPROMPTER has a corresponding visual clip in the visual prompt plan
- No visual clips exist without corresponding narration (unless explicitly marked as music-only B-roll)
- Scene numbers in SCRIPT match scene numbers in visual prompts
- Character names/descriptions in narration match character descriptions in visual prompt anchors
- Era boundaries (timestamps) are consistent across all documents
- Clip durations in visual prompts are sufficient to cover the narration they accompany
- ElevenLabs segment splits align with natural narrative breaks (no mid-sentence splits)
- Total clip count in visual prompts is consistent with the estimate (37-55 clips)
- Model assignments in visual prompts follow the selection rules documented in VISUAL_PROMPTS_PLAN.md

**Severity:**
- Narration text mismatch between SCRIPT and TELEPROMPTER = **ERROR** (critical production issue)
- Narration segment without visual coverage = **ERROR** (visual gap in final video)
- Timestamp inconsistency across documents = **WARNING** (production confusion)
- Clip count deviation >20% from estimate = **WARNING** (budget impact)

---

## 2. Fact-Check Protocol

### Priority 1 — Foundational Claims (must verify before publication)

| Claim Category | Specific Claims to Verify | Risk Level |
|---|---|---|
| **Founding of Byzantion** | Date (traditionally ~657 BC), founder (Byzas of Megara), initial purpose (fishing colony vs. trade settlement) | HIGH — establishes entire Era 1 premise |
| **Constantinople founding** | 330 AD by Constantine I; reasons for site selection; "New Rome" designation | HIGH — well-documented but details matter |
| **1453 transformation** | Date, key figures (Mehmed II), method (cannons, fleet portage across land), duration of siege | HIGH — most dramatic event in script; factual precision critical |
| **Bosphorus geography** | Width (700m-3.3km), length (~31km), current patterns, strategic significance | HIGH — central thesis depends on geographic accuracy |
| **Hagia Sophia** | Construction dates (532-537 AD under Justinian), architectural claims, conversion timeline | MEDIUM — iconic landmark, widely known, errors noticed quickly |
| **Suleymaniye Mosque** | Construction dates (1550-1557), architect (Mimar Sinan), commission by Suleiman the Magnificent | MEDIUM — well-documented |
| **Grand Bazaar** | Origin date (~1461, expanded over centuries), claim it "survived all three civilizations" (actually built by Ottomans — verify Era 2 market precursors) | HIGH — potential factual error if presented as pre-Ottoman |
| **Theodosian Walls** | Construction date (408-413 AD under Theodosius II), length (~6.5 km), structural claims | MEDIUM — well-documented |

### Priority 2 — Character Plausibility Claims

| Claim | What to Verify |
|---|---|
| Greek fisherman's daily life | Fishing methods in ancient Byzantion; net types; boat construction; clothing materials |
| Byzantine silk merchant trade | Silk trade routes through Constantinople; market organization; merchant social status |
| Ottoman craftsman's work | Stone-working techniques during mosque construction; craftsman guilds; materials used |
| Time-of-day claims | Would a fisherman fish at dawn? Would markets operate at midday? Would construction happen in afternoon? |

### Priority 3 — Contextual/Background Claims

| Claim Category | Risk Level |
|---|---|
| Trade route descriptions (Silk Road, Maritime routes) | LOW — general context, simplified for documentary |
| Population estimates for different periods | LOW — inherently uncertain, note as estimates |
| Climate/weather descriptions | LOW — verify monsoon/seasonal patterns if mentioned |
| Comparisons to other cities (if any) | MEDIUM — comparative claims are easy to dispute |

### Fact-Check Workflow

1. List all factual claims extracted from the final script
2. For each claim, identify the source citation in SOURCE_MATERIALS
3. If no citation exists, flag as **UNVERIFIED** and attempt to verify via known historical sources
4. For any claim that conflicts with SOURCE_MATERIALS, flag as **ERROR**
5. For disputed/uncertain claims, recommend hedging language ("historians believe", "according to tradition", "by most accounts")

---

## 3. Consistency Checklist

### Prohibited Words and Phrases

Check that NONE of the following appear in the narration:

| Prohibited | Category | Replacement |
|---|---|---|
| "Hey guys, welcome back" (or any variation) | YouTube cliche | (omit — cold hook, no greeting) |
| "Subscribe" / CTA in first 60 seconds | Premature CTA | (defer to conclusion) |
| "Mind-blowing", "insane", "you won't believe" | Clickbait hyperbole | Use specific descriptors: "extraordinary", "unprecedented" |
| "Dark Ages" | Historically inaccurate | "medieval period", "Middle Ages" |
| "Exotic" | Orientalist cliche | "distinctive", "remarkable", "singular" |
| "Oriental" | Orientalist cliche | "Eastern", or specific regional term |
| "Mysterious East" | Orientalist cliche | (omit entirely) |
| "Discovered by [Europeans]" | Eurocentric | "encountered by", "arrived at", "reached" |
| "massacre", "genocide", "torture" | Content filter trigger / sensitivity | Contextual alternatives: "the city's population suffered greatly", "a devastating toll" |
| "fall of Constantinople" (as framing) | Eurocentric framing | "the city's transformation", "Constantinople's third life", "the great transition" |

### Naming Conventions

Verify consistent usage throughout the script:

| Entity | Era 1 (Greek) | Era 2 (Byzantine) | Era 3 (Ottoman) | Modern Reference |
|---|---|---|---|---|
| **The city** | Byzantion | Constantinople | Istanbul | Istanbul (if referenced) |
| **The strait** | Bosphorus | Bosphorus | Bosphorus | Bosphorus |
| **The inlet** | Golden Horn | Golden Horn | Golden Horn / Halic | Golden Horn |
| **The building** | — | Hagia Sophia | Hagia Sophia / Ayasofya | — |
| **The market area** | — | Market/Bazaar district | Grand Bazaar / Kapali Carsi | — |

**Rule:** Use the historically appropriate name for each era. When the narration bridges eras, use the name of the era being discussed. On first use of a non-English term, provide brief context (not a formal translation — keep it flowing).

### Tone Register Consistency

Verify the script maintains the channel's documented tone:
- Formality: 5/10 — literary but warm, never academic or casual
- Emotionality: 8/10 — personal stories create emotional depth
- Humor: 2/10 — minimal; slight ironic observations allowed, no jokes
- Address mode: "you" (occasional) — "Stand beside him...", "Look out across the water..."
- Never breaks into first-person ("I think...", "In my opinion...")
- Never addresses the audience directly in meta-commentary ("As you can see in this video...")

---

## 4. Language Localization Check

### Primary Check: English Quality

The narration is in English for an English-speaking global audience. Verify:

- [ ] No Russian words or phrases in the narration text (production documentation is in Russian; narration is not)
- [ ] No untranslated Russian production notes leaked into narration or teleprompter
- [ ] All non-English historical terms (Turkish, Greek, Arabic) are properly introduced with context
- [ ] British vs. American English consistency — pick one and maintain throughout (recommended: British English for documentary tone, but either is acceptable if consistent)
- [ ] No machine-translation artifacts ("it is necessary to note that...", "it should be said that...")
- [ ] No calque constructions from Russian ("in connection with this", "from the point of view of")
- [ ] Numbers written out in narration text ("three civilizations" not "3 civilizations") — for natural speech synthesis
- [ ] Dates formatted for speech ("fourteen fifty-three" not "1453" — or written as "1453" with expectation that ElevenLabs will speak it naturally)
- [ ] Technical terms from production documentation (e.g., "pattern interrupt", "open loop", "retention") do NOT appear in narration text — these are internal concepts, not viewer-facing language

### Secondary Check: Historical Term Accuracy

- [ ] Turkish/Ottoman terms spelled correctly (Suleymaniye, Kapali Carsi, Halic, Beyoglu)
- [ ] Greek terms spelled correctly (Byzantion, Chrysokeras)
- [ ] Arabic-origin terms used appropriately (bazaar, minaret, muezzin)
- [ ] Diacritical marks used if present in source names (or consistently omitted — no mix)

### Tertiary Check: Pronunciation Preparedness

- [ ] Unusual proper nouns have pronunciation guide notes for ElevenLabs (via alias rules in pronunciation dictionary or inline phonetic hints)
- [ ] Key terms that ElevenLabs may mispronounce identified and tested:
  - Byzantion (biz-AN-tee-on)
  - Bosphorus (BOS-for-us)
  - Suleymaniye (soo-lay-MAH-nee-yeh)
  - Hagia Sophia (HAH-gee-ah so-FEE-ah)
  - Mehmed (MEH-med)
  - Theodosian (thee-oh-DOH-shun)

---

## 5. Report Format

### Proofreading Report Structure

```
# PROOFREAD REPORT — Istanbul: The Port Between Two Worlds
**Date:** [date]
**Reviewed by:** [agent]
**Script version:** [version hash or date]

---

## VERDICT SUMMARY

| Domain | Verdict | Errors | Warnings | Notes |
|--------|---------|--------|----------|-------|
| A. Factual Accuracy | PASS/FAIL/WARN | N | N | ... |
| B. Linguistic Quality | PASS/FAIL/WARN | N | N | ... |
| C. Technical Correctness | PASS/FAIL/WARN | N | N | ... |
| D. Structural Integrity | PASS/FAIL/WARN | N | N | ... |
| E. Cross-Deliverable Consistency | PASS/FAIL/WARN | N | N | ... |

**OVERALL VERDICT:** PASS / FAIL / CONDITIONAL PASS

---

## ERRORS (Blocking — must fix before production)

### [E-001] [Domain] — [Short title]
- **Location:** Scene N, line N / TELEPROMPTER segment N
- **Issue:** [Description]
- **Evidence:** "[quoted text from script]"
- **Recommendation:** "[suggested fix]"
- **Severity:** ERROR

### [E-002] ...

---

## WARNINGS (Non-blocking — recommended fixes)

### [W-001] [Domain] — [Short title]
- **Location:** Scene N, line N
- **Issue:** [Description]
- **Recommendation:** "[suggested fix]"
- **Severity:** WARNING

### [W-002] ...

---

## NOTES (Observations, no action required)

### [N-001] ...

---

## STATISTICS

- Total narration characters: N (target: 18,000-22,000)
- Total scenes: N (target: 14-18)
- Total clips: N (target: 37-55)
- Total audio tags: N
- Total ElevenLabs segments: N (target: 4-5)
- Open loops planted: N / Open loops resolved: N
- Prohibited phrases found: N
- Russian text detected in narration: Yes/No
```

### Verdict Definitions

| Verdict | Definition | Action Required |
|---|---|---|
| **PASS** | 0 errors, 0-3 warnings | Proceed to production |
| **CONDITIONAL PASS** | 0 errors, 4+ warnings | Proceed but address warnings before final render |
| **WARN** | 1-2 errors, any warnings | Fix errors, re-review affected sections |
| **FAIL** | 3+ errors OR any critical factual error | Fix all errors, full re-review required |

### Error vs. Warning Classification

| Type | Criteria | Examples |
|---|---|---|
| **ERROR** (blocking) | Would cause visible/audible defect in final video, factual inaccuracy, or policy violation | Wrong historical date; prohibited phrase in narration; invalid ElevenLabs tag syntax; narration/teleprompter text mismatch; missing visual prompt |
| **WARNING** (non-blocking) | Suboptimal but not defective; viewer unlikely to notice; production impact is minor | Tone register slightly inconsistent; clip duration at boundary (exactly 5s or 10s); model selection slightly off-optimal; hedging language recommended for uncertain claim |

### Report Delivery

The proofread report is saved as:
```
istanbul/docs/PROOFREAD_REPORT.md
```

If the verdict is FAIL or WARN, the report includes a numbered fix list. After fixes are applied, a re-review is performed on the changed sections only, and the report is updated with a "Re-review" section appended at the bottom.
