---
name: xlo-effects
description: How to use each xLights effect well — one file per effect under effects/, mined from the community corpus and hand-tuned. Each file gives the effect's identity and stack role, thematic fit, the dials and what moving each one does, anchor settings to permute from (never the only options), layering recipes with blend semantics, value-curve shapes with exact strings, prop fit and render style, timing habits, cited exemplar moments from the best community sequences, anti-patterns, and what code can realize today. Load during /xlo:design and /xlo:review for every effect type a section names, and whenever you decide how a chosen effect should actually look, move, stack or breathe.
---

# xlo-effects

The craft of individual effects, one file each, in `effects/<Type>.md`. This index is deliberately
short: read the file for the effect you are about to use, not this page.

## How to use these files

1. Pick the section's effect types with `xlo-sequencing` (which family fits the moment).
2. Open `effects/<Type>.md` for each chosen type **before** deciding how it looks. Read the whole
   file the first time it comes up in a show; afterwards go straight to the section you need.
3. Design from an **anchor**, then permute. Anchors are starting points mined from the pros, not a
   menu. The expected move is: take an anchor, change one or two dials for this section, give the
   twin layer its own difference, choose the value-curve shape for the phrase, pick the bed.
4. Think in **stacks**, not single effects. Every file says what the effect sits over, what sits
   over it, and which blend makes that work. A lone effect on a group canvas is the samey look.
5. Cite the exemplar you are leaning on in the section's `rationale` ("twin thin spirals over a
   Butterfly bed, Kid On Christmas 0:00–0:13") so a reviewer can look at the source.

## Stack roles (the vocabulary every file uses)

| Role | What it is | Typical layer |
|---|---|---|
| **bed** | the long, soft layer everything else sits on (Ripple, Morph, Butterfly, Color Wash, a slow thick Spirals) | bottom |
| **carrier** | the rhythmic layer cut on the beat grid (1–2 beat cells, chases, ticks) | middle |
| **feature** | the identity of the section on the hero (a twin Spirals, a Pinwheel) | middle/top |
| **overlay** | a layer that only makes sense with something beneath it (Warp, Shader, Kaleidoscope, VU Meter on top) | top |
| **mask** | a shape whose blend reveals or hides the layer below (Shape + "1 is Mask", SingleStrand + "2 is Unmask") | top |
| **accent** | a short hit (Shockwave, Meteors, a white flash) | top, punch-through |

xLights composites **bottom → top**. In the `.xsq` the first `EffectLayer` is the TOP layer, and
the automation API's layer index 0 is that top layer (verified live 2026-11-02). Inside the
pipeline every layer number is LOGICAL (0 = bottom) and the emitter flips to xLights indices at
placement, so write stacks bottom → top and never think in indices. With
the `Normal` blend, black pixels in an upper layer are transparent, so the bed shows through the
gaps of a striped effect. `Brightness` uses the upper layer as a brightness envelope on the bed.
`Layered`, `2 reveals 1`, `1 is Mask`/`Unmask` are the reveal tools. See each file's recipes.

## Files

| Effect | Status |
|---|---|
| [Spirals](effects/Spirals.md) | mined 2026-11-02 (20 of 22 sequences, 2,068 placements); craft written — the twin on the tree |
| [SingleStrand](effects/SingleStrand.md) | mined (20 seq, 13,636); craft written — the outline/arch/cane comet |
| [Shockwave](effects/Shockwave.md) | mined (20 seq, 11,114); craft written — the beat pop and the yard ring |
| [Pinwheel](effects/Pinwheel.md) | mined (21 seq, 2,586); craft written — the counter-rotating pair |
| [Bars](effects/Bars.md) | mined (16 seq, 1,115); craft written — beat bar, clap, sweep, texture mask |
| [Morph](effects/Morph.md) | mined (10 seq, 1,693); craft written — the wipe |
| [Color Wash](effects/Color%20Wash.md) | mined (12 seq, 1,260); craft written — flood pulse and matrix pool |
| [Ripple](effects/Ripple.md) | mined (12 seq, 951); craft written — the beat ring and the ring mask |
| [Warp](effects/Warp.md) | mined (7 seq, 212); craft written — the mirror overlay |
| [On](effects/On.md) | mined 2026-11-03 (22 seq, 5,580); craft written — the flat fill: one-beat color pops, the flood flash, the house bed, and the `2 is Unmask` stamp through a shape beneath |
| [VU Meter](effects/VU%20Meter.md) | mined (12 seq, 1,674); craft written — 95% `Timing Event …` types firing on a timing track: the beat cutter and the `2 is True Unmask` stamp, not an audio meter |
| [Shader](effects/Shader.md) | mined (11 seq, 880); craft written — a `.fs` texture kept under an On/VU/Bars stamp; asset-bound, not placeable from the catalog yet |
| [Curtain](effects/Curtain.md) | mined (10 seq, 742); craft written — the one-beat open-then-close twitch, the black close/open over a stack, the slow house close |
| [Shape](effects/Shape.md) | mined (12 seq, 621); craft written — a one-beat star popping somewhere new every beat over a Spirals twin; ornament scatters on the house |
| [Wave](effects/Wave.md) | mined (15 seq, 408); craft written — the travelling sine line, twinned L→R against R→L, and the `True Unmask` wave window |
| [Twinkle](effects/Twinkle.md) | mined (17 seq, 381); craft written — a two-beat white pop every couple of bars, or the quiet bed at Count 2–6; never per-beat |
| [Butterfly](effects/Butterfly.md) | mined (14 seq, 292); craft written — the organic bed held a phrase on lines and trees, with hits layered beneath it |
| [Fan](effects/Fan.md) | mined (9 seq, 275); craft written — the per-flake propeller, three stacked wheels on the tree, the corner sunburst at a section head |
| [Meteors](effects/Meteors.md) | mined (15 seq, 115); craft written — rain, rising music sparks, and the corner-explosion twin; black in the palette is the density dial |
| [Kaleidoscope](effects/Kaleidoscope.md) | mined (5 seq, 35 — thin); craft written — the overlay (Canvas on) that tiles the layers beneath into a mandala on the matrix |
| [Fire](effects/Fire.md) | mined (4 seq, 8 — thin); craft written — the flame bed; mostly labelled xLights behaviour plus the Halloween brief |
| [Off](effects/Off.md) | mined (11 seq, 429); craft written — the blank layer: a placeholder beneath a `2 is Unmask` On, a 1–2 beat kill on one prop, a `Max` gate; never the way to say silence |
| [Fill](effects/Fill.md) | mined (4 seq, 295 — thin); craft written — the line-prop fill from one end on a `Fill_Position` curve, 100% curved, 2–4 beat cells |
| [Garlands](effects/Garlands.md) | mined (10 seq, 129); craft written — four crossing swags netting the tree under chases, or a 1-beat per-model house hit |
| [Marquee](effects/Marquee.md) | mined (7 seq, 129 — thin); craft written — the sign chase: a 1-pixel band round the roofline, Reverse flipped every 8 beats; a matrix frame around the hero |
| [Pictures](effects/Pictures.md) | mined (6 seq, 137); craft written — a photo or GIF on the matrix telling the lyric, scrolled, mirrored or held; asset-bound, not placeable yet |
| [Snowflakes](effects/Snowflakes.md) | mined (11 seq, 73); craft written — falling flakes held a phrase on tree, matrix and house, twinned by Type, never curved |
| [Galaxy](effects/Galaxy.md) | mined (9 seq, 64); craft written — one spiral arm that blooms or collapses over Duration; a 3–12 beat house or star feature, twinned by palette or Reverse+Flip |
| [Lightning](effects/Lightning.md) | mined (2 seq, 33 — thin); craft written — three bolts at once re-cut every half second through a stinger; never a bed |
| [Circles](effects/Circles.md) | mined (6 seq, 27 — thin); craft written — drifting discs for 2 beats at section heads, a new colour pair each time |
| [Plasma](effects/Plasma.md) | mined (4 seq, 23 — thin); craft written — the texture bed with black in the palette, 8–40 beats under Spirals, Warp or video; the `2 reveals 1` layer over a Fan pair |
| [Shimmer](effects/Shimmer.md) | mined (2 seq, 16 — thin); craft written — the whole prop blinking in palette bands, a phrase apart, never on the beat |
| [Fireworks](effects/Fireworks.md) | mined (2 seq, 9 — thin); craft written — a 1-beat Beats-triggered burst with a Shockwave over it, or a 3-beat Gravity finale over Bars |
| [Liquid](effects/Liquid.md) | mined (2 seq, 8 — thin); craft written — the particle fluid sim: cyan rain on the matrix under a film; render-heavy |
| [Strobe](effects/Strobe.md) | mined (1 seq, 3 — effectively absent); craft is xLights behaviour plus our house rule: peak payoff only, once, ≤ 1 bar |
| Faces, Video, Text, Moving Head, DMX, Tree, Sketch, Snowstorm, Tendril | not written — asset-bound or hardware types placed by code (`pipeline/faces.py`, `pipeline/matrix_video.py`, `matrix_text`), or one-off corpus curiosities; fall back to `xlights-effects-catalog.md` §3–§10 — run `xlo mine-effect "<Type>" --write`, then fill the craft skeleton; until then fall back to `xlights-effects-catalog.md` §3–§10 |

The corpus itself, with the duplicate check, is in [corpus.md](corpus.md).

Readings the corpus overturned, worth knowing before you trust the old catalog: Ripple is a
one-beat ring and a mask, not an ambient bed; Color Wash is mostly a flood-light pulse; Warp and
Kaleidoscope are overlays that need `Canvas` on and something beneath them; VU Meter is a
timing-track event stamp, not an audio meter; Twinkle is a phrase-pickup pop, not a per-beat
sparkle; Shape is a per-beat star pop over a twin, not a mask. And one idiom runs through every
file: the **twin**, two layers of the same effect differing by direction, transform or color.

`effects/_TEMPLATE.md` is the shape every file follows. The **Corpus facts** block is generated:

```bash
uv run xlo mine-effect "<Type>" --write
```

reads the corpus named by `xlights_core/knowledge/corpus_manifest.json` (see [corpus.md](corpus.md)),
mines every placement of that type with its stack context, and splices the block into
`effects/<Type>.md`, creating the file with an empty craft skeleton when it does not exist. The
**Craft** block is hand-written and survives re-mining. Edit craft, never facts. Without `--write`
the block prints to stdout; `--json <path>` dumps the raw placements and pairs for ad-hoc analysis.

## How a file's knowledge reaches the show

A section's `stack` (the `xlo-brief` skill documents every field) carries what these files
teach: each layer names the effect, a catalog look (`vocab.json` `looks`), its knobs, raw
settings such as the value-curve strings printed here, blend, transform, direction, palette,
`cell_beats` for the beat grid, and a `twin` (mirror / counter / flip / color). Code places the
stack as written and withholds its synthesized weave, composites, phrase gesture, VU and final
layer for that section; beat accents still run unless a layer's role is `accent`.

Where a section has no stack, code still synthesizes as before, but its looks now come from a
picker that rotates among the most-used neutral catalog looks per section instead of taking the
first look in file order, and the catalog itself is mined from the corpus manifest, so the looks
these files cite are placeable by id. A look that bakes in a blend or a mask (the "designed"
looks such as `Spirals#99`) is never a default pick; name it in a stack layer on purpose.
