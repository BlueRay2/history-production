# Google Flow Prompt Formula Reference

## Table of Contents

1. [Five-Part Formula](#five-part-formula)
2. [Camera Movement Keywords](#camera-movement-keywords)
3. [Framing and Lens Keywords](#framing-and-lens-keywords)
4. [Lighting Descriptors](#lighting-descriptors)
5. [Atmosphere and Weather](#atmosphere-and-weather)
6. [Style Keywords](#style-keywords)
7. [Audio Prompting Syntax (Veo 3.1)](#audio-prompting-syntax)
8. [Negative Prompting](#negative-prompting)
9. [Timestamp Prompting](#timestamp-prompting)
10. [Prompt Examples by Footage Type](#prompt-examples-by-footage-type)

---

## Five-Part Formula

**Order matters.** Veo prioritizes elements mentioned first in the prompt.

```
[1. Cinematography] + [2. Subject] + [3. Action] + [4. Context] + [5. Style & Ambiance]
```

| Part | What to include | Example phrases |
|---|---|---|
| **1. Cinematography** | Camera angle, movement, lens type, framing | "Slow dolly-in close-up shot", "Aerial drone sweep" |
| **2. Subject** | Who/what, described with visual specificity (clothing, color, material, texture) | "A weathered fisherman in a torn yellow raincoat" |
| **3. Action** | What is happening — use motion verbs, describe trajectory | "Casting a net into churning grey waters" |
| **4. Context** | Environment, time, weather, spatial relationships | "On a wooden pier during a violent coastal storm at dusk" |
| **5. Style & Ambiance** | Film style, lighting quality, color palette, emotional tone | "Documentary realism, desaturated teal-and-orange grade, moody" |

**Target length:** 100–150 words (3–6 sentences).
- < 50 words → generic, unpredictable output
- > 200 words → coherence failures, conflicting elements

---

## Camera Movement Keywords

Confirmed working in Veo 3.1 (community-tested, March 2026):

### Movement types
| Keyword | Effect |
|---|---|
| `dolly shot` / `dolly in` / `dolly out` | Forward/backward camera movement along track |
| `tracking shot` | Camera follows subject laterally |
| `crane shot` | Vertical camera movement (up or down) |
| `pan` / `pan left` / `pan right` | Horizontal rotation from fixed position |
| `tilt up` / `tilt down` | Vertical rotation from fixed position |
| `aerial shot` / `drone sweep` | High altitude, moving overhead |
| `arc shot` | Camera orbits around subject |
| `steadicam` | Smooth handheld-style following shot |
| `handheld` / `shaky cam` | Deliberate instability, documentary feel |
| `timelapse` | Accelerated time passage |
| `dolly zoom` / `vertigo effect` | Zoom + dolly in opposite directions |
| `static` / `locked-off` | No camera movement |
| `pull back` / `reveal` | Camera retreats to reveal wider context |
| `push in` | Camera advances toward subject |
| `whip pan` | Rapid pan creating motion blur |

### Movement modifiers
- `slowly` / `gradually` — reduces movement speed
- `rapidly` / `quickly` — increases movement speed
- `smoothly` — emphasizes stability
- `starting low and ascending` — compound movement description

---

## Framing and Lens Keywords

### Shot sizes
| Keyword | Coverage |
|---|---|
| `extreme wide shot` / `establishing shot` | Full environment, subject tiny |
| `wide shot` / `full shot` | Full subject + surrounding environment |
| `medium wide` / `cowboy shot` | Subject from knees up |
| `medium shot` | Subject from waist up |
| `medium close-up` | Subject from chest up |
| `close-up` | Face or single object fills frame |
| `extreme close-up` / `macro` | Detail — eye, texture, mechanism |

### Angles
| Keyword | Effect |
|---|---|
| `low angle` / `worm's eye` | Looking up at subject (power, dominance) |
| `high angle` / `bird's eye` | Looking down at subject (vulnerability) |
| `eye level` | Neutral, natural perspective |
| `over-the-shoulder` / `OTS` | Framed past one character toward another |
| `POV` / `first person` | Camera is the character's eyes |
| `Dutch angle` / `canted angle` | Tilted horizon (unease, tension) |
| `top-down` / `overhead` | Directly above looking straight down |

### Lens simulation
| Keyword | Visual effect |
|---|---|
| `shallow depth of field` | Subject sharp, background blurred |
| `deep focus` | Everything sharp front-to-back |
| `macro lens` | Extreme magnification of small details |
| `wide-angle lens` / `fisheye` | Distorted, expansive field of view |
| `telephoto` / `long lens` | Compressed depth, flattened perspective |
| `50mm lens` | Natural perspective, portrait-like |
| `anamorphic` | Horizontal lens flares, oval bokeh, cinematic |
| `tilt-shift` | Selective focus creating miniature effect |
| `soft focus` | Gentle overall softness |

---

## Lighting Descriptors

### Natural light
| Keyword | Visual |
|---|---|
| `golden hour light` | Warm, low-angle sun near sunrise/sunset |
| `blue hour` | Cool, diffuse light just before dawn or after sunset |
| `dappled sunlight` / `dappled light through canopy` | Patterned light-shadow through leaves |
| `harsh midday sun` | Strong overhead light, hard shadows |
| `overcast` / `flat light` | Soft, shadowless, even illumination |
| `backlit` / `contre-jour` | Light source behind subject, rim glow |
| `silhouetted` | Subject as dark shape against bright background |
| `rim lighting` | Bright edge around subject from back/side light |
| `lens flare` | Light artifacts from shooting toward source |
| `volumetric light` / `god rays` | Visible light beams through atmosphere |

### Artificial light
| Keyword | Visual |
|---|---|
| `neon glow` (+ color) | Colored artificial light, urban/cyberpunk |
| `fluorescent overhead` | Cool, slightly green, institutional |
| `candlelight` / `firelight` | Warm, flickering, intimate |
| `spotlight` | Focused beam, theatrical |
| `tungsten` / `warm indoor light` | Orange-warm interior lighting |
| `LED panel` / `studio lighting` | Clean, controlled, commercial look |
| `streetlight` / `sodium lamp` | Orange-yellow urban night light |

### Lighting modifiers
- `soft light` / `diffused` — reduced contrast, gentle shadows
- `hard light` — sharp shadow edges, dramatic
- `high-key` — bright, low contrast, airy
- `low-key` / `chiaroscuro` — dark, high contrast, dramatic
- `color temperature: warm / cool / neutral`

---

## Atmosphere and Weather

Confirmed to produce reliable visual effects:

| Keyword | Visual effect |
|---|---|
| `thick fog` / `dense mist` | Reduced visibility, depth layering |
| `light haze` | Subtle atmospheric diffusion |
| `rain` / `heavy rain` / `drizzle` | Water droplets, wet surfaces |
| `snow` / `gentle falling snow` / `blizzard` | Snowflakes, accumulation |
| `dust motes dancing in a beam of light` | Particle effects in light |
| `smoke` / `wispy smoke` | Floating particles, mystery |
| `swirling desert sands` | Wind-driven particles |
| `heat haze` / `heat shimmer` | Air distortion from heat |
| `underwater` / `submerged` | Aquatic light caustics, bubbles |
| `frost` / `ice crystals` | Cold surface textures |
| `storm clouds` / `dramatic sky` | Atmospheric sky with movement |
| `aurora borealis` / `northern lights` | Color bands in night sky |

---

## Style Keywords

### Film and genre styles
| Keyword | Look |
|---|---|
| `cinematic` | General high-production-value look |
| `documentary` / `vérité` | Observational realism |
| `film noir` | High contrast B&W, deep shadows, moody |
| `retro` / `VHS` / `analog` | Scan lines, color bleed, grain |
| `found footage` | Shaky, raw, accidental feel |
| `music video` | Stylized, high energy, creative grading |
| `commercial` / `advertisement` | Clean, polished, product-focused |
| `news broadcast` | Formal framing, institutional |

### Animation and CG styles
| Keyword | Look |
|---|---|
| `3D cartoon` / `Pixar-style` | Smooth CG animation aesthetic |
| `anime` | Japanese animation style |
| `stop-motion` / `claymation` | Frame-by-frame physical animation |
| `graphic novel` / `comic book` | Bold lines, flat color, panels |
| `8-bit` / `pixel art` | Retro game aesthetic |
| `LEGO` | Brick-built world |
| `origami` / `papercraft` | Folded paper aesthetic |

### Period-specific
| Keyword | Look |
|---|---|
| `shot on 1980s color film, slightly grainy` | Analog warmth, grain |
| `1970s Kodachrome` | Saturated, warm vintage |
| `black and white, 1940s newsreel` | B&W film grain, period |
| `early color television, 1960s` | Desaturated, slightly off color |
| `Super 8` / `home movie` | Small gauge film look |

### Aesthetic modifiers
| Keyword | Effect |
|---|---|
| `cyberpunk` | Neon, rain, tech-noir |
| `solarpunk` | Green tech utopia, organic + high-tech |
| `cottagecore` | Pastoral, cozy, rustic |
| `brutalist` | Raw concrete, imposing geometry |
| `minimalist` | Clean, sparse, essential |
| `maximalist` | Dense, ornate, overwhelming |
| `dreamlike` / `surreal` | Logic-defying, uncanny |
| `hyperrealistic` | Indistinguishable from reality |

---

## Audio Prompting Syntax

Audio generation is native to Veo 3/3.1. Specify audio directly in the
text prompt. Audio **only works reliably in Text-to-Video mode** — not
in image-to-video or Frames-to-Video.

### Dialogue
Use colon syntax to avoid triggering visual subtitles:
```
A man says: We need to leave before sunrise.
A child whispers: Look at the stars.
```
Do NOT use quotes around dialogue. Quotes may generate on-screen text.

### Sound effects
Describe naturally within or after the visual description:
```
The sound of a heavy metal door slamming shut echoes through the hallway.
SFX: Glass shattering, followed by an alarm.
```

### Ambient sound
```
The ambient sounds of a busy Tokyo intersection at night — car horns,
distant chatter, the hum of neon signs.
```

### Music
```
A low, tense cello drone builds gradually underneath the scene.
Upbeat electronic music with a driving bassline.
```

### Audio suppression
To prevent unwanted audio hallucinations:
```
No background music. No dialogue. Only ambient wind and birdsong.
```

### Subtitle suppression
Veo sometimes bakes in poorly-spelled subtitles. Mitigation:
```
No subtitles. No on-screen text. No subtitles.
```
(Repetition helps suppress this behavior.)

---

## Negative Prompting

Flow supports a negative prompt field. Use descriptive alternatives, not
instructive negatives.

**BAD:** `No walls. Don't show people. No text.`

**GOOD:** `wall, frame, border, text, watermark, subtitle, blurry,
low quality, distorted, deformed hands, extra fingers`

Common negative prompt elements for production footage:
```
text, watermark, subtitle, logo, UI elements, blurry, out of focus,
overexposed, underexposed, distorted, warped, extra limbs, deformed hands,
extra fingers, cropped, letterbox bars, frame border, glitch, artifact
```

---

## Timestamp Prompting

Available in Veo 3.1. Enables multi-shot sequences within a single
8-second generation:

```
[00:00-00:03] Wide establishing shot of an empty parking garage,
fluorescent lights flickering overhead.
[00:03-00:06] Medium shot, a figure in black walks between the cars,
footsteps echoing.
[00:06-00:08] Close-up of their hand pulling a car door handle.
```

Rules:
- Timestamps must be within the generation duration (max 8s)
- Each segment should describe a coherent shot
- Transitions between timestamps are implicit (cut)
- Keep dialogue per segment proportional to segment duration

---

## Prompt Examples by Footage Type

### Nature / Establishing shot (Flow strength)
```
Aerial drone sweep over a vast emerald rainforest canopy at golden hour,
camera slowly descending through a break in the trees to reveal a hidden
waterfall cascading into a turquoise pool below. Mist rises from the
water's surface. National Geographic documentary style, vivid saturated
colors, warm golden light, awe-inspiring scale. The sound of rushing
water grows louder as the camera descends, birds calling in the distance.
```

### Tech / Product shot (Flow strength)
```
Slow dolly-in close-up of a cutting-edge microprocessor on a matte black
surface, rotating gently on a turntable. Circuit traces glow with subtle
blue light. Tiny reflections dance across the silicon surface. Apple
product launch style, ultra-clean studio lighting, shallow depth of field,
dark background with a single soft key light from above. No sound except
a quiet electronic hum.
```

### Atmospheric / Mood piece (Flow strength)
```
Static medium shot of an empty cobblestone alley in an old European city
during heavy rain at night. Warm light spills from a single open doorway
halfway down the alley. Puddles reflect neon signs and streetlamps.
A lone umbrella rolls slowly across the wet stones. Film noir aesthetic,
desaturated with isolated warm tones, moody and contemplative. Rain sounds,
distant thunder, the faint echo of jazz from behind the lit doorway.
```

### Human figure (moderate — consider Sora/Runway fallback)
```
Medium close-up of a middle-aged woman sitting at a kitchen table,
morning light streaming through a window to her left. She holds a
steaming cup of coffee with both hands, staring thoughtfully through
the window. Warm steam rises from the cup. Indie film aesthetic, soft
natural lighting, shallow focus, gentle handheld movement. The quiet
sounds of a suburban morning — birdsong, a distant lawnmower.
```

### Abstract / Conceptual (moderate — consider Runway fallback)
```
Macro lens extreme close-up of thick oil paint being squeezed from a tube
onto a white canvas, colors swirling and mixing in slow motion. Vivid
cadmium red meets ultramarine blue, creating fractal-like patterns as
they blend. Studio lighting from above, shallow depth of field, black
background. Art documentary style, mesmerizing, meditative. Only the
quiet sound of paint and brush.
```
