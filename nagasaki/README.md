# Nagasaki (長崎) — Cities Evolution Production

**Working title:** *Nagasaki — The City That Hid a Faith for 250 Years*
**Target length:** 16 min
**Target publish:** Tuesday, 21 April 2026
**Language:** English (narration), Russian (production docs)
**Branch:** `feature/nagasaki` (worktree: `history-production-claude-nagasaki`)
**Owner:** BlueRay2 (Дима) | **Lead / script / marketing:** Claude | **Research / proofreading:** Gemini | **Prompt-engineering / proofreading:** Codex

## Hook (cold open, 0:00–0:15)

> In 1865, a group of peasants walked into a newly-built church in Nagasaki and confessed a secret their families had protected for two hundred and fifty years. They were Christians. They had survived crucifixions, torture, and forced renunciation — by simply hiding. Eighty years later, at 11:02 on a bright August morning, a second sun opened directly above the cathedral where their grandchildren now prayed. The oldest hidden Christian community on earth was erased in forty-three seconds.

Two shock reveals — 250-year survival and 43-second erasure — braided across the same physical place (Urakami valley).

## Three eras, three character anchors

| Act | Era | Period | Anchor | Angle |
|---|---|---|---|---|
| II | Sakoku / Dejima | 1639–1853 | Dutch *tsuji* (interpreter) | Japan's only window to the outside world; smuggling of knowledge through 120×75 m artificial island |
| III | Meiji–Shōwa | 1865–1944 | Kakure kirishitan peasant | Coming-out at Ōura Cathedral 1865 → Fourth Urakami Persecution → Urakami Cathedral 1914 |
| IV | 9 August 1945 | 11:02 am | Doctor at Nagasaki Medical College Hospital (modelled on Nagai Takashi) | Fat Man plutonium implosion 503 m above Matsuyama-chō, 8,500+ of 12,000 Urakami Christians killed |

## Pipeline status (2026-04-16)

- [x] Topic approved (Ярослав msg 1152 in forum; brief via Дима DM)
- [x] Hook drafted + fact-checked
- [x] Worktree `feature/nagasaki` created from `origin/main`
- [x] Directory scaffold (nagasaki/{docs, assets/footage_prompts})
- [ ] Phase 0: `docs/KNOWLEDGE_SUMMARY.md` (Gemini research — **in flight**)
- [ ] Phase 0.5: `docs/VIDEO_CREATIVE_BRIEF.md`
- [ ] Phase 1: `docs/audience/` (persona, retention architecture)
- [ ] Phase 2: `SCRIPT.md` (16 min, 3 acts, 13–15 scenes)
- [ ] Phase 2.5: `TELEPROMPTER.md` (ElevenLabs v3 tags)
- [ ] Phase 3: `assets/footage_prompts/ALL_CLIPS.md` (100–120 prompts, Sora 2 Pro / Kling / Flow mix)
- [ ] Phase 3.5: `MUSIC_CUES.md`
- [ ] Phase 4: Gemini cross-validation (structure, facts, tone)
- [ ] Phase 5: Rendering handoff to Дима (Thu–Fri)

## Dependencies

- Style guide: `../docs/ref/NICHE_STYLE_GUIDE.md`
- Retention patterns: `../docs/ref/RETENTION_STRATEGY.md` (referenced by Phase 0 template)
- Previous city template: `../quanzhou/` (closest analogue — maritime-history deep-research structure)
- Service selector: `.claude/skills/ai-service-selector/`
- Cost estimator: `.claude/skills/production-cost-estimator/`

## Fact-check anchors (must hold through script)

- Fat Man detonation: 11:02 JST, 9 August 1945, ~503 m altitude, 21 kt yield
- Hypocenter: Matsuyama-chō, Urakami valley
- Urakami Cathedral (浦上天主堂): completed 1914, largest Catholic church in East Asia at the time, ~500 m from hypocenter, destroyed
- Ōura Cathedral (大浦天主堂): built 1864, still standing — where 1865 coming-out happened
- Bernard Petitjean: priest who received the first confession
- Fourth Urakami Persecution (浦上四番崩れ): 1867–1873, exile to 20 fiefs
- Dejima dimensions: 120 m × 75 m, fan-shape, 1641–1853 Dutch-only trading post
- Engelbert Kaempfer: first Western ethnography of Japan (1690–92 on Dejima)
- Philipp Franz von Siebold: two Dejima tenures (1823–29, 1859–62), Siebold Incident over smuggled map

All anchors to be cross-verified in Phase 4 Gemini review.
