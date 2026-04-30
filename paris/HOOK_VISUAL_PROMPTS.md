# HOOK_VISUAL_PROMPTS — Paris: Building the Eiffel Tower

**Episode codename:** `paris-eiffel`
**Scene:** 01 — Cold Hook (0:00–0:20, ~70 words narration)
**Format:** 9:16 vertical, 1080×1920, 60fps, Patrick International cinematic grade
**Service strategy:** Sora 2 Pro across all 4 shots (Premium Start zone per `.claude/skills/ai-service-selector`)
**Created:** 2026-04-30, per Дима msg 9652

---

## Narration ↔ shots map

| Shot | Time | Narration line | Visual concept |
|---|---|---|---|
| 1 | 0:00–0:05 | "Eighteen thousand and thirty-eight iron pieces. Two and a half million rivets. Three hundred workers. Zero deaths during the main build." | Iron lattice forest at dawn, archival overlay numbers |
| 2 | 0:05–0:10 | "The Eiffel Tower has stood over Paris for one hundred thirty-seven years — and it's still the most-visited paid monument on Earth." | Modern night Paris, golden tower, crowd at the base |
| 3 | 0:10–0:13 | "But it was meant to stand for only twenty." | Antique 1885 blueprint, faded red "TEMPORAIRE — 20 ANS" stamp |
| 4 | 0:13–0:20 | "The story of how a temporary engineering experiment outlived its critics, outlived a war, and outlived the man who built it — starts with one contest in 1886." | Eiffel walking through his factory, archival sepia, transition to date card |

---

## Shot 1 (0:00–0:05) — Iron pieces overture

**Service:** Sora 2 Pro
**Duration:** 5s
**Aspect:** 9:16 vertical, 1080×1920, 60fps

> Cinematic close-up, 9:16 vertical, 4K, slow tracking shot through a forest of wrought iron lattice beams of the Eiffel Tower at dawn. Each iron piece sharply lit against a soft orange Paris sky. Camera glides between the lattice cells like through a metallic forest. Numbers "18,038", then "2,500,000", then "300", then "0" appear in elegant white sans-serif overlay, fading in and out one after another over the iron texture, synced to a low strung note swelling. Dust particles in the air. No people in frame. Dramatic low-angle. Patrick International cinematic grade, slightly hushed mood. 60fps.

**Negative prompt:** modern photographers, tourists, cranes, Eiffel Tower full silhouette in distance, motion blur on text overlay.

---

## Shot 2 (0:05–0:10) — 137 years standing

**Service:** Sora 2 Pro
**Duration:** 5s
**Aspect:** 9:16 vertical, 1080×1920, 60fps

> Cinematic wide shot, 9:16 vertical, 4K, present-day Eiffel Tower at golden hour transitioning into full night, fully lit with iconic golden lights and the sparkling beacon. Massive crowd at the base, tourists looking up, phones lifted, faces softly illuminated by the tower's glow. Camera tilts up slowly from the crowd to the very top of the tower, where the antenna pierces a dark blue Parisian sky. Subtle elegant white sans-serif text overlay "137 years" fades in midway through the tilt and fades out before the cut. Slight Paris haze. Patrick International cinematic grade. 60fps. Music swells with the tilt.

**Negative prompt:** daytime overcast, empty foreground, drone-style aerial, tourists with selfie sticks in foreground.

---

## Shot 3 (0:10–0:13) — TEMPORAIRE stamp

**Service:** Sora 2 Pro
**Duration:** 3s
**Aspect:** 9:16 vertical, 1080×1920, 60fps

> Cinematic extreme close-up, 9:16 vertical, 4K, antique 1885 architectural blueprint of the Eiffel Tower with handwritten French notes in faded brown ink. Camera slowly pushes in on a single line of the document where a faded red rubber stamp reads "TEMPORAIRE — 20 ANS" (TEMPORARY — 20 YEARS). Aged paper texture, slight dust particles catch a warm side light from an oil lamp out of frame. Subtle vignette. The red of the stamp dominates the final frame. Patrick International cinematic grade. 60fps. Music drops to silence as the stamp fills the frame.

**Negative prompt:** modern paper, blue ink, color drawings, computer-generated CAD aesthetic, hands holding the document.

---

## Shot 4 (0:13–0:20) — Eiffel in his factory + 1886 card

**Service:** Sora 2 Pro
**Duration:** 7s
**Aspect:** 9:16 vertical, 1080×1920, 60fps

> Cinematic medium tracking shot, 9:16 vertical, 4K, sepia-toned 1880s archival aesthetic. A bearded man in a dark frock coat and waistcoat walks slowly through a vast iron-forging workshop just outside Paris, hands behind his back, surveying rows of glowing iron parts being shaped by workers in caps and aprons. Sparks fly upward in slow motion. Steam and smoke drift across the frame. Soft side light from tall workshop windows. The camera tracks behind him for 4 seconds, then dissolves into a clean black title card with elegant white sans-serif text "1886" centered, holding for 2 seconds before transitioning out. Patrick International cinematic grade. 60fps. Music shifts from low strings to a single piano note as the title card appears.

**Negative prompt:** modern factory, color-saturated, CGI workers, generic blacksmith stereotype, the man's face shown directly to camera, anachronistic safety equipment.

---

## Production notes

- All 4 shots use **Sora 2 Pro** per `.claude/skills/ai-service-selector` Premium Start temporal rule (first ~3 min = premium models). Cold Hook is the most retention-critical surface — no economy substitution.
- **Cross-shot consistency:** keep Patrick International cinematic grade across all 4 shots. Keep dust particles / period grain motif consistent (Shot 1 dust, Shot 3 paper dust, Shot 4 sparks/steam).
- **Text overlays:** white sans-serif (clean, like a high-end documentary). Numbers in Shot 1 + "137 years" in Shot 2 + "1886" title in Shot 4. No overlay in Shot 3 — the red stamp IS the text.
- **Audio handoff:** music continuity across all 4 shots is critical (low strung note swelling through 1+2, dropping at 3, piano on 4). Visual cuts on music beats, not strict 5s grid.
- Iterate via Sora 2 Pro Variations until each shot reaches the cinematic threshold; cost ≤ $5 per shot per `production-cost-estimator`.
