# xLights Scene & Combination Cookbook

> **Living document.** Volume 4 in the series. Where Volume 3 catalogs individual effects, this volume catalogs **scenes**: named, multi-prop, multi-layer combinations with a musical purpose — the repertoire a sequencer (human or model) composes from before reaching for individual effects.
>
> Each scene is a testable unit. Scenes carry a **status** (`PROPOSED → TESTING → KEEP / CUT`) and a test log entry. Nothing graduates to KEEP until it's been verified on real lights at viewing distance. Cut scenes stay in the graveyard (§9) with the reason — negative results are knowledge too.
>
> **Version:** 0.1 — June 2026
> **Assumes:** the generic display archetypes from Volume 1 §3 (Hero, Rhythm, Canvas, Frame, Accent, Character, Atmosphere) and the master-view architecture from Volume 2 §7. Render styles per Volume 2 §6; effect specs per Volume 3.

---

## Table of Contents

1. [Scene Schema](#1-scene-schema)
2. [Prerequisite: Group Architecture for Scenes](#2-prerequisite-group-architecture-for-scenes)
3. [Bed + Feature Scenes](#3-bed--feature-scenes)
4. [Showpiece Scenes](#4-showpiece-scenes)
5. [Build & Release Scenes](#5-build--release-scenes)
6. [Quiet & Transitional Scenes](#6-quiet--transitional-scenes)
7. [Spatial & Conversational Scenes](#7-spatial--conversational-scenes)
8. [Testing Protocol](#8-testing-protocol)
9. [The Graveyard (Cut Scenes)](#9-the-graveyard-cut-scenes)
10. [Scene Test Log](#10-scene-test-log)
11. [Sources & Prior Art](#11-sources--prior-art)
12. [Changelog](#12-changelog)

---

## 1. Scene Schema

Every scene entry has:

- **ID & Status:** `SC-NN` and lifecycle state.
- **Musical slot:** where it belongs (Vol 1 §2 taxonomy) and energy band (1–5).
- **Stack table:** every participating row, top-to-bottom in master-view order, with render style, layers, effects, and blend modes.
- **Why it works:** the perceptual/musical logic.
- **Variants & escalation:** chorus-1 vs final-chorus versions.
- **Failure modes:** what breaks it.
- **Prior art:** where the pattern was observed.

Stack table format:

| Row (master-view order) | Render style | Layer | Effect | Blend | Notes |

A blank Layer column row means the row has a single layer (Normal). Energy/intensity values are starting points, not gospel.

---

## 2. Prerequisite: Group Architecture for Scenes

Scenes depend on groups existing. Beyond the Vol 2 §7 hierarchy, prior art adds one crucial pattern:

**Subtractive groups.** Pro sequence vendors maintain groups like *Whole House Less Mega Tree*, *Whole House Less Mini Trees & Arches*, alongside the zone and prop-type groups. The point: when you want a whole-display background **plus** a clean feature on one prop, you put the bed on the subtractive group instead of the full ALL group. The featured prop never receives the bed at all — no blending arithmetic, no override ordering to reason about, no bed ghosting through the feature. This is the single most robust way to do "background + things on top," and it works identically whether Allow Blending Between Models is on or off.

Generic-display group set this cookbook assumes:

```
G0-ALL                  (everything)
G0-ALL-LESS-HERO        (everything except the mega tree)        <- subtractive
G0-ALL-LESS-HERO-RHYTHM (everything except tree, arches, minis)  <- subtractive
G1-LEFT / G1-RIGHT      (yard halves, for call-response)
G2-HERO    (mega tree [+ topper star as submodel/model])
G2-RHYTHM  (arches + mini trees + canes)
G2-FRAME   (house outline)
G2-ACCENT  (star, spinners, snowflakes)
G2-CANVAS  (matrix)
G9-STROBE-OVERLAY       (bottom of master view; always wins)
```

Maintenance rule from prior art: **add groups freely** (it doesn't disturb existing sequences and re-renders cleanly), but be careful *removing models from* groups — that silently changes every sequence using them; prefer creating a new group.

---

## 3. Bed + Feature Scenes

### SC-01 · The Standard Stack — `PROPOSED`
*The default state of the display. ~60% of any song lives here.*

- **Musical slot:** verses, choruses, anywhere. Energy 2–4 (parameter-scaled).
- **Stack:**

| Row | Render style | Layer | Effect | Blend | Notes |
|---|---|---|---|---|---|
| G0-ALL-LESS-HERO | Default (canvas) | L1 | Color Wash, 30–40% | Normal | The bed. Palette = section script |
| G2-HERO | Default | L3 | Color Wash 25% | Normal | Hero's own dim bed |
| | | L2 | *Feature effect* (Spirals/Morph/Bars per Vol 3) | Normal | The musical statement |
| | | L1 | Twinkle, low density | Max | Sparkle |
| G2-RHYTHM | Per Model | L1 | Single Strand chase on beat | Normal | The drummer |

- **Why it works:** subtractive group keeps the hero clean for its 3-layer stack; the frame/accents/canvas inherit the bed so the display never looks broken; one feature, one rhythm voice, one bed — the Vol 3 §11 "one feature per moment" rule embodied.
- **Escalation:** raise bed to 50%, feature speed +curve, Twinkle density up. That alone carries chorus 1 → 2.
- **Failure modes:** bed too bright (competes with feature); feature + rhythm in the same color (reads as one mush — separate palettes).
- **Prior art:** vendor group lists (Showstopper); standard 2–4 layer hero stacks observed across vendor sequences.

### SC-02 · Counter-Rotating Spirals — `PROPOSED`
*The mega tree showpiece-within-the-stack.*

- **Musical slot:** chorus feature, instrumental hooks. Energy 3–4.
- **Stack:**

| Row | Render style | Layer | Effect | Blend | Notes |
|---|---|---|---|---|---|
| G2-HERO | Default | L2 | Spirals, direction A, color set 1 | Normal | |
| | | L1 | Spirals, direction B (opposite), color set 2 | Average (try Max) | Counter-rotation |
| G0-ALL-LESS-HERO | Default | L1 | Color Wash 30% matching color set 1 | Normal | Ties yard to tree |

- **Why it works:** opposing motion creates interference patterns the eye can't predict — the manual itself calls out two opposing spirals on a mega tree as a signature stunning combination. Tying the yard wash to one of the two spiral palettes makes the tree read as the source of the display's color.
- **Variants:** thick+slow vs thin+fast pairs; one spiral white for a candy-cane look; speed value-curves in opposite phase for a "breathing" rotation.
- **Failure modes:** both layers same brightness + similar colors = visual mud; Average blend halves brightness — compensate or use Max.
- **Prior art:** xLights manual (Layers chapter); ubiquitous in vendor mega-tree effect packs.

### SC-03 · Split-House Dual Texture — `PROPOSED`
*One effect, two zones, two colors — via Sub-Buffer, no extra groups needed.*

- **Musical slot:** bridges, dual-instrument passages. Energy 2–3.
- **Stack:**

| Row | Render style | Layer | Effect | Blend | Notes |
|---|---|---|---|---|---|
| G0-ALL | Default | L2 | Fire (or Plasma), color A, Sub-Buffer = left half | Normal | Manual's own worked example |
| | | L1 | Fire, color B, Sub-Buffer = right half | Normal | |

- **Why it works:** the Sub-Buffer redefines the render area per layer, so each half renders a *complete* effect rather than a cropped one — the documented distinction from masking. Two-zone color conversation without touching the group architecture.
- **Variants:** animate the Sub-Buffer boundary with value curves so the split point travels with the music.
- **Prior art:** xLights manual Layer Settings (whole-house Fire sub-buffer example).

---

### SC-15 · Galaxy Swirl Bed — `PROPOSED`
*A living bed that breathes, with an organic hero over it.*

- **Musical slot:** dreamy verses, atmospheric choruses, instrumental pads. Energy 2–3.
- **Stack:**

| Row | Render style | Layer | Effect | Blend | Notes |
|---|---|---|---|---|---|
| G0-ALL-LESS-HERO | Default (canvas) | L1 | Galaxy, slow, cool palette | Normal | The swirling bed — never a flat wash |
| G2-HERO | Default | L2 | Butterfly, color set 2 | Normal | Organic hero feature |
| | | L1 | Color Wash 20% | Normal | Hero's own dim bed |
| G2-ACCENT | Per Model | L1 | Twinkle, low | Max | Sparkle |

- **Why it works:** Galaxy gives a non-repeating, alive background that reads richer than a Color Wash; Butterfly's curved organic motion contrasts it, and the two curved effects stay distinct because one is the bed and one is the focal.
- **Failure modes:** both at full brightness compete (keep the bed ≤30%); Galaxy too fast reads as static noise.
- **Prior art:** atmospheric living-bed pattern; original — untested idea.

---

## 4. Showpiece Scenes

### SC-04 · The Drop Formula — `PROPOSED`
*The biggest 2 seconds in the show.*

- **Musical slot:** the drop. Energy 5. Use <= 2 per song.
- **Stack (timeline, not just layers):**

| Phase | Row | Effect | Notes |
|---|---|---|---|
| Build peak (last beat) | G0-ALL | **Off** | 2–4 frame blackout. Explicit Off, not empty cells |
| Impact (1–2 frames) | G0-ALL | On, white, 100% | The flash |
| Release (2–8 bars) | G0-ALL | Shockwave from center, full palette | Default canvas: one wave across the entire yard |
| Release | G2-HERO | Fast Spirals or Pinwheel | Hero takes over motion |
| Release | G2-RHYTHM (Per Model) | Single Strand double-time | |
| Release | G9-STROBE-OVERLAY | Strobe, <=1s | Stinger garnish only |

- **Why it works:** the blackout is the setup — contrast principle (Vol 1 §1). The single group-canvas Shockwave reads as one physical wave through the yard, which per-model pops cannot replicate.
- **Failure modes:** skipping the blackout (drop lands flat); strobe held past 1s; using it for every chorus (devalues it).
- **Prior art:** Vol 1 §4.3 drop formula; universal in EDM-genre vendor sequences (e.g., the famously popular *Blinding Lights* sequences).

### SC-05 · Shaped Reveal Chorus — `PROPOSED`
*Texture alive inside lyrics or shapes.*

- **Musical slot:** title-lyric moments, hook lines. Energy 3.
- **Stack:**

| Row | Render style | Layer | Effect | Blend | Notes |
|---|---|---|---|---|---|
| G2-CANVAS | Default | L2 | Bars or Plasma, full palette | Normal | The living texture |
| | | L1 | Text (the lyric) or Shape | **1 is Mask** | Texture shows only inside glyphs |
| G0-ALL-LESS-HERO-RHYTHM | Default | L1 | Color Wash 25% | Normal | Quiet bed so the canvas owns focus |

- **Why it works:** masked texture reads as premium production value at near-zero render cost; polarity flip (UnMask) gives the inverse for the repeat.
- **Failure modes:** text too small for canvas density (Vol 3 §8 limits); busy effects behind small glyphs destroy legibility — bars beat plasma for thin fonts.
- **Prior art:** Vol 2 §9.2; mask/unmask usage per AusChristmasLighting threads and the manual's blending chapter.

### SC-06 · Persistent Trail Finale — `PROPOSED`
*Accumulating light that doesn't let go.*

- **Musical slot:** finales, last-chorus walls of sound. Energy 4.
- **Stack:**

| Row | Render style | Layer | Effect | Blend | Notes |
|---|---|---|---|---|---|
| G2-HERO | Default | L1 | Meteors (implode), **Persistent ON** | Normal | Trails accumulate until the tree is full |
| G2-FRAME | Default | L1 | Marquee | Normal | Steady motion under the accumulation |
| (at release) | G2-HERO | | **Off**, then next scene | | Off clears the persistent buffer |

- **Why it works:** persistence turns motion into accumulation — a visual crescendo that matches a sustained final chord; the documented buffer behavior (frames remain until overwritten) is the mechanism.
- **Failure modes:** forgetting the Off reset (trail garbage bleeds into the next section).
- **Prior art:** manual Layer Settings (Persistent); Vol 2 §9.5.

---

### SC-16 · Radiant Fan Bloom — `PROPOSED`
*A flower of light that opens with the music.*

- **Musical slot:** builds into a chorus, instrumental reveals, key lifts. Energy 3–4.
- **Stack:**

| Row | Render style | Layer | Effect | Blend | Notes |
|---|---|---|---|---|---|
| G2-HERO | Default | L2 | Fan, center-out, full palette | Normal | The bloom |
| | | L1 | Color Wash 25% | Normal | Hero bed |
| G2-RHYTHM | Per Model | L1 | Bars on beat | Normal | Linear rhythm under the radial feature |
| G0-ALL-LESS-HERO-RHYTHM | Default | L1 | Color Wash 30% | Normal | The bed |

- **Why it works:** Fan's radial opening reads as a bloom/burst that physically grows with the build; pairing a radial feature with a *linear* rhythm (Bars) keeps the two voices from mushing into one.
- **Failure modes:** Fan on a linear prop reads as nothing — keep it on the hero/canvas; too many petals at low energy looks busy.
- **Prior art:** radial-reveal pattern; original — untested idea.

### SC-17 · Kaleidoscope Canvas — `PROPOSED`
*The matrix as a premium, asset-free showpiece.*

- **Musical slot:** instrumental hooks, psychedelic bridges, solo spotlights. Energy 3–4.
- **Stack:**

| Row | Render style | Layer | Effect | Blend | Notes |
|---|---|---|---|---|---|
| G2-CANVAS | Default | L1 | Kaleidoscope, full palette, slow rotation | Normal | The storyteller |
| G0-ALL-LESS-HERO | Default | L1 | Color Wash 20% | Normal | Quiet bed so the canvas owns focus |

- **Why it works:** the matrix is the storyteller (Vol 3 §6); a kaleidoscope is premium motion with no assets, and its symmetry reads as deliberately "designed."
- **Failure modes:** kaleidoscope on small non-matrix props is invisible — canvas only; too fast reads as chaos rather than pattern.
- **Prior art:** matrix shader/effect tradition; original — untested idea.

---

## 5. Build & Release Scenes

### SC-07 · The Additive Build — `PROPOSED`
*Eight bars of rising inevitability.*

- **Musical slot:** pre-chorus / pre-drop builds. Energy ramps 2→5.
- **Stack (additive timeline; rows join every 2 bars):**

| Enters | Row | Effect | Curve |
|---|---|---|---|
| Bar 1 | G2-FRAME | Color Wash | brightness 20→60% |
| Bar 3 | G2-RHYTHM (Per Model) | Single Strand | speed ramp |
| Bar 5 | G2-HERO | Fill (bottom-up) + Spirals above | Fill position curve to bar 8; spiral speed ramp |
| Bar 7 | G2-ACCENT | Shimmer | short |
| Bar 8 | G2-HERO | Shockwave (contracting) | the inhale |
| Bar 8 end | → SC-04 | | |

- **Why it works:** additive layering *is* the musical build made visible; contracting shockwave at the peak is the inhale before the exhale of the drop.
- **Failure modes:** starting too bright (nowhere to go); linear curves (use ease-in — the difference between mechanical and musical, Vol 2 §11.1).
- **Prior art:** Vol 1 §4.3 build row; accelerating-spiral builds throughout vendor mega-tree packs.

### SC-08 · The Brightness Envelope Pulse — `PROPOSED`
*The whole display breathes on the beat — without touching any effect.*

- **Musical slot:** grooves, four-on-the-floor sections. Energy 3.
- **Stack:**

| Row | Render style | Layer | Effect | Blend | Notes |
|---|---|---|---|---|---|
| G0-ALL | Default | L2 | Any bed/texture combination | Normal | Whatever the section is doing |
| | | L1 | Color Wash white→black, value-curve bouncing on beat | **Subtractive** | The envelope |

- **Why it works:** one curve modulates everything beneath it — beat-ducking as a compositing operation. Community-documented recipe; more controllable than out-transitions.
- **Variants:** sidechain feel = sharp dip on the kick, fast recover; half-time pulse for half-time sections.
- **Prior art:** AusChristmasLighting subtractive-wash recipe; Vol 2 §9.3.

---

## 6. Quiet & Transitional Scenes

### SC-09 · Snowfall Hush — `PROPOSED`
- **Musical slot:** quiet bridges, ballad verses, the breath after a big chorus. Energy 1.
- **Stack:** G0-ALL (Default): L2 Color Wash deep blue 15% / L1 Snowflakes sparse, Max blend. G2-ACCENT: Twinkle low. Everything else **dark** — the restraint is the scene.
- **Why it works:** Vol 1 §1 contrast doctrine; the cheapest "beautiful" available, and it buys impact for whatever follows.
- **Prior art:** ubiquitous ballad treatment across vendor Christmas sequences.

### SC-10 · Curtain Section-Open — `PROPOSED`
- **Musical slot:** verse→chorus boundary, song open. Energy 2→3.
- **Stack:** G2-CANVAS or G0-ALL (Default): L1 Curtain (open, from center) over the incoming scene's bed on L2 — curtain as transition rather than effect. Alternatively per-row in/out wipe transitions (Vol 2 §5) when only one prop changes.
- **Why it works:** borrows a century of theater language; the audience knows "curtain opening = something is starting" without being taught.

### SC-11 · The Handoff — `PROPOSED`
*Moving the audience's eye deliberately from prop A to prop B.*

- **Musical slot:** instrument changes (verse vocal → guitar fill), any focus shift. Energy any.
- **Stack (timeline):** A's feature gets an out-transition (fade/wipe, ~0.5–1s) while a Morph effect travels across G0-ALL from A's position toward B (start/end blocks aimed via Morph's positioning); B's feature enters with an in-transition timed to the Morph's arrival.
- **Why it works:** the eye follows motion; the morph is a literal pointer. Without it, focus changes read as "something turned off."
- **Failure modes:** morph slower than the musical gesture; both features at full brightness simultaneously.

---

### SC-18 · Ember Glow — `PROPOSED`
*A warm, living glow a flat wash can't give.*

- **Musical slot:** warm intense bridges, slow-burn builds, candle-lit ballads. Energy 2–3.
- **Stack:** G0-ALL (Default): L2 Plasma, warm palette (red/orange/amber + 1 cool anchor) | L1 Fire on G2-FRAME or the hero base, low, **Max** — embers licking up. G2-ACCENT: Twinkle gold, low.
- **Why it works:** Fire + Plasma read as a genuinely warm, moving glow that a Color Wash can't fake; the single cool anchor keeps it from collapsing into one orange mush on LEDs (Vol 3 LED-contrast rule).
- **Failure modes:** Fire across the whole display reads as flat orange — keep it to frame/hero; no cool anchor → the tonal subtlety is invisible.
- **Prior art:** warm-wash tradition; original — untested idea.

### SC-19 · Ripple Reflections — `PROPOSED`
*Calm concentric motion instead of a still wash.*

- **Musical slot:** gentle verses, ambient interludes, "water/light" lyrics. Energy 1–2.
- **Stack:** G0-ALL-LESS-HERO (Default): L1 Ripple, slow, cool palette — concentric gentle waves. G2-HERO (Default): L1 Color Wash 20%. G2-ACCENT: Twinkle low, Max.
- **Why it works:** Ripple's slow concentric motion reads as calm/water and is a restful, *moving* alternative to a flat wash for quiet sections — variety without raising the energy.
- **Failure modes:** Ripple too fast reads as energetic (keep it slow); on tiny props it's invisible — broad groups only.
- **Prior art:** ambient water pattern; original — untested idea.

---

## 7. Spatial & Conversational Scenes

### SC-12 · Call and Response — `PROPOSED`
- **Musical slot:** call-response vocals, trading instrument bars. Energy 2–4.
- **Stack:** G1-LEFT and G1-RIGHT (Default canvas each), alternating: the call phrase fires the left group's feature (e.g., Bars sweeping inward), response fires the right. G2-FRAME holds a neutral dim bed so the inactive half isn't dead black (unless the song's spareness wants it).
- **Why it works:** stereo made physical; the yard becomes the arrangement.
- **Variants:** front/back zones for depth instead of L/R; per-phrase color identity (call=warm, response=cool).
- **Prior art:** Vol 1 §2 vocal taxonomy; standard duet treatment in singing-face sequences.

### SC-13 · Strobe Overlay Stingers — `PROPOSED`
- **Musical slot:** orchestral hits, gunshot SFX, cymbal chokes. Energy 5, <=1s.
- **Stack:** G9-STROBE-OVERLAY (bottom of master view, so it wins over everything per render order): On white 100% 1–2 frames, or Strobe <=1s, exactly on the hit marks. Whatever else is playing is irrelevant — that's the point of the overlay row.
- **Why it works:** guaranteed-priority punctuation with zero coordination cost against the rest of the sequence.
- **Failure modes:** Vol 3 §11.7 budget violations; using it as texture.

### SC-14 · Escalating Chorus Series — `PROPOSED`
*One motif, three sizes. The structural spine of a whole song.*

- **Musical slot:** chorus 1 / chorus 2 / final chorus. Energy 3 → 4 → 5.
- **Definition:** pick a chorus scene (SC-01 with a signature feature, or SC-02). Then:
  - **Chorus 1:** scene at ~70% — bed dimmer, Twinkle off, rhythm at half density.
  - **Chorus 2:** full scene.
  - **Final chorus:** full scene + accent layer (SC-13 stingers on downbeats) + key-change palette swap if the song has one + topper star sustained.
- **Why it works:** repetition-with-escalation doctrine (Vol 1 §1); viewers recognize the motif and *feel* the growth.
- **Failure mode:** playing the full version at chorus 1 — the song has nowhere to go.

---

## 7b. Composite Stacks (single-group effect blends)

A *scene* layers effects across MANY groups; a **composite** layers 2–3 effects on the **same**
group so they COMBINE into one rich look — the depth Morph/Galaxy/Plasma get when stacked. Code
realizes these (`weave.expand_composite`): each layer shares the group + span, with a blend mode on
the upper layers and a rotated palette so the effects read distinctly instead of one hiding another.
The generator may design `composites`; code also drops one curated stack on the hero at the peak.

Curated combos (`weave.CURATED_COMPOSITES`):

| Name | Stack (base → top) | Reads as | Best moment |
|---|---|---|---|
| `kaleidoscope` | Morph + Morph (Max) | shifting symmetric wash | peak / instrumental hook |
| `swirl` | Galaxy + Butterfly (Max) | living organic swirl | dreamy chorus / bridge |
| `ember` | Plasma + Fire (Brightness) | warm flickering depth | warm build / ballad |
| `bloom` | Spirals + Fan (Max) | radial bloom | lift into a chorus |

- **Why it works:** blend + per-layer palette makes two effects combine rather than the top one
  occluding the base; direction-capable layers (Bars/Wave/Garlands/SingleStrand/Butterfly/Galaxy)
  additionally counter-phase. Keep composites to a FEATURE group — stacking the whole yard is mush.
- **Failure modes:** >3 layers (layer-budget clamp drops them); two beds with no blend (the top wins
  and you've wasted a layer); a composite on a tiny prop (the combine needs pixels to read).

---

## 8. Testing Protocol

How a scene moves through the lifecycle:

1. **PROPOSED** — specified here, with prior art noted.
2. **TESTING** — built as a 30–60 second test cell in a dedicated `_SceneTest` sequence (one scene per labeled section, against a click/representative song snippet). Render and check, in order:
   - **Preview check:** does it composite as specified? (Render-order regressions surface here — Vol 2 §11.7 test-pattern logic.)
   - **Yard check:** on real lights, from the street, at night. Brightness, color separation, and density limits only exist out there.
   - **Squint check:** at distance with eyes squinted — is there exactly one focal point?
   - **Mute check:** with audio imagined/muted — does the structure read?
3. **KEEP** — passes; save each row's layer stack as Effect Presets named `SCNN-<row>` in the scene preset group so the scene is droppable in future sequences.
4. **CUT** — fails twice (after one revision attempt); move to §9 with the reason.

Log every test in §10. One scene per test session changes — otherwise you can't attribute results.

---

## 9. The Graveyard (Cut Scenes)

Scenes that failed testing, kept so they aren't reinvented. Format: ID, what it was, why it died.

| ID | Scene | Cut reason |
|---|---|---|
| — | *(empty — nothing tested yet)* | |

---

## 10. Scene Test Log

| Date | Scene | Status change | Conditions (preview/yard, distance) | Findings |
|---|---|---|---|---|
| — | | | | |

---

## 11. Sources & Prior Art

- **Showstopper Sequences, "Get Your Group On"** — the subtractive-group pattern (*Whole House Less X* group families) and group-maintenance rules; the "display as a single canvas, apply effects to parts of the canvas" mental model.
- **xLights Manual** — Layers chapter (200-layer limit; red-wash-plus-snowflakes mask inversion; opposing spirals callout), Layer Settings (Sub-Buffer split-house Fire example; Persistent behavior), Layer Blending (mask/transition mechanics), Render All (authoritative render-direction statement).
- **AusChristmasLighting** — "Layering effects" thread (overlay-group ordering tricks), subtractive brightness-envelope recipe.
- **Pixel Pro Displays** — layering/blending tutorial series (group-level rendering and blend-setting walkthroughs).
- **Vendor sequence observation** — xTreme Sequences, RGB Sequences (*Blinding Lights* et al.), Showstopper: escalating-chorus structure, drop construction, mega-tree spiral pairings. `TODO:` per-sequence dissections via the Vol 1 §10 mining workflow feed new scenes here.
- Volumes 1–3 of this series.

---

## 12. Changelog

| Version | Date | Changes |
|---|---|---|
| 0.1 | 2026-06-09 | Initial cookbook: schema, group architecture incl. subtractive groups, 14 scenes (all PROPOSED), testing protocol, graveyard & log scaffolding |
| 0.2 | 2026-06-16 | +5 variety scenes (PROPOSED) spotlighting under-used effects: SC-15 Galaxy Swirl Bed, SC-16 Radiant Fan Bloom, SC-17 Kaleidoscope Canvas, SC-18 Ember Glow (Fire/Plasma), SC-19 Ripple Reflections |

<!--
Editing conventions:
- New scenes get the next SC-NN, status PROPOSED, and a prior-art note (or "original — untested idea").
- Status changes only via a §10 log entry.
- KEEP scenes must name their preset group entries.
- Cut != delete: move to §9 with the reason.
-->
