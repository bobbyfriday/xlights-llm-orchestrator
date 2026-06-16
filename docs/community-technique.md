# Community Sequencing Technique — cited reference

Distilled from public xLights documentation and community sources, to ground the effect/scene
guidance (the Director cheat-sheet, the scene cookbook, `xlights-effects-catalog.md`) in
documented practice rather than guesswork. Every claim is cited. Where a source is a tutorial/
forum (taste, not spec) it's noted as such.

> Sourcing note: this is a *technique* digest from public docs. The parameterized **presets**
> (`looks.json`) come from mining real `.xsq` files — see `knowledge/xsq_extractor.py`. Web pages
> don't contain presets; to expand the preset catalog, feed more (rights-cleared) `.xsq` files
> through the miner.

## 1. Value curves — the highest-leverage technique

A value curve makes a *setting* change over the effect's duration in a non-linear way (Ramp,
Ramp Up/Down, etc.); the canonical use is a **Ramp on speed/brightness/thickness** to build or
fade across a phrase. Community tutorials call this "an easy way to make your show look twice as
good." The system already synthesizes these (`knowledge/value_curves.py`); the takeaway is to
reach for them more — builds, swells on held notes, intro/outro fades.
[Manual: Value Curves](https://manual.xlights.org/xlights/chapters/chapter-four-sequencer/value-curves) ·
[Learn Christmas Lighting — Value Curves](https://www.learnchristmaslighting.com/xlights-next-level-tips-value-curves-an-easy-way-to-make-your-show-look-twice-as-good/)

## 2. Buffers / rendering — what reads, and what's expensive

- **Default** = the model's Default buffer (for a group, that's *Per Preview*). **Single Line** lays
  all strands end-to-end on a 1-pixel line. **Per Preview** renders as the model is laid out in the
  preview. A whole-yard *gesture* wants Per Preview / group canvas; a *fill* wants Per Model.
- **Grid size matters for performance:** prefer **Minimal Grid**; large grids "significantly slow
  down rendering, particularly on effects like **Fan and Shockwave**." → keep Fan/Shockwave off
  huge whole-house canvases unless you need the one gesture.
- Per-Model render styles composite **top-to-bottom in model order**.
[Manual: Layer Settings](https://manual.xlights.org/xlights/chapters/chapter-four-sequencer/layers/layer-settings) ·
[Manual: Rendering](https://manual.xlights.org/xlights/chapters/chapter-four-sequencer/rendering)

## 3. Layering & blending

- Layers render **bottom → top**; the top layer sits over everything below. In the blend UI the
  current layer is "layer 1", the one beneath is "layer 2".
- **Max** keeps the brighter of the two values (the safe way to overlay an accent on a bed without
  occluding it — this is why woven cells default to Max over a base); **Min** keeps the darker.
- The manual's own advice: stack two effects and step through the modes — experience beats reading.
- **Masking / reveal:** put a shape on a top layer (e.g. **Curtain** in white) and set blend to
  **"1 is Mask" / "1 is UnMask"** so the layer below shows only inside (or outside) the shape — a
  premium reveal at near-zero cost. The sequence-level **"Allow Blending Between Models"** lets an
  earlier model's effect blend into a later one instead of starting from black.
[Manual: Layer Blending](https://manual.xlights.org/xlights/chapters/chapter-four-sequencer/layers/layer-blending) ·
[AusChristmasLighting — Layering effects](https://auschristmaslighting.com/threads/layering-effects.14957/)

## 4. Per-effect reference (xLights Manual)

What each effect actually renders as, the moment it suits, and a concrete tip. Descriptions are
from the manual's effect pages; "best for" blends the description with conventional use.

| Effect | Renders as | Best for | Tip |
|---|---|---|---|
| **Spirals** | 2D/3D spirals & helix | builds, mega-tree hooks | needs ≥2 colors; value-curve the speed for a build; set color-repeats 1–5 |
| **Bars** | straight multi-color bars moving across the model | driving rhythm, directional sweeps | pick a direction; cell-able as a beat carrier |
| **Pinwheel** | rotating radial rays | energetic rotation, round/star props | set # arms + twist; speed = energy |
| **Butterfly** | random swirling color patterns (10 styles) | organic / psychedelic | **style #2 is radial — great on round props (snowflakes, stars, globes)** |
| **Fan** | spiralling blades rotating CW/CCW | reveals, blooms into a chorus | grid-expensive — keep it on the hero/canvas, not the whole yard |
| **Galaxy** | a spiral that expands around the model | atmospheric, swirling bed | slow it down as a living bed (richer than a flat wash) |
| **Plasma** | cycling color, liquid organic movement | warm/organic bed | a true bed effect; pair a cool anchor so it isn't one mush |
| **Fire** | licks of flame | warm/intense moments | keep to frame/hero — full-display Fire reads as flat orange |
| **Ripple** | concentric spread like a drop in water | calm verses, "water" lyrics | keep it slow; broad groups only (invisible on tiny props) |
| **Shockwave** | a circle growing small→large (or reverse) | impact accents on a hit | hit-class (≤1 bar); grid-expensive on big canvases |
| **Color Wash** | a wash of cycling/blended color | the section bed | the default bed; keep it dim under features |
| **Curtain** | open/close wipe of color | section opens, transitions, masks | doubles as a transition and as a mask shape |

[Manual: Built-in Effects index](https://manual.xlights.org/xlights/effects) ·
[Spirals](https://manual.xlights.org/xlights/effects/off/spirals) ·
[Bars](https://manual.xlights.org/xlights/effects/off/bars) ·
[Pinwheel](https://manual.xlights.org/xlights/effects/off/pinwheel) ·
[Butterfly](https://manual.xlights.org/xlights/effects/off/butterfly) ·
[Fan](https://manual.xlights.org/xlights/effects/off/fan) ·
[Galaxy](https://manual.xlights.org/xlights/effects/off/galaxy) ·
[Plasma](https://manual.xlights.org/xlights/effects/off/plasma) ·
[Fire](https://manual.xlights.org/xlights/effects/off/fire) ·
[Ripple](https://manual.xlights.org/xlights/effects/off/ripple) ·
[Shockwave](https://manual.xlights.org/xlights/effects/off/shockwave)

## 5. Verification status

Tier-1 (spec-grade, from the manual): the effect descriptions, buffer/grid behavior, blend
semantics, value-curve mechanics. Tier-2 (tutorial/forum taste): the "best for" moments and the
masking workflow. None of the "best for" mappings have been render-verified here — the visual
critic + the cookbook's PROPOSED→test lifecycle remain the arbiters.

**Overview source:** [Listen To Our Lights](https://sites.google.com/site/listentoourlights/home/vcs2021)
(403 to automated fetch; included for provenance).
