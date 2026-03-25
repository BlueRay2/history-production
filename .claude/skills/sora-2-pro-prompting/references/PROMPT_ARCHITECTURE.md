# Sora 2 Pro — Prompt Architecture Reference

## Table of Contents
1. [Prompt Template](#prompt-template)
2. [Camera Movement Vocabulary](#camera-movement-vocabulary)
3. [Shot Type Reference](#shot-type-reference)
4. [Style and Format Keywords](#style-and-format-keywords)
5. [Lighting Descriptions](#lighting-descriptions)
6. [Composition and Depth](#composition-and-depth)
7. [Color Palette Anchoring](#color-palette-anchoring)
8. [Genre Presets](#genre-presets)
9. [Worked Examples](#worked-examples)
10. [Anti-Patterns](#anti-patterns)
11. [Storyboard Multi-Shot Protocol](#storyboard-multi-shot-protocol)
12. [Image-to-Video Specific Tips](#image-to-video-specific-tips)

---

## Prompt Template

Use this as the structural backbone for every prompt. Not every block is required — omit irrelevant ones rather than leaving them empty.

```
[STYLE]: {Film format, lens, post-processing feel, shutter}
[GRADE]: {Highlight treatment, mid tone cast, shadow behavior, grain}
[LENS]: {Focal length, filter (Pro-Mist, CPL), aperture feel}
[LIGHTING]: {Key source direction + quality, fill, rim, atmosphere}
[LOCATION]: {Setting with foreground / midground / background elements}
[SUBJECT]: {Who/what, clothing, posture, distinguishing features}
[ACTION]: {1–3 sequential beats with timing if >5s}
[CAMERA]: {Shot type + single movement descriptor}
[PALETTE]: {3–5 named colors}
[AUDIO]: {Ambient sound, dialogue, music mood — if applicable}
```

For shorter prompts (B-roll, simple scenes), compress into natural prose while preserving information density. The block format is a *planning* tool — the final prompt can be flowing text.

---

## Camera Movement Vocabulary

These terms produce reliable, predictable camera behavior in Sora 2. Each entry is tested and community-validated.

### Lateral Movement
- `slow dolly left` / `slow dolly right`
- `tracking left to right` / `tracking right to left`
- `shoulder-mounted slow dolly left`
- `slow arc in` (curves toward subject)
- `slow arc around` (orbits subject)
- `over-shoulder arc`

### Depth Movement
- `slow push-in` (dolly toward subject)
- `slow pull-back` (dolly away from subject)
- `creeping dolly forward`
- `slow zoom-in` (use sparingly — lens zoom, not dolly)

### Vertical Movement
- `slow crane up` / `slow crane down`
- `overhead drone shot descending`
- `low-angle tilt up`
- `high-angle tilt down`

### Handheld and Special
- `handheld eng camera` (news/documentary feel)
- `shoulder-mounted steady` (controlled handheld)
- `FPV-style flight` (first-person drone movement)
- `locked-off tripod` / `static camera` (no movement)
- `slow drift` (subtle, almost imperceptible movement)

### Movements That Degrade Quality (avoid)
- `whip pan` — too fast, causes artifacts
- `rapid zoom` — inconsistent results
- `spin` / `rotation` — almost always fails
- Combined movements: `pan while dollying and tilting` — pick ONE

---

## Shot Type Reference

### Framing
- `extreme wide shot` — full environment, subject is small
- `wide establishing shot eye level` — environment with clear subject
- `full shot` — head to toe
- `medium shot` / `medium close-up` — waist up / chest up
- `close-up` — face fills frame
- `extreme close-up` — single feature (eye, hand, texture)
- `over-the-shoulder` — subject seen past another's shoulder
- `two-shot` — two subjects in frame

### Angle
- `eye level` — neutral, standard
- `low-angle` — looking up at subject (power, grandeur)
- `high-angle` — looking down at subject (vulnerability, context)
- `bird's-eye` / `overhead` — directly above
- `Dutch angle` — tilted horizon (unease, dynamism)
- `worm's-eye` — extreme low, near ground level

### Combined (Shot + Angle + Movement)
```
medium close-up, slight angle from behind, slow arc in
wide establishing shot, eye level, slow crane up
extreme close-up, low-angle, locked-off tripod
over-shoulder arc, medium shot, slow dolly right
```

---

## Style and Format Keywords

### Film Format (strongest style lever)
- `cinematic film shot in 35mm` — classic cinema look
- `shot with a mobile phone camera` — casual, authentic
- `IMAX-scale scene` — epic, vast
- `16mm black-and-white film` — documentary, vintage
- `anamorphic 2.0x lens` — wide cinematic, lens flares
- `180° shutter` — standard cinematic motion blur
- `digital capture emulating 65mm photochemical contrast` — high-end digital

### Post-Processing Feel
- `fine grain` — subtle film texture
- `subtle halation on speculars` — glow on highlights
- `Kodak-inspired grade` — warm, slightly desaturated
- `chromatic bloom` — dreamy highlight glow
- `soft vignette` — darkened edges
- `no gate weave` — steady frame (default for clean look)
- `pro-mist 1/4` — soft diffusion filter

### Genre/Aesthetic Presets
These single keywords set a strong visual direction:
- `cinematic` — photorealistic film look (default)
- `stop motion` — claymation-style animation
- `film noir` — high contrast B&W, dramatic shadows
- `anime` — Japanese animation style
- `cyberpunk` — neon-lit, futuristic, rain-soaked
- `dreamy` — soft focus, pastel, ethereal
- `hyper-realistic` — pushes photorealism to maximum
- `pixel art` — retro game aesthetic
- `claymation` — textured stop-motion feel
- `vintage VHS` — scan lines, color bleed, tracking artifacts

---

## Lighting Descriptions

Effective lighting prompts name **source direction, quality, and color temperature**. Always specify at least key light; add fill and rim for control.

### Patterns That Work Well
```
Soft window light with warm lamp fill, cool rim from hallway
Golden hour sunlight, sun 15° above horizon, long shadows
Single bare bulb, light pooling onto the scarred metal table
Warm key from overhead practical; cool spill from window
Overcast diffused daylight, flat and even, no harsh shadows
Neon signs casting magenta and cyan across wet pavement
Candlelight flicker, warm amber, deep shadows
Backlit silhouette, rim light only, no fill
```

### Lighting Vocabulary
- **Key light**: Primary illumination source
- **Fill light**: Softens shadows from key
- **Rim/edge light**: Highlights subject edges from behind
- **Practical light**: In-frame light sources (lamps, candles, screens)
- **Volumetric**: Visible light rays through atmosphere (fog, dust, smoke)
- **Motivated lighting**: Light that appears to come from a visible source

---

## Composition and Depth

Explicitly define spatial layers to prevent Sora from producing flat compositions.

### Three-Layer Rule
Always describe:
- **Foreground**: Objects nearest camera (railing, leaves, table edge)
- **Midground**: Primary subject and action
- **Background**: Environment context (buildings, sky, crowd)

### Depth of Field
- `shallow depth of field, sharp on subject, background rendered as soft bokeh`
- `deep focus, everything from foreground to infinity sharp`
- `rack focus from foreground object to midground subject`

### Focal Length Implications
- **24mm**: Wide, expansive, slight distortion at edges
- **35mm**: Standard wide, natural perspective
- **50mm**: Classic portrait, minimal distortion
- **85mm**: Tight portrait, compressed background
- **135mm+**: Telephoto compression, flattened layers

---

## Color Palette Anchoring

For visual consistency across a multi-shot sequence, name 3–5 palette colors and repeat them in every prompt.

```
Palette anchors: amber, cream, walnut brown, deep navy, copper
```

This creates a cohesive color world even when scenes change location. Sora responds well to named colors — use specific names (not "warm tones") like:
- `burnt sienna`, `slate blue`, `ivory`, `charcoal`, `sage green`
- `champagne gold`, `midnight blue`, `terracotta`, `frost white`

---

## Genre Presets

These compound descriptors set strong visual direction with minimal words:

```
90s documentary-style interview, 16mm grain, available light
Cinematic fashion editorial reel, anamorphic, high contrast
Music video visual, neon-lit, slow-motion, wide lens
Nature documentary, IMAX-scale, David Attenborough aesthetic
Corporate tech product launch, clean, modern, white studio
Sci-fi film trailer, volumetric fog, cyan-orange grade
Horror film opening, handheld, underexposed, shallow DOF
Wes Anderson symmetrical composition, pastel palette, 35mm
```

---

## Worked Examples

### Example 1: YouTube B-Roll — City Morning

```
Cinematic film shot in 35mm, shallow depth of field, 180° shutter.
Grade: Warm highlights with amber lift, neutral mids, soft blacks with
slight teal cast in shadows. Fine grain.

Dawn light rakes across a Manhattan intersection. Foreground: steam
rises from a subway grate, catching amber sunlight. Midground: a woman
in a charcoal wool coat crosses the street, coffee cup in hand, breath
visible in cold air. Background: yellow cabs queue at a red light,
their headlights haloed in morning mist.

Camera: Medium shot, eye level, slow tracking right to left.
She walks steadily, not looking at camera. At the end of the shot,
she pauses at the curb and glances up at the sky.

Palette anchors: amber, charcoal, cream, yellow, steel blue.
```

**Parameters**: 10s | 1080p | 16:9  
**Credits**: ~600 | **API**: ~$5.00

---

### Example 2: Product Hero Shot

```
IMAX-scale cinematic capture, anamorphic 2.0x lens, Black Pro-Mist 1/4.
Grade: Clean highlights, neutral mids, minimal shadow lift. No grain.

A single wireless headphone sits centered on a polished obsidian surface.
Camera begins on extreme close-up of the ear cup's brushed aluminum
texture, then pulls back slowly to reveal the full product.
Volumetric light beams cut diagonally from upper-right, casting long
geometric shadows. Background: pure black void with subtle blue
edge glow on the headphone's silhouette.

Camera: Extreme close-up pulling back to medium shot, slow steady
dolly back, locked tripod smoothness.

Palette anchors: obsidian black, brushed silver, deep cobalt, white.
```

**Parameters**: 5s | 1080p | 16:9  
**Credits**: ~200 | **API**: ~$2.50

---

### Example 3: Nature Documentary B-Roll

```
Nature documentary, IMAX-scale scene, digital capture emulating 65mm.
180° shutter. Subtle halation on water reflections.

Early morning in a temperate rainforest. Heavy mist drifts between
moss-covered Douglas firs. A creek runs through the foreground,
smooth stones visible beneath crystal-clear water. A single shaft of
sunlight pierces the canopy, illuminating a patch of ferns in the
midground. Tiny water droplets float in the light beam.

Camera: Wide establishing shot, eye level, slow crane up — starting
from creek level, rising to reveal the full forest cathedral above.
Everything is still except the drifting mist and flowing water.

Palette anchors: emerald green, moss, silver mist, bark brown, gold shaft.
```

**Parameters**: 10s | 1080p | 16:9  
**Credits**: ~600 | **API**: ~$5.00

---

### Example 4: Social Media Vertical — Food

```
Shot with a mobile phone camera, shallow depth of field, natural light.
Slight warm grade, no filters, authentic feel.

A hand slowly pours honey from a ceramic spoon onto a stack of golden
pancakes. The honey catches morning window light, creating amber
translucency. Steam rises from the stack. Foreground: edge of a
linen napkin and a fork. Background: soft bokeh of a sunny kitchen
window with herbs on the sill.

Camera: Extreme close-up, overhead angle, locked-off. No movement.
Only the honey pouring provides motion.

Palette anchors: amber, golden, cream, soft white, sage green.
```

**Parameters**: 5s | 1080p | 9:16  
**Credits**: ~200 | **API**: ~$2.50

---

### Example 5: Time-Coded Multi-Beat (8s+)

For durations above 5 seconds, use explicit time codes to sequence beats:

```
Cinematic 35mm, shallow depth of field, Kodak-inspired grade.

[0–3s]: Wide establishing shot of a dimly lit jazz club. Warm amber
practicals glow above a small stage. A saxophone player stands in
silhouette, instrument catching a single spotlight rim.

[3–6s]: Medium close-up, slow push-in. The saxophonist raises the
instrument, fingers finding position. We see concentration on their face,
sweat on their brow, eyes closed. Warm key from the stage spot.

[6–8s]: Extreme close-up of the saxophone bell as the first note sounds.
Golden brass fills the frame, vibrating with sound. Shallow DOF blurs
the audience into warm bokeh points behind.

Palette anchors: amber, brass gold, deep indigo, warm black.
Audio: Jazz club ambience, single saxophone note swelling.
```

**Parameters**: 8s | 1080p | 16:9  
**Credits**: ~360 | **API**: ~$4.00

---

## Anti-Patterns

Prompts that consistently produce poor results. Avoid these:

| Anti-Pattern | Why It Fails | Fix |
|---|---|---|
| `a beautiful cinematic scene` | Too vague, no visual specifics | Name exact subjects, lighting, camera |
| `camera pans while zooming and tilting` | Multiple simultaneous movements | Choose ONE movement |
| `a crowd of people talking and dancing` | Too many simultaneous actions | Focus on 1–2 subjects |
| `text saying "WELCOME"` | ~5% text readability | Add text in post-production |
| `rapid whip pan to the left` | Too fast, causes artifacts | Use `slow pan left` |
| `make it longer` / `1080p` in prompt text | Parameters are set outside the prompt | Set via UI/API parameters |
| Prompt under 20 words | Insufficient detail, random results | Aim for 50–200 words |
| Mixing languages in prompt | Confuses the model | Write entirely in one language |
| `a person jumping, then running, then climbing, then swimming` | 4+ actions degrade quality | Max 3 beats per clip |

---

## Storyboard Multi-Shot Protocol

When writing a sequence of connected shots (storyboard mode):

1. **Lock a character description** — write it once, copy exactly into every prompt:
   ```
   SUBJECT LOCK: A woman, early 30s, dark hair in a loose bun,
   wearing a navy wool coat over a cream turtleneck, brown leather bag.
   ```

2. **Lock a palette** — repeat the same 5 colors in every card:
   ```
   PALETTE LOCK: navy, cream, walnut brown, amber, slate gray.
   ```

3. **Write each card as an independent prompt** — Sora processes each storyboard card separately. Do not assume continuity between cards.

4. **Use consistent lighting direction** — if the sun is camera-left in card 1, keep it camera-left throughout unless the narrative demands a change.

5. **Number cards with shot types** for editor reference:
   ```
   CARD 1 / WIDE ESTABLISHING — exterior street, morning
   CARD 2 / MEDIUM CLOSE-UP — subject enters frame
   CARD 3 / CLOSE-UP — reaction shot
   CARD 4 / WIDE — new location reveal
   ```

---

## Image-to-Video Specific Tips

When using a still image as the first frame:

- The image **defines the opening composition** — prompt should describe motion FROM that composition, not contradicting what's visible.
- Keep the prompt focused on **what changes**: camera movement and subject action. Don't re-describe what's already in the image.
- Front or 45° facial angles produce the best lip-sync if dialogue is needed.
- If the image has a specific color grade, reference it: "Maintain the warm amber grade visible in the reference frame."
- Image-to-video costs the same credits as text-to-video at equivalent resolution and duration.
