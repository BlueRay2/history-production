# Nagasaki v2 — Cities Evolution Production (7-10 min format)

**Working title:** *Nagasaki — The City That Hid a Faith for 250 Years*
**Target length:** 7-10 minutes (new channel format — shorter, higher CTA cadence)
**Language:** English (narration), Russian (production docs)
**Branch:** `feature/nagasaki-v2`
**Owner (repo):** BlueRay2 (Дима)
**Pipeline owner:** Claude (autonomous — all teammate roles, Codex/Gemini not delegated this run due to auth/crash issues today)

## Hook (cold open, 0:00–0:15)

> In 1865, a group of peasants walked into a newly-built church in Nagasaki and confessed a secret their families had protected for two hundred and fifty years. They were Christians. They had survived crucifixions, torture, and forced renunciation — by simply hiding. Eighty years later, at 11:02 on a bright August morning, a second sun opened directly above the cathedral where their grandchildren now prayed. The oldest hidden Christian community on earth was erased in forty-three seconds.

Two shock reveals — 250-year survival and 43-second erasure — braided across the same physical place (Urakami valley).

## Three eras, three character anchors

| Act | Era | Period | Anchor | Angle |
|---|---|---|---|---|
| I | Sakoku / Dejima | 1639–1853 | Dutch *tsuji* (interpreter) | Japan's only window to the outside world; smuggling of knowledge through 120×75 m artificial island |
| II | Meiji–Shōwa | 1865–1944 | Kakure kirishitan peasant | Coming-out at Ōura Cathedral 1865 → Fourth Urakami Persecution → Urakami Cathedral 1914 |
| III | 9 August 1945 | 11:02 am | Doctor at Nagasaki Medical College (modelled on Nagai Takashi) | Fat Man plutonium implosion 503 m above Matsuyama-chō, 8,500+ of 12,000 Urakami Christians killed |

## Pipeline status

- [x] Branch created from `previews` (all new rules inherited: 7-10 min target, CTA cadence, Phase 7 SEO, Seedance 2.0 lineup)
- [x] `docs/ref/NICHE_STYLE_GUIDE.md` §9 filled for Nagasaki
- [ ] Phase 0: KNOWLEDGE_SUMMARY.md — in flight
- [ ] Phase 1: AUDIENCE_PERSONA.md, RETENTION_ARCHITECTURE.md
- [ ] Phase 2: VIDEO_CREATIVE_BRIEF.md
- [ ] Phase 3: SCRIPT.md (7-10 min, 3 acts)
- [ ] Phase 4: TELEPROMPTER.md, ALL_CLIPS.md (Seedance/Flow/Kling), MUSIC_CUES.md
- [ ] Phase 5: CTA_PLACEMENT.md, integration
- [ ] Phase 5.5: COST_ESTIMATE.md
- [ ] Phase 6: Validation reports
- [ ] Phase 7: COMPETITOR_KEYWORDS.md, GOOGLE_TRENDS_REPORT.md, SEO_PACKAGE.md

## Dependencies

- Style guide: `../docs/ref/NICHE_STYLE_GUIDE.md` (updated with Nagasaki §9)
- Retention patterns: `../docs/ref/RETENTION_STRATEGY.md`
- Service selector: `../.claude/skills/ai-service-selector/`
- Cost estimator: `../.claude/skills/production-cost-estimator/`
- Seedance 2.0 prompting: `../.claude/skills/seedance-2-prompting/`

## Fact-check anchors (must hold through script)

- Fat Man detonation: 11:02 JST, 9 August 1945, ~503 m altitude over Matsuyama-chō
- Yield: 21 kt TNT-equivalent (plutonium implosion)
- Urakami Christian casualties: 8,500+ of 12,000 killed
- Ōura Cathedral discovery: 17 March 1865 (Gregorian), Bernard Thaddée Petitjean
- Kakure kirishitan hiding duration: 250+ years (c. 1614 shogunate ban → 1865 reveal)
- Dejima dimensions: ~120 × 75 m (~9,000 m² / ~2.2 acres)
- Urakamikuzure IV: 1867-1873, 3,394 exiles, 662 deaths
