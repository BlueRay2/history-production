# Kling AI Camera Movement Reference

Complete camera motion vocabulary for Kling AI video generation. All keywords tested and verified across Kling 2.5–3.0.

## CRITICAL: Kling reverses pan/tilt terminology

Standard cinematography → Kling AI mapping:

| Standard term | Kling keyword | Actual movement |
|--------------|---------------|-----------------|
| Pan left/right | **tilt left/right** | Horizontal camera rotation |
| Tilt up/down | **pan up/down** | Vertical camera rotation |

This is the single most common mistake in Kling prompting. Using "pan left" in Kling produces vertical movement.

---

## Depth movements

| Keyword | Effect | Best for |
|---------|--------|----------|
| `slow dolly in` | Camera physically moves toward subject with parallax | Emotional reveals, tension building |
| `dolly out` / `pull back` | Camera retreats from subject | Context reveals, endings |
| `push in` | Faster dolly in | Urgency, dramatic emphasis |
| `crash zoom` | Rapid optical zoom | Shock moments, comedy |
| `zoom in` / `zoom out` | Optical zoom (no parallax) | Quick emphasis, surveillance feel |
| `dolly zoom` | Simultaneous dolly + counter-zoom (Vertigo effect) | Disorientation, psychological tension |

**Note:** Kling correctly distinguishes `dolly in` (physical move, parallax) from `zoom in` (optical, no parallax). Use this to your advantage.

## Horizontal and vertical

| Keyword | Effect |
|---------|--------|
| `tilt left` / `tilt right` | Horizontal camera rotation (what cinematographers call "pan") |
| `pan up` / `pan down` | Vertical camera rotation (what cinematographers call "tilt") |
| `truck left` / `truck right` | Camera slides laterally on rails |
| `pedestal up` / `pedestal down` | Camera physically raises/lowers |

## Orbit and rotation

| Keyword | Effect |
|---------|--------|
| `360-degree rotation` | Full orbit around subject |
| `orbit shot` | Partial arc around subject |
| `arc shot` | Quarter to half orbit |
| `camera roll` | Rotation around lens axis (Dutch angle) |
| `spiral up` | Rising orbit (helix path) |

## Tracking and following

| Keyword | Effect |
|---------|--------|
| `tracking shot` | Camera follows subject's movement path |
| `follow` | Camera trails behind subject |
| `side tracking shot` | Camera moves parallel to subject |
| `leading shot` | Camera moves ahead of subject |

## Special perspectives

| Keyword | Effect | Best for |
|---------|--------|----------|
| `FPV drone` | First-person drone flight | Action, exploration, reveals |
| `bird's eye view` | Directly overhead | Scale, patterns, maps |
| `drone shot` | Elevated aerial perspective | Establishing shots, landscapes |
| `POV shot` | Through character's eyes | Immersion, horror, gaming |
| `handheld` | Organic camera shake | Realism, documentary, urgency |
| `crane shot` | Sweeping vertical + horizontal | Grand reveals, transitions |
| `low angle` | Camera below eye level pointing up | Power, dominance, scale |
| `high angle` | Camera above eye level pointing down | Vulnerability, overview |

## Focus control

| Keyword | Effect |
|---------|--------|
| `rack focus` | Shift focus from foreground to background (or reverse) |
| `shallow depth of field` | Subject sharp, background blurred |
| `snap focus` | Instant focus change |
| `deep focus` | Everything sharp front to back |

## Speed modifiers

Attach directly to any movement keyword:
- `slow` — deliberate, contemplative
- `gentle` — subtle, barely perceptible
- `fast` — energetic, urgent
- `rapid` — almost violent speed
- `accelerating` — starts slow, builds speed
- `decelerating` — starts fast, settles

Example: `slow dolly in`, `rapid crash zoom`, `gentle orbit shot`

## Static shots

| Keyword | Effect |
|---------|--------|
| `fixed lens` | No camera movement |
| `static tripod` | Locked camera position |
| `locked off` | Completely static frame |

Static shots work well when combined with subject motion: `static tripod, the figure slowly walks away from camera into the fog`

---

## Production patterns — camera + scene combinations

### Reveal pattern
```
Camera begins on [detail/close-up], then [slow dolly out / crane up] to reveal [wider context]
```

### Tension build pattern
```
[Slow push in] toward [subject], background [blurs / darkens], ending in [tight close-up]
```

### Environmental sweep pattern
```
[Drone shot / crane shot] slowly [panning across / tracking through] [environment], camera [descends / ascends] to settle on [focal point]
```

### Product showcase pattern
```
[Orbit shot] around [product] on [surface], [rack focus] from [detail] to [full product], [shallow depth of field]
```

### Documentary interview feel
```
[Static tripod], [shallow depth of field], subject [centered / rule-of-thirds], [gentle handheld micro-movements]
```
