# Xi'an — The City Where 8,000 Clay Soldiers Still Stand Guard

**Format:** 7-10 min long-form documentary
**Channel:** Cities Evolution (UCjLrTC9jdfx6iI5w7SL8LHw)
**Requested by:** Дима (BlueRay2), 2026-04-22 00:11+03:00 via Telegram msg 6906.
**Hook anchor:** Terracotta Army — globally recognised, serves as universal cold-open.
**Coordinator:** Claude
**Delegation plan:**
- Phase 0 Knowledge Summary → **Gemini** (research-heavy, WebSearch-aware)
- Phase 1 audience persona + retention architecture → **Claude** (policy/narrative)
- Phase 2 SCRIPT.md → **Codex** (long-form content generation with tight structure)
- Phase 3-4 review/refinement → Codex + Gemini parallel (per process.md Ярослав directive)
- Phase 5-7 (clips, cost estimate, SEO) → Codex
- Phase 8 final proofread → parallel critic pass

**Branch:** `feature/xian`

## Working arc (to be confirmed after Phase 0 research)

| Era | Approx dates | Hook |
|---|---|---|
| Neolithic Banpo | 5000-4000 BCE | Early urban origins — 6000-year-old village under modern city |
| Zhou capital (Feng/Hao) | 1046-771 BCE | First "empire" capital nearby |
| **Qin Shi Huang's tomb & Terracotta Army** | 221-210 BCE, **discovered 1974** | **COLD OPEN** |
| Han Chang'an | 206 BCE–220 CE | Silk Road western terminus |
| Tang Chang'an | 618-907 CE | World's largest city (~1 million), cosmopolitan capital |
| Muslim Quarter / Great Mosque | 742 CE onwards | Xi'an as gateway of Islam into China |
| Xi'an Incident | December 1936 | Chiang Kai-shek kidnapped — changed WWII trajectory |

## Directory layout (follows nagasaki-v2 pattern)

```
xian/
├── README.md                       ← this file
├── docs/
│   ├── KNOWLEDGE_SUMMARY.md        ← Phase 0 (Gemini)
│   ├── VIDEO_CREATIVE_BRIEF.md     ← Phase 1 (Claude)
│   ├── audience/
│   │   └── AUDIENCE_PERSONA.md     ← Phase 1
│   ├── research/                   ← Gemini source dump, competitor analysis
│   ├── plans/                      ← retention architecture, CTA placement
│   └── validation/                 ← fact-check notes
├── SCRIPT.md                       ← Phase 2 (Codex)
├── TELEPROMPTER.md                 ← Phase 3 (Codex)
├── ALL_CLIPS.md                    ← Phase 4 (Codex, ~40-60 visual prompts)
├── COST_ESTIMATE.md                ← Phase 5
├── SEO_PACKAGE.md                  ← Phase 6 (Codex)
├── MUSIC_CUES.md                   ← Phase 7
├── CTA_PLACEMENT.md                ← Phase 7
└── assets/                         ← reference images, source screenshots
```

## Cold-open hypothesis

> In 1974, a farmer digging a well in rural Shaanxi struck something hard. He'd just found the private army of China's first emperor — 8,000 life-size clay soldiers, each with a different face, entombed for two thousand years. Two kilometres away lies his mummified emperor, in a tomb still sealed because even modern archaeology is afraid to open it. This is the story of Xi'an — the city where the First Emperor still keeps his court.

To be refined in Phase 1 after Gemini's Knowledge Summary verifies Hook-A/B/C options against current Xi'an SEO landscape and persona fit.

## Status

| Phase | Owner | Status |
|---|---|---|
| 0 — Knowledge Summary | Gemini | dispatched |
| 1 — Audience persona + retention arch | Claude | pending (after phase 0) |
| 2 — SCRIPT.md | Codex | pending |
| 3 — TELEPROMPTER.md | Codex | pending |
| 4 — ALL_CLIPS.md | Codex | pending |
| 5 — COST_ESTIMATE.md | Codex | pending |
| 6 — SEO_PACKAGE.md | Codex | pending |
| 7 — MUSIC_CUES + CTA_PLACEMENT | Codex | pending |
| 8 — Final proofread | Codex + Gemini parallel | pending |

Parallel review per `docs/tz/dashboard-kpi/process.md` (Ярослав directive msg 6879) applies here when code-level review is needed. Narrative content review pass is Claude-curated (Дима + Настя final approval).
