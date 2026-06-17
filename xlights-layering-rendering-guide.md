# xLights Layering, Render Order & Render Styles: Reference & Best Practices

> **Living document.** Companion to the *Music-to-Effect Reference*. This one covers the rendering machinery: effect layers, layer blending, group ordering and render order, render/buffer styles, and the layer settings most people never touch. Getting these right is the difference between effects that fight each other and effects that compose.
>
> **Version:** 0.1 — June 2026
> **Status:** Initial draft. Verify version-specific behavior against your installed xLights release; the render engine evolves.

---

## Table of Contents

1. [The Mental Model](#1-the-mental-model)
2. [The Two Render Directions (The Rule Everyone Trips On)](#2-the-two-render-directions)
3. [Effect Layers](#3-effect-layers)
4. [Layer Blending Modes](#4-layer-blending-modes)
5. [Layer Settings: Buffer, Transitions, and Friends](#5-layer-settings-buffer-transitions-and-friends)
6. [Render Styles: Group vs Per-Model](#6-render-styles-group-vs-per-model)
7. [Group Ordering & Master View Strategy](#7-group-ordering--master-view-strategy)
8. [Allow Blending Between Models](#8-allow-blending-between-models)
9. [Recipes: Common Layering Patterns](#9-recipes-common-layering-patterns)
9b. [Per-Effect Layering Roles](#9b-per-effect-layering-roles)
10. [Performance & Render Hygiene](#10-performance--render-hygiene)
11. [What Else We Might Be Missing](#11-what-else-we-might-be-missing)
12. [Sources](#12-sources)
13. [Changelog](#13-changelog)

---

## 1. The Mental Model

Think of xLights rendering like a compositing pipeline, not a paint program:

- Every **model or group row** in the sequencer gets its own **render buffer** — a virtual 2D canvas whose shape is determined by the model geometry and the chosen buffer/render style.
- Every **effect** is drawn into a buffer on a **layer**. A model can have many layers; layers composite together via **blend modes** to produce that model's final output.
- Then all the model/group outputs composite together according to **render order** (their top-to-bottom position in the master view) and the **Allow Blending Between Models** setting.
- The result is sampled down to actual pixels (nodes) for output.

So there are *two* compositing stages: **layers within a row**, then **rows against each other**. Most confusion comes from conflating the two.

---

## 2. The Two Render Directions

The single most important fact in this document, straight from community elders:

> **Layers render bottom-to-top. Models/groups render top-to-bottom.**

Concretely:

- **Within a model's layers:** the *top* layer wins. Layer 1 (top) draws over Layer 2, which draws over Layer 3, etc. Put your mask/accent on top, your base effect below.
- **Across rows in the master view:** rows are rendered top-down, so the *bottom-most* row's effects land last and draw over everything rendered before it (when blending between models is on; when off, lower rows simply override).

**The classic gotcha:** you put a whole-display chase on an "ALL" group and a Marquee on a smaller group, and the chase never shows. That's because the row order is wrong — if you want a group's effect to overlay individual models (or another group), the overlay group must be **lower** in the master view, and the models/groups it should cover must be **above** it. Conversely, to drop a special effect onto one arch *on top of* the arch group's effect, the individual arch row must be below the arches group row.

**Practice:** decide a canonical ordering convention and keep it stable (see §7). Re-ordering rows mid-season silently changes how every sequence composites.

---

## 3. Effect Layers

- Layers are multiple effects stacked on the same model/group row. Think of them as additive by default but fully capable of subtractive work via masks: a red Color Wash base with a Snowflakes layer normally gives red with white flakes, but with mask blending you can invert it — black model, red showing only inside the flakes.
- Each layer has its own effect, palette, blend mode, mix slider, transitions, and buffer settings. Layers are independent instruments; the blend mode is how they talk to each other.
- Pro sequences typically run **2–4 layers on hero props**: a bed (wash/texture), a feature (the musical effect), an accent (sparkle/twinkle), and sometimes a mask or warp layer.
- Layers can also subdivide space: two Morphs confined to different portions of a mega tree interleave like fingers; two Spirals in opposing directions create signature looks.
- Add layers deliberately, not by default. Every layer is render cost and cognitive load. If a layer isn't earning its place musically, delete it.
- **Convention to adopt:** name what each layer is for in a comment/label scheme and keep layer roles consistent across songs (e.g., L1 = mask/accent, L2 = feature, L3 = bed). Consistency makes copy/paste between songs safe — pasting multi-layer effects requires the target to have at least as many layers.

---

## 4. Layer Blending Modes

When setting blend modes, the **current layer is "Effect 1"** and the **layer below is "Effect 2."** The fastest way to learn them: drop two contrasting effects on two layers and step through every mode — experience beats reading here, per the manual itself.

The high-value modes (grouped by job):

| Job | Modes | Use case |
|---|---|---|
| Default compositing | **Normal** | Top layer simply draws over the lower one (with the Mix slider controlling balance) |
| Masking / reveals | **1 is Mask / 1 is UnMask / 2 is Mask / 2 is UnMask** (and reveal variants) | Use one layer's shape to hide or reveal the other. The workhorse for text knockouts, shaped reveals, "effect inside a shape" looks. If Mask looks wrong, try UnMask — community shorthand for the polarity being backwards |
| Math blends | **Average, Max, Bottom-Top, Additive, Subtractive** | Mixing two textures (Average), keeping the brighter of two (Max), or carving brightness away (Subtractive) |
| Per-pixel alternation | **1 reveals 2 / 2 reveals 1**, Shimmer-style alternation | Strobing between two effects |
| Time-based blend | **Morph** (the *blending option*, not the Morph effect) | Effect 1 cross-fades into Effect 2 midway through the timing cell. Great for one-cell transitions without sequencing two segments |
| Canvas | **Canvas mode (layer setting)** | The layer renders on top of what lower layers already produced — required for Warp, and useful for Shaders/effects that should distort or tint the composite below rather than replace it |

**The fade-with-control recipe** (community favorite, more controllable than out-transitions): put your effects on Layer 2; on Layer 1 put a Color Wash from white to black (or On with intensity 100→0); set it Subtractive. Where the wash is white the effect shows at 100%, where black at 0% — a brightness envelope you can shape with value curves, perfect for pulsing to beat tracks.

**Mix slider:** per-layer-pair balance control; automatable with value curves for evolving blends.

---

## 5. Layer Settings: Buffer, Transitions, and Friends

The Layer Settings panel has two tabs — **Buffer** (how the effect renders into the buffer) and **Roto-Zoom** (rotation/zoom applied over the effect). These are the most underused power tools in xLights:

| Setting | What it does | When to use |
|---|---|---|
| **Blur** | Softens the effect, fading color edges into each other; value-curve drivable | Take the "digital" edge off geometric effects; animate blur for focus-pull moments on builds |
| **Sub-Buffer** | Restricts the effect to a region by *redefining the model size for that effect* — the whole effect renders into the smaller area (different from masking, which covers up part of a full render) | Effect on just the top half of the tree; splitting one prop into zones without making submodels; offsetting copies of the same effect |
| **Persistent** | Doesn't clear the buffer between frames — each frame paints over the last | Trails, smears, build-up looks (meteors that leave permanent trails) |
| **In/Out Transitions** | Per-layer wipes, fades, circles, dissolves, blinds, bow-tie, fold, etc., with adjustment and reverse controls | The cheap, clean way to enter/exit effects without sequencing extra cells |
| **Roto-Zoom** | Rotates/zooms the rendered layer, value-curve drivable | Spin a static effect; zoom-punch on a drop |
| **Brightness / contrast per layer** | Per-layer level control | Duck a bed layer under a feature layer without changing palettes |

**Transitions vs Morph blend vs sequencing:** for section boundaries you have three tools — out/in transitions on the layers, the Morph blend mode within one cell, or explicitly sequencing a transition effect (Shockwave/wipe) on a group. Use transitions for routine entries/exits, Morph-blend for one-cell crossfades, and explicit effects for *musical* transitions the audience should notice.

**Phrasing → soft cell edges (orchestrator behavior):** the cell weaver softens or sharpens cell edges by the section's *phrasing*. A **legato** section (the Director's call for calm/introspective moods, or the default below mid energy) gives each woven cell a soft entrance/exit — a linear **fade in/out** scaled to the cell's length for line/chase/point effects, or a **Dissolve** in/out for full-canvas fills/washes — and lengthens short cells so the edge has room to read, so the fabric evolves instead of flashing. A **staccato** section (energetic, or directed) keeps crisp on/off cells. The Director picks only the feel (`phrasing`); code owns the fade/dissolve timing. An explicit per-recipe transition still wins over the phrasing default.

---

## 6. Render Styles: Group vs Per-Model

This is the heart of what you said we're not capturing. When an effect sits on a **model group**, the render/buffer style decides whether the group is treated as **one combined canvas** or as **N independent models**:

| Style | Behavior | Use when |
|---|---|---|
| **Default** (group canvas) | The group's models are placed into one 2D buffer based on their preview locations; the effect renders once across the whole canvas. A sweep crosses the entire display; a Shockwave radiates over all props | Whole-display moves: sweeps, radial bursts, washes, anything that should *travel across* props |
| **Per Preview** | Like Default but the buffer is built from the props' actual preview (screen) coordinates | When spatial accuracy across the yard matters (a wipe that tracks real positions) |
| **Per Model Default** | The effect renders independently on each model in the group, each using its own default buffer | "Same effect, every prop does it itself": Fire on each mini tree, Pinwheel on each spinner. **Required practice for groups of DMX models** (moving heads), which have custom render styles |
| **Per Model Per Preview** | Per-model rendering, each using its preview-based buffer | Per-model with spatial orientation preserved |

Key facts and gotchas:

- **The same effect can look completely different in each style.** Bars on a group Default = one set of bars across the yard; Per Model = every prop running its own bars. Neither is "right" — they're different musical statements. Group-canvas = unified gestures (choruses, drops); per-model = rhythmic multiplicity (verses, percussion).
- **Groups don't know model geometry.** A group buffer is a flat 2D canvas built from preview positions; model-specific render styles (3D cubes' axis styles, custom model internals) are unavailable at group level, and some effects that look great on the individual model can't be reproduced on the group. If you need the model's native rendering, sequence at model level or use Per Model styles.
- **Warp (and some buffer-manipulating effects) do not work in Per Model styles** — they need a group-level canvas. Keep warp/canvas layers on Default/Per Preview.
- **Import note:** modern xLights offers an option when importing effects to convert them to Per Model — relevant when mining vendor sequences whose layout differs from yours.
- **Effect-level scaling:** Galaxy, Shockwave, and Fan now default to "Scale to Buffer," which changes how they size on differently-shaped buffers; check this when an imported radial effect looks tiny or cropped.
- **Document your choices.** Render style is invisible in the grid at a glance and silently changes meaning when models join/leave a group. When a group-canvas effect looks wrong after adding a prop, the buffer shape changed — that's the first thing to check.

**Convention to adopt:** for every group, decide its *default* sequencing style and note it in the layout docs — e.g., `ALL-HOUSE: Default (canvas)`, `MINI-TREES: Per Model Default`, `MOVING-HEADS: Per Model Default (mandatory)`.

---

## 7. Group Ordering & Master View Strategy

Because rows render top-to-bottom and later rows win, **the master view ordering is part of your show's architecture**, not cosmetics.

A widely used layered architecture (top → bottom in the master view):

1. **Whole-display groups** (ALL, ALL-PIXELS) — broad beds and sweeps, rendered first so everything else can override locally
2. **Zone groups** (HOUSE, YARD-LEFT, YARD-RIGHT) — section-level statements over the bed
3. **Prop-type groups** (ARCHES, MINI-TREES, SPINNERS) — the per-archetype workhorses
4. **Individual models** — surgical overrides (the one arch that does something special)
5. **Submodels** — finest-grained accents (tree topper, window frames, spinner rings)
6. **Overlay/FX groups** (STROBES-ALL, an intentional "TOP-LAYER" group) — global accents that must beat everything, living at the very bottom so they always win

Practices:

- **Stability:** freeze the order before sequencing season; changing it re-composites every sequence.
- **Views per song** control what you *see*; the **Master View order** controls what *renders over what*. Keep working views lean, but make ordering decisions in the master view.
- **Naming convention** that encodes the hierarchy (e.g., `G0-ALL`, `G1-HOUSE`, `G2-ARCHES`, model names plain) makes the ordering self-documenting and sorts naturally.
- **One row, one job per moment:** if both a zone group and a prop group are animating the same prop simultaneously, you've created a blend whether you meant to or not. Either intend it (see §8) or keep one of them dark.

---

## 8. Allow Blending Between Models

A sequence-level setting (Sequence Settings) that decides what happens at the *row vs row* compositing stage:

- **Enabled:** when a later (lower) row renders, it starts from what earlier rows already produced and **merges** with it — group beds shine through model-level effects, true cross-row layering.
- **Disabled:** later rows start from black; lower rows **override** higher rows wherever they have effect data.

Implications:

- Enabled is the more expressive mode (bed + feature compositing across rows) but makes every overlap intentional-or-accidental blending — discipline in §7 matters more.
- Disabled is more predictable (last writer wins) and matches how many vendor sequences are authored. If imported sequences look washed out or doubled, check this setting first.
- Changing it requires a **Render All**, and it changes the meaning of every existing overlap in the sequence — pick a house standard and stay with it. `TODO:` record our standard here once chosen.

---

## 9. Recipes: Common Layering Patterns

Patterns worth saving as presets:

1. **Bed + Feature + Sparkle (the standard stack).** L3: Color Wash bed at 30–40% • L2: the musical feature effect • L1: Twinkle at low density, Max blend. The hero-prop default.
2. **Shaped reveal.** L2: any texture effect • L1: Text or Shape effect, "1 is Mask" — the texture shows only inside the letters/shape. Invert with UnMask.
3. **Brightness envelope (beat ducking).** Effects on L2; L1 Color Wash white→black, Subtractive, with a value curve bouncing on the beat — the whole stack pulses musically without touching the effects.
4. **Warp-over-composite.** L2: anything • L1: Warp in Canvas mode (group-level render style, not Per Model) — ripples/drops distort the live composite.
5. **Trail-maker.** Meteors (or moving Single Strand) with **Persistent** on its layer; clear by sequencing an Off/black wash when the trail should reset.
6. **Interleaved fingers.** Two Morph layers, each Sub-Buffered to alternating slices of the tree.
7. **Counter-rotation.** Two Spirals, opposite directions, Average or Max blend — the classic mega-tree showpiece.
8. **Crossfade in one cell.** Two layers, Morph blend mode — effect 1 melts into effect 2 mid-cell. Cheap section transitions.
9. **Global strobe overlay.** A bottom-of-master-view STROBES group with short Strobe/On hits — guaranteed to render over everything for stingers, regardless of what else is playing.

---

## 9b. Per-Effect Layering Roles

A curated, per-effect reference for *how each effect is used in a stack* — its typical role, what
it layers over/under, and the blend it usually wears. This is reference knowledge (what to reach
for), not a placement spec.

Grounded in 648 multi-layer models mined from the community corpus (Listen To Our Lights + xLights
Around the World). Two patterns fell straight out of the data and frame the whole table:

- **Duration tells you the role.** Effects split cleanly into **sustained beds/textures** (median
  2–6 s — they sit low and hold) and **cells/accents** (median 0.4–0.9 s — they ride the beat on
  top). VU Meter (3.8 s), Twinkle (4.2 s), Butterfly (5.1 s), Wave (5.6 s), Circles (5.0 s),
  Color Wash (3.5 s) are beds; On (0.4 s), SingleStrand (0.5 s), Shockwave (0.5 s), Bars (0.5 s),
  Ripple (0.5 s), Morph (0.7 s) are cells/accents.
- **Masking is the community's dominant blend**, not Max/Average. `1/2 is (Un)Mask` and
  `1 reveals 2` show up far more than the math blends — a *shape* layer (On/Shape/Bars/Text/Faces)
  reveals or knocks out the *texture* below it. Our weaver defaults to **Max**; the corpus says the
  richest looks come from **reveal/mask** stacks. Worth leaning into.

### Beds & sustained textures (sit LOW, run long, ≥~2 s)

| Effect | Layers as | Pairs well with (above it) | Typical blend (below the top) | Note |
|---|---|---|---|---|
| **Color Wash** | the base bed | a feature + Twinkle | Normal / `Layered` | the default 30–40% bed; dim it under features |
| **Plasma** | warm organic bed | Fire above; sparkle | `Layered` | liquid color; pair a cool anchor |
| **VU Meter** | music-reactive bed/texture | Twinkle, SingleStrand, Butterfly | `2 is (Un)Mask` (revealed by a shape above) | n=1384; a *reactive* bed, not just a meter |
| **Butterfly** | organic swirl bed | On, Twinkle, SingleStrand, VU Meter | `2 is True Unmask` / `Effect 1` | n=331; the most-layered organic texture |
| **Galaxy / Spirals** | rotating texture bed | a counter-spiral, sparkle | `Average` / `Max` | counter-rotation pair = the mega-tree showpiece (§9.7) |
| **Wave / Circles / Ripple(slow)** | flowing water bed | sparkle, accents | `1 reveals 2` | long, calm; good under a bright accent |
| **Shader** | canvas tint/distort bed | anything | **Canvas mode** | distorts/tints the composite below (§4) |
| **Shape** | a mask SHAPE or slow texture | a texture below it | `2 is True Unmask` | doubles as a reveal mask |

### Carriers & motion cells (beat-length, ~0.4–0.9 s)

| Effect | Layers as | Pairs well with | Typical blend | Note |
|---|---|---|---|---|
| **SingleStrand** | the beat carrier (chase) | Twinkle above; over a wash | `Effect 1` / over-bed Max | n=4484; the workhorse rhythm layer |
| **Bars** | driving carrier / reveal shape | On, SingleStrand | `1 reveals 2` | also a clean mask shape for text-style knockouts |
| **Garlands / Marquee / Fan** | sweeping carrier | over a bed | Normal | directional; read on a group canvas, not per-model |
| **Morph** | short motion cell (NOT a bed here) | another Morph, sparkle | `Layered` | community uses it as a *cell*, often two interleaved (§9.6) |
| **Pinwheel** | radial cell on round props | Twinkle | `Average` | n=596; spinners/stars |
| **Ripple / Fill** | gentle motion / fill cell | over a bed | `1 is True Unmask` | |

### Overlays, accents & mask shapes (sit HIGH, on top)

| Effect | Layers as | Pairs well with (below) | Typical blend | Note |
|---|---|---|---|---|
| **Twinkle** | the universal sparkle overlay | On, SingleStrand, VU Meter, Butterfly, Pinwheel | `Effect 1` / `Max` | n=661, med 4.2 s — a sustained top coat over almost anything |
| **Shimmer** | strobing top coat | a steady bed | per-pixel alternation | |
| **On** | base fill **and** mask shape **and** flash accent | everything | `1 is True Unmask` (as a mask) / Normal | n=15288 — the most-used layer; wears every hat |
| **Shockwave / Strobe / Lightning** | punch-through accent (short) | a bed/carrier | `1 is Unmask` / on top | n(Shockwave)=1760; ≤1-bar punctuation |
| **Text / Faces** | a reveal mask / character layer | a texture to show through it | `1 is Mask` / `Effect 1` | the texture shows only inside the glyphs/face |

### What pairs with what (top community co-occurrences)

The pairs that show up most often on the same multi-layer model — a quick "if you have X, Y goes
well on top":

`On+Twinkle` · `On+SingleStrand` · `On+VU Meter` · `Butterfly+On` · `SingleStrand+Twinkle` ·
`Bars+On` · `On+Pinwheel` · `Twinkle+VU Meter` · `Butterfly+Twinkle` · `SingleStrand+VU Meter` ·
`On+Spirals` · `Shockwave+Twinkle`. The throughline: **Twinkle and On go over everything**, and the
**beds (VU Meter / Butterfly) carry a chase (SingleStrand) or sparkle (Twinkle) on top.**

> **Reach for masking.** The single biggest gap between our stacks and the community's is the
> reveal/mask family (§4). A texture bed + a shape (On/Bars/Shape/Text) set `1 is Mask`/`UnMask`
> on top is the corpus's most distinctive move and costs almost nothing to render.

---

## 10. Performance & Render Hygiene

- **Group buffers can get huge.** Whole-display group canvases at preview resolution are expensive; xLights enforces a max group buffer size in places, but be deliberate about how many giant-canvas effects run simultaneously.
- **Render cache & GPU:** enable the render cache for iteration speed; note GPU-rendered effects have had cache-interaction bugs historically — if an effect renders black after caching, clear the cache before debugging your sequencing.
- **Canvas Mode (sequence-level)** changes render semantics: the fseq isn't cleared before render, so deleted effects keep playing until overwritten. Know whether it's on.
- **Render All after structural changes:** sequence timing, blending-between-models, duration changes all need a full re-render to take effect.
- **F5 / targeted render** for spot checks; full Render All before exporting or judging the look.
- **Layer count audit:** layers nobody can see (fully occluded, zero-mix) still cost render time. Prune.

---

## 11. What Else We Might Be Missing

Things adjacent to this topic that we likely aren't capturing yet, ranked by impact:

1. **Value curves everywhere.** Speed, brightness, blur, mix, roto-zoom — nearly every numeric is curve-drivable. Curves are what make builds feel musical instead of mechanical. Deserves its own section or document, with a library of named curves (ease-in build, beat-bounce, swell-release).
2. **Submodel strategy.** Defining submodels (tree rings/slices, spinner arms, window frames) is what unlocks surgical layering — and HD-prop vendors ship effects targeted at *their* submodel definitions, so adopting vendor-compatible submodel naming pays off at import time. We have no documented submodel scheme yet.
3. **Buffer styles at the model level.** Beyond group render styles, individual models have buffer styles (horizontal/vertical per strand, stacked/overlaid arrangements, single line) that change how effects map onto the geometry. Worth a per-prop cheat sheet of which buffer style each effect assumes.
4. **Transitions catalog.** The in/out transition types (wipes, blinds, dissolve, fold, bow-tie...) with notes on which read well at yard distance. Currently tribal knowledge.
5. **The Off effect as an instrument.** Explicit Off effects to punch holes, reset persistent layers, and guarantee darkness regardless of lower rows — different from "no effect," which lets lower rows show through when blending is on. Subtle and worth documenting.
6. **State/dimming curves & gamma per controller.** Why the preview and the yard disagree on brightness/color — output-side correction belongs in our standards too.
7. **Render-order regression checks.** A quick "test pattern" sequence that exercises group-over-model and model-over-group overlaps, to verify nothing composites differently after layout changes or xLights upgrades. (Very cheap insurance; very platform-engineer-brained, but it works here.)
8. **Shaders.** The Shader effect opens GLSL-based looks far beyond stock effects; interacts with canvas mode and group buffers. A future doc once the basics above are standardized.
9. **DMX/moving-head integration rules.** Per Model Default is mandatory for DMX groups; position/gobo channels need their own sequencing conventions separate from pixel thinking.
10. **Sequence-level vs layer-level canvas mode disambiguation.** Two different features share the "canvas" name (a layer render-on-top setting vs the sequence fseq-persistence setting); our docs should always specify which.

---

## 12. Sources

- xLights Manual — Layers, Layer Blending, Layer Settings, Windows/Layer panel, DMX Model (manual.xlights.org)
- AusChristmasLighting — "Layering effects" thread (the render-direction rules and master-view ordering tricks), "Effect/layers help" (subtractive fade recipe, Mask/UnMask), "Cube models in groups" (group vs model geometry limits)
- xLights GitHub issues — Warp vs Per Model render styles (#3286), DMX group render style (#4895)
- xLights release notes — render cache/GPU fixes, max group buffer, Scale-to-Buffer defaults, import-as-Per-Model option
- Video: "In-depth walkthrough of xLights Buffers and Layer Blending" (videos.xlights.org); "xLights – Basic Layer Blending" tutorial

---

## 13. Changelog

| Version | Date | Changes |
|---|---|---|
| 0.2 | 2026-06-16 | §9b Per-Effect Layering Roles — curated per-effect reference (role / pairs / typical blend) grounded in 648 multi-layer community models; surfaces duration→role and the under-used masking family |
| 0.1 | 2026-06-09 | Initial draft: render directions, layers, blend modes, layer settings, render styles, ordering architecture, blending-between-models, recipes, gaps list |

<!--
Editing conventions:
- Version-specific behavior gets a release note citation or an (verify on current release) tag.
- New recipes go in §9 with the preset name used in our library.
- Items resolved from §11 graduate into their own section or document; strike them from the list with a link.
-->
