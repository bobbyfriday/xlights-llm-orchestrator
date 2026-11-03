# Marquee

The sign chase: a one-pixel RGB band running round the roofline on a Single Line buffer with Reverse flipped every 8 beats, or a Thickness 3–10 frame on the matrix around the hero's twin; seven sequences, four songs.

---

## Corpus facts

> Generated 2026-11-03 from the deduped corpus: **22 community sequences, 14 distinct songs** (xLights 2020.45–2025.08; 0 byte-identical files dropped). 7 sequences / 4 songs use Marquee: **129 placements, 198 overlapping pairs.** Every share carries its breadth (sequences / songs); a habit in one sequence is one sequencer's habit, however many placements it has.
>
> Sources by placements: Light Of Christmas (Bill Jenkins) 54 · Light Of Christmas (main) 34 · Christmas Just Ain't Christmas 20 · Danger Zone (XATW) 14 · Kid On Christmas (Eliot Wisser) 4 · Kid On Christmas (Greg Colburn) 2 · Kid On Christmas (Jeremy Poling) 1.

### Where it is placed

| Prop class | Share | Breadth | Example model names |
|---|---|---|---|
| matrix | 42% | 2 seq / 1 song | Matrix1, Matrix2, P10 |
| megatree | 16% | 3 seq / 3 songs | MegaTree, MegaTree Singing Faces, MegaTree1 |
| tree | 14% | 3 seq / 3 songs | Mini Trees, Spiral Trees, Mini Trees Evens |
| roofline | 12% | 2 seq / 2 songs | Outlines |
| arch | 11% | 3 seq / 3 songs | Archs, Arch Fans, Arches |
| window | 3% | 1 seq / 1 song | Windows |
| group_all | 1% | 1 seq / 1 song | *Entire Display no Floods |
| house | 1% | 1 seq / 1 song | House_Verticals |

### Dials observed

Share · breadth per value; `curved` = that key has an active value curve instead of a static value.

| Key | Values |
|---|---|
| `PixelOffsets` (checkbox) | 0: 100% · 7 seq / 4 songs |
| `Reverse` (checkbox) | 0: 57% · 7 seq / 4 songs — 1: 43% · 4 seq / 3 songs — range 0…1 |
| `WrapX` (checkbox) | 0: 100% · 7 seq / 4 songs |
| `WrapY` (checkbox) | 0: 91% · 7 seq / 4 songs — <absent>: 9% · 1 seq / 1 song |
| `E_NOTEBOOK_Marquee` | Settings: 100% · 7 seq / 4 songs |
| `MarqueeXC` (slider) | 0: 100% · 7 seq / 4 songs |
| `MarqueeYC` (slider) | 0: 100% · 7 seq / 4 songs |
| `Band_Size` (slider) | 3: 93% · 5 seq / 4 songs — 5: 2% · 1 seq / 1 song — 7: 2% · 1 seq / 1 song — 4: 1% · 1 seq / 1 song — 9: 1% · 1 seq / 1 song — 1: 1% · 1 seq / 1 song — 8: 1% · 1 seq / 1 song — range 1…9 |
| `ScaleX` (slider) | 100: 100% · 7 seq / 4 songs |
| `ScaleY` (slider) | 100: 100% · 7 seq / 4 songs |
| `Skip_Size` (slider) | **curved 25% · 1 seq / 1 song** — 0: 60% · 4 seq / 4 songs — 3: 9% · 1 seq / 1 song — 16: 2% · 1 seq / 1 song — 9: 2% · 1 seq / 1 song — 8: 1% · 1 seq / 1 song — 23: 1% · 1 seq / 1 song — 6: 1% · 1 seq / 1 song — range 0…23 |
| `Speed` (slider) | 3: 53% · 7 seq / 4 songs — 1: 45% · 2 seq / 2 songs — 2: 2% · 1 seq / 1 song — range 1…3 |
| `Stagger` (slider) | 0: 89% · 6 seq / 4 songs — 50: 6% · 1 seq / 1 song — 29: 2% · 1 seq / 1 song — 13: 2% · 1 seq / 1 song — 12: 1% · 1 seq / 1 song — range 0…50 |
| `Start` (slider) | 0: 94% · 7 seq / 4 songs — 100: 6% · 1 seq / 1 song — range 0…100 |
| `Thickness` (slider) | 1: 60% · 3 seq / 3 songs — 3: 15% · 2 seq / 2 songs — 10: 11% · 1 seq / 1 song — 100: 6% · 1 seq / 1 song — 9: 2% · 1 seq / 1 song — 25: 2% · 1 seq / 1 song — 15: 1% · 1 seq / 1 song — 6: 1% · 1 seq / 1 song — range 1…100 |
| `B_CHOICE_BufferStyle` | <absent>: 36% · 3 seq / 2 songs — Default: 19% · 1 seq / 1 song — Per Model Single Line: 18% · 3 seq / 3 songs — Single Line: 15% · 3 seq / 3 songs — Per Preview: 6% · 1 seq / 1 song — Per Model Default: 3% · 3 seq / 3 songs — Per Model Default Deep: 2% · 1 seq / 1 song |
| `T_CHOICE_LayerMethod` | <absent>: 84% · 6 seq / 4 songs — Layered: 16% · 2 seq / 2 songs |
| `T_TEXTCTRL_Fadein` | <absent>: 48% · 4 seq / 3 songs — 0.25: 25% · 1 seq / 1 song — .5: 12% · 3 seq / 2 songs — 1: 6% · 2 seq / 2 songs — .2: 6% · 1 seq / 1 song — 0.50: 2% · 1 seq / 1 song — 3: 1% · 1 seq / 1 song — range 0.2…3 |
| `T_TEXTCTRL_Fadeout` | <absent>: 52% · 5 seq / 4 songs — 0.25: 25% · 1 seq / 1 song — .5: 10% · 1 seq / 1 song — .2: 6% · 1 seq / 1 song — 1: 2% · 1 seq / 1 song — 0.75: 2% · 1 seq / 1 song — 1.00: 2% · 1 seq / 1 song — .75: 1% · 1 seq / 1 song — range 0.1…1 |
| `B_SLIDER_Blur` | <absent>: 87% · 6 seq / 4 songs — 4: 12% · 2 seq / 2 songs — 9: 2% · 1 seq / 1 song — range 4…9 |

### Value curves

| Parameter | Share · breadth | Shapes |
|---|---|---|
| any curve | 33% · 2 seq / 2 songs | |
| `B_VALUECURVE_Rotation` | 25% · 1 seq / 1 song | Ramp 32 |
| `E_VALUECURVE_Marquee_Skip_Size` | 25% · 1 seq / 1 song | Timing Track Fade Proportional 32 |
| `T_VALUECURVE_In_Transition_Adjust` | 7% · 1 seq / 1 song | Ramp 9 |
| `T_VALUECURVE_Out_Transition_Adjust` | 9% · 1 seq / 1 song | Custom 11 |
| timing-track curves (`TT=`) | 25% · 1 seq / 1 song | Beat Count |

Most-used exact strings (copy verbatim; `Min`/`Max` are the parameter range, `P*` the real values):

```
B_VALUECURVE_Rotation (16, 1 seq / 1 song): Active=TRUE|Id=ID_VALUECURVE_Rotation|Type=Ramp|Min=0.00|Max=100.00|P2=100.00|RV=TRUE|
B_VALUECURVE_Rotation (16, 1 seq / 1 song): Active=TRUE|Id=ID_VALUECURVE_Rotation|Type=Ramp|Min=0.00|Max=100.00|P1=100.00|RV=TRUE|
E_VALUECURVE_Marquee_Skip_Size (32, 1 seq / 1 song): Active=TRUE|Id=ID_VALUECURVE_Marquee_Skip_Size|Type=Timing Track Fade Proportional|Min=0.00|Max=100.00|TT=Beat Count|P2=100.00|P3=50.00|TO=75|RV=TRUE|
T_VALUECURVE_In_Transition_Adjust (9, 1 seq / 1 song): Active=TRUE|Id=ID_VALUECURVE_In_Transition_Adjust|Type=Ramp|Min=0.00|Max=100.00|P1=33.00|P2=67.00|RV=TRUE|
T_VALUECURVE_Out_Transition_Adjust (11, 1 seq / 1 song): Active=TRUE|Id=ID_VALUECURVE_Out_Transition_Adjust|Type=Custom|Min=0.00|Max=100.00|RV=TRUE|Values=0.00:0.30;0.14:0.50;0.22:0.63;0.31:0.78;0.42:0.85;0.51:0.78;0.57:0.69;0.64:0.56;0.73:0.40;0.80:0.28;0.89:0.20;0.93:0.20;1.00:0.29|
```

### Palette habits

Colors per placement: 1: 2% · 2: 31% · 3: 48% · 4: 17% · 5: 2%.
Black as a color: 28% · 4 seq / 4 songs. Sparkles on: 3% · 1 seq / 1 song.
Top palettes: #FF0000+#00FF00+#0000FF 48 · #008040+#0000FF 12 · #008040+#00FF00+#000000+#000000 7 · #004080+#0000FF+#000000+#000000 7 · #008040+#FFFF00 6 · #FFFFFF+#0000FF 6 · #D50000+#000000 5 · #00FF00+#000000 5.

### Duration

Median 3.88 s. 2–4 s 65% · 4–8 s 18% · 8–16 s 9% · ≥16 s 8%.
In beats (129 placements with a beat track): 8 beats 43% · 7 beats 11% · 15 beats 5% · 9 beats 4% · 5 beats 3% · 13 beats 3% · 24 beats 2% · 14 beats 2%.

### Stacking

**67% of placements share the model with at least one concurrent effect (7 seq / 4 songs); 25% with three or more (1 seq / 1 song).**

Partner types (pairs · sequences): Spirals 75 · 3 · Marquee 48 · 1 · Faces 39 · 2 · Pinwheel 18 · 1 · VU Meter 14 · 2 · Color Wash 1 · 1 · Butterfly 1 · 1 · On 1 · 1 · Off 1 · 1.

Above Marquee (partner type, the partner's blend): Spirals 64 Normal · Marquee 24 Normal · Pinwheel 18 Normal · VU Meter 14 Normal · Spirals 8 1 reveals 2 · Spirals 3 Subtractive · Faces 1 Normal.

Beneath Marquee (partner type, Marquee's own blend over it): Faces 38 Normal · Marquee 24 Normal · Color Wash 1 Normal · Butterfly 1 Normal · On 1 Normal · Off 1 Normal.

Recurring full stacks (top → bottom, `*` = the mined effect): *Marquee (43) · *Marquee > Faces (18) · VU Meter > *Marquee (13) · *Marquee > Faces > Faces (10) · Spirals > Spirals > Pinwheel > *Marquee > Marquee (9) · Spirals > Spirals > Pinwheel > Marquee > *Marquee (9) · Spirals > *Marquee (8) · Spirals > Spirals > *Marquee > Marquee (3) · Spirals > Spirals > Marquee > *Marquee (3) · Spirals > Spirals > *Marquee > Marquee > Marquee > Marquee (2) · Spirals > Spirals > Marquee > *Marquee > Marquee > Marquee (2) · Spirals > Spirals > Marquee > Marquee > *Marquee > Marquee (2) · Spirals > Spirals > Marquee > Marquee > Marquee > *Marquee (2) · *Marquee > Color Wash > Butterfly (1) · *Marquee > On (1) · Spirals > Spirals > *Marquee (1).

Same-type twins (24 top-over-bottom pairs): identical effect settings 100%; buffer transform differs 0%.

---

## Craft

### Identity and role

Marquee runs colored bands around the border of the buffer like a theatre sign. **Band Size**
is the pixels per color band (3 in 93%, 5 seq / 4 songs), **Skip Size** the black pixels
between bands (0 in 60%, 4 seq / 4 songs; 3 for a dotted chase; curved on a timing track in
25%, 1 seq), **Thickness** how deep the border is (1 in 60%, 3 seq / 3 songs; 3 in 15%, 2 / 2;
10 in 11% and 100 — the whole buffer — in 6%, 1 seq each), **Speed** 1–3 (3 in 53%, 7 seq / 4
songs; 1 in 45%, 2 / 2), **Reverse** the way round (on in 43%, 4 seq / 3 songs), **Stagger**
offsets successive rings (0 in 89%; 50 with Thickness 100), **Start** where the chase begins
(0 in 94%). ScaleX / ScaleY 100, X / Y center 0, WrapX / WrapY off and PixelOffsets off in
every placement: the pros never shrink, move or wrap the box.

On a **Single Line** buffer the border *is* the string, so a Marquee there is a chase running
round the roofline or the tree's outline: Band 3, Skip 0, Thickness 1, Speed 1, RGB. On a
**matrix** with Default buffer it is a frame: Thickness 3 or 10, Speed 3, eight beats, under
the hero's spirals. With Thickness 100 and Stagger 50 it stops being a border and becomes
staggered bands sweeping the whole buffer. Breadth is thin — 7 seq / 4 songs, 129 placements,
88 of them in two Light of Christmas files, 54 on one matrix — so the roofline chase (3 seq /
3 songs at Thickness 1) is the only habit with breadth.

Roles: **carrier** (the outline chase, 8-beat cells with Reverse flipping), **frame** — a
feature's border on the matrix (`Spirals > Spirals > Pinwheel > Marquee > Marquee`, 9 × 2
placements) or around a singing face (`*Marquee > Faces` 18 + 10), **overlay-bed** (Thickness
100 `Layered` beneath a Spirals `1 reveals 2`, 8). 67% of placements have a partner (7 seq / 4
songs); the partner is almost always above it at Normal (Spirals 64, Pinwheel 18, VU Meter
14). Never an accent, never a 1-beat cell (the shortest bucket is 2–4 s, 65%).

### Thematic fit

Marquee says *sign*, *frame*, *around*: the lit border of a marquee, lights chasing round a
window, a ring running the roofline. It is the house-outline effect of the Christmas files
(red-green-blue 48 placements, the top palette) and the chorus frame on the matrix in
#008040 + yellow / blue. For Halloween: an orange + black dotted chase (Band 3, Skip 3) round
the house outline reads as a carnival sign; a purple frame at Thickness 10 around the hero's
feature; Thickness 100 orange bands with Stagger 50 beneath a Spirals `1 reveals 2` for a
striped reveal. Three colors in 48% of placements, two in 31%; black as a color in 28% (4 seq
/ 4 songs) — the second black in `#008040 + #00FF00 + #000000 + #000000` is how the LoC
matrix frame gets its gaps without touching Skip Size.

### Anchors (starting points, not a menu)

| Anchor | Settings | Catalog look | Where | Dials to move |
|---|---|---|---|---|
| **Outline chase** | Band 3, Skip 0, Thickness 1, Speed 1, Stagger 0, `Single Line`, RGB, 8 beats, Reverse flipped every cell | `Marquee#14` / `#12` (Band 3, Skip 0, Stagger 0, Thickness 1 frozen; knobs Reverse, Speed 1–3) + `render_style: "Single Line"`; `Marquee#11` (Single Line + Reverse frozen; Speed knob); `Marquee#8` (buffer knob {Default|Per Model Single Line|Single Line}, Speed, fade-in {1|3}) | Light of Christmas outlines, the whole intro (3 seq / 3 songs for Thickness 1) | Speed 1 → 3 at the chorus; `Per Model Single Line` with fade .5 / .5 on a prop group (10, 1 seq) |
| **Matrix frame** | Band 3, Thickness 3, Speed 3, Stagger 0, Skip Size on a Beat Count timing curve, buffer Rotation Ramp, fade 0.25 / 0.25, two colors, 8 beats, doubled on two layers | `Marquee#2` (69; knobs buffer {Default|Per Model Default Deep|Per Model Single Line|Single Line}, Reverse, Band 3–5, Skip 0–23, Speed 1–3, Stagger 0–29, Thickness 1–9) + the two curves in `settings` | Light of Christmas Matrix1, CHORUS OWL ×4 (1 seq / 1 song) | Thickness 3 → 10 (`Marquee#1`, Thickness 1–25) with black as the third and fourth color; the pair's palette |
| **Dotted ring** | Reverse, Band 3, Skip 3, Thickness 1, Speed 3, `Single Line`, `Layered`, 13–15 beats, three or four pastels | `Marquee#3` (all frozen; knob buffer {Per Model Single Line|Single Line}) · `#4` (+ fade-in .2) · `#7` (+ fade-out 1 and the Custom out-transition curve) | Christmas Just Ain't Christmas mega tree intro (1 seq / 1 song) | Skip 3 → 6 (`Marquee#6`); fade-out 1 at the phrase end |
| **Band sweep** | Reverse, Band 3, Skip 0, Speed 3, Stagger 50, Start 100, Thickness 100, `Per Preview`, `Layered`, fade 1 / .2 on the first, .2 / .2 on the repeat, 6–7 beats, under a Spirals `1 reveals 2` | `Marquee#5` (8; everything frozen incl. the blend and both transition curves; knob fade-in {.2|1}) | Christmas Just Ain't Christmas mega tree, six times (1 seq / 1 song) | the Spirals above decides what shows; the four colors |
| **Deep border** | Band 5, Skip 16, Speed 3, Stagger 29, Thickness 9, `Per Model Default Deep` | `Marquee#2` with its knobs at the top of their ranges; `Marquee#9` (Band 4, Skip 8, Stagger 12, Thickness 15, fades .5 / .75 all frozen) | 3 + 1 placements, 1 seq / 1 song each — one sequencer's experiment | Stagger is the dial that makes rings chase each other |
| **Soft bands** | `Single Line`, Blur 4, Speed 3, Band 1–9, Thickness 21–23, `Layered`, fade .5 / 1.00 | `Marquee#0` (2, 1 seq) | a blurred wide chase | Blur 4 → 9 (`Marquee#1` Blur 4–9, 2 seq / 2 songs for Blur 4) |

**Dials** — pick from the observed values, then move one:

| Dial | Sane range | Moving it | Corpus picks |
|---|---|---|---|
| Band Size | 1–9 | pixels per color band; 3 is the sign look | 3 93% · 5 · 7 · 4 · 9 · 1 · 8 (1 seq each) |
| Skip Size | 0–23 | black between bands: 0 a solid chase, 3 dots, 16+ sparse; curved on beats it pumps | 0 60% (4 seq / 4 songs) · 3 9% · curved 25% (1 seq) · 16 · 9 · 8 · 23 · 6 |
| Thickness | 1–100 | 1 on a line; 3 a frame; 10 a thick frame; 100 bands across the whole buffer | 1 60% (3 / 3) · 3 15% (2 / 2) · 10 11% · 100 6% · 9 · 25 · 15 · 6 |
| Speed | 1–3 | 1 the intro crawl, 3 the chorus; `effect_meta` allows 1–8, the corpus never passes 3 | 3 53% (7 / 4) · 1 45% (2 / 2) · 2 |
| Reverse | off / on | the way round; flipped every 8 beats on the outline | off 57% · on 43% (4 / 3) |
| Stagger | 0–50 | offsets each ring from the last; 50 with Thickness 100 makes the bands sweep | 0 89% · 50 (1 seq) · 29 · 13 · 12 |
| Start | 0 / 100 | where the chase begins; 100 with the band sweep | 0 94% · 100 6% (1 seq) |
| Scale / Center / Wrap / PixelOffsets | 100 / 0 / off / off | never moved in the corpus | 100% |
| Buffer | Single Line / Per Model Single Line / Default / Per Preview / Per Model Default Deep | the string · each prop's string · the matrix frame · the yard as one box · deep rings per prop | PMSL 18% (3 / 3) · Single Line 15% (3 / 3) · Default 19% (1 seq) · Per Preview 6% · PMD Deep 2% |
| Blend | Normal / Layered | Layered under a reveal or for the dotted ring (2 seq / 2 songs) | absent 84% · Layered 16% |
| Fades | 0.25 / 0.25 on the frame; .5 / .5 on the per-model chase; 1 / 0 at a song start; 1 / .2 then .2 / .2 on the sweep | | 0.25 25% (1 seq) · .5 12% (3 seq / 2 songs) · 1 6% (2 / 2) |
| Blur | 0 / 4 / 9 | softens the bands | absent 87% · 4 12% (2 / 2) · 9 |

**How to permute.** Flip Reverse every 8 beats (Light of Christmas does it for 40 s of intro)
and change nothing else. Between sections move Speed (1 in the intro, 3 from the first chorus)
and the palette (RGB → white + blue → RGB). On the matrix change Thickness per chorus (3, 3,
10, 3) and double the layer with a second palette. Dots (Skip 3) for a verse, solid for the
chorus. Thickness 100 only under a reveal.

### Layering recipes

| Name | Stack (top → bottom) | Blend | Use |
|---|---|---|---|
| **Outline chase** | Marquee, Single Line | Normal | 43 placements alone; the roofline sign |
| **Frame under the twin** | Spirals · Spirals · Pinwheel · Marquee · Marquee (identical, second palette) | all Normal | the LoC chorus matrix (9 × 2): the hero's spirals and pinwheel inside a chasing frame |
| **Frame round a face** | Marquee · Faces (· Faces) | Normal | 18 + 10 placements (2 seq / 2 songs): the singing tree gets a chasing border |
| **Meter over the chase** | VU Meter · Marquee | Normal | 13–14 pairs (2 seq / 2 songs): the beat stamp rides the ring |
| **Striped reveal** | Spirals · Marquee Thickness 100 Stagger 50 | Spirals: `1 reveals 2`; Marquee: `Layered` | the spirals cut the band sweep into their shape (8, 1 seq) |

### Value curves

| Want | Curve | Dial |
|---|---|---|
| the gaps pumping on the beat | Skip Size Timing Track Fade Proportional on the beat track (32, 1 seq / 1 song) | Skip Size |
| the frame turning over the 8 beats | Rotation Ramp 0 → 100 (clockwise) or 100 → 0 (16 each, 1 seq) | buffer rotation |
| a wiped-in sweep | In Transition Adjust Ramp 33 → 67; the Custom out-transition hump | transition |

```
E_VALUECURVE_Marquee_Skip_Size: Active=TRUE|Id=ID_VALUECURVE_Marquee_Skip_Size|Type=Timing Track Fade Proportional|Min=0.00|Max=100.00|TT=Beat Count|P2=100.00|P3=50.00|TO=75|RV=TRUE|
B_VALUECURVE_Rotation: Active=TRUE|Id=ID_VALUECURVE_Rotation|Type=Ramp|Min=0.00|Max=100.00|P2=100.00|RV=TRUE|
B_VALUECURVE_Rotation: Active=TRUE|Id=ID_VALUECURVE_Rotation|Type=Ramp|Min=0.00|Max=100.00|P1=100.00|RV=TRUE|
T_VALUECURVE_In_Transition_Adjust: Active=TRUE|Id=ID_VALUECURVE_In_Transition_Adjust|Type=Ramp|Min=0.00|Max=100.00|P1=33.00|P2=67.00|RV=TRUE|
T_VALUECURVE_Out_Transition_Adjust: Active=TRUE|Id=ID_VALUECURVE_Out_Transition_Adjust|Type=Custom|Min=0.00|Max=100.00|RV=TRUE|Values=0.00:0.30;0.14:0.50;0.22:0.63;0.31:0.78;0.42:0.85;0.51:0.78;0.57:0.69;0.64:0.56;0.73:0.40;0.80:0.28;0.89:0.20;0.93:0.20;1.00:0.29|
```

The Skip Size curve names the sequencer's own `TT=Beat Count` track; on our shows write
`TT=Beats`, and it only works after `xlo finalize` patches the Beats track into the sequence
— `xlo apply` has no tracks, so until then the Skip Size sits at its static value.

### Prop fit and render style

Matrix 42% (2 seq / 1 song), mega tree 16% (3 / 3), mini trees 14% (3 / 3), roofline 12% (2 /
2), arches 11% (3 / 3), windows 3% (1 seq). `Single Line` or `Per Model Single Line` on
rooflines, arches, trees and canes (the chase along the string; 3 seq / 3 songs each);
`Default` on the matrix (the frame); `Per Preview` only with Thickness 100 (the band sweep).
`render_style.py` puts Marquee in `_SWEEP` and falls back to `Per Preview`, which on a sparse
yard draws a box round the whole display's bounding rectangle and lights almost nothing —
always set `render_style`. On our layout: the house outline (`Single Line`), the stakes `Per
Model Single Line`, a frame on the hero seed matrices around a feature; the characters' faces
get the face frame.

### Timing

8 beats 43% and 7 beats 11% (the same cells on a short bar), 13–15 beats for the tree ring
and the sweep's longer holds, 28–35 beats held on the outline through an intro (LoC 0:40–
1:12). Median 3.88 s; nothing under 2 s. Fades 0.25 / 0.25 on the matrix frame, .5 / .5 on the
per-model chase, 1 / 0 at the song's first placement, 1 / .2 on the first band sweep and .2 /
.2 on its repeats. Reverse flips on the 8-beat cut.

### Exemplars

| Where | Stack top → bottom | Why it works |
|---|---|---|
| **Light of Christmas.xsq** 0:02–0:40 (2.05–39.75), intro, Outlines | Marquee Band 3, Skip 0, Thickness 1, Speed 1, `Single Line`, red + green + blue, fade-in 1 on the first; 7–9 beat cells with Reverse off, on, off, on …; then 35 beats white + blue, 31 beats Reverse RGB; Speed 3 from 1:51 | a one-pixel RGB chase runs the roofline for the whole intro and the only thing that changes is which way it goes, every two bars; the chorus just speeds it up |
| Light of Christmas.xsq 1:16–1:19 (75.55–79.42), 2:10, 3:28, CHORUS OWL, Matrix1 | Spirals · Spirals · Pinwheel · Marquee · Marquee — both Band 3, Thickness 3, Speed 3, Skip Size on the Beat Count curve, Rotation Ramp, fade 0.25 / 0.25, #008040 + yellow (then + blue), 8 beats | the hero twin spins inside a frame whose gaps pump on the beat and which turns once across the phrase; the doubled layer thickens it without changing it |
| Light of Christmas.xsq 2:56–3:00 (176.20–180.07), CHORUS OWL, Matrix1 | Spirals · Spirals · Marquee Thickness 10, #008040 + #00FF00 + black + black · Marquee Thickness 10, #004080 + #0000FF + black + black | the third chorus trades the Pinwheel for a thick two-tone frame, green on one layer and blue on the other, gapped by the two blacks |
| **Idina Menzel - Christmas Just Ain't Christmas**, 0:00–0:17 (0.65–17.50), intro, MegaTree | Marquee Reverse, Band 3, Skip 3, Thickness 1, Speed 3, `Single Line`, `Layered`, #8080FF + #0000FF + #FF00FF (+ #FF0080), 13–15 beats, alone | a dotted pastel ring crawls round the tree's outline as the song opens |
| Christmas Just Ain't Christmas 0:17–0:21 (17.50–20.90), 0:25, 0:50, 0:59, 1:24, 1:32, 2:14, 2:22, MegaTree | Spirals `1 reveals 2` · Marquee Reverse, Band 3, Skip 0, Speed 3, Stagger 50, Start 100, Thickness 100, `Per Preview`, `Layered`, fade 1 / .2 then .2 / .2, four colors | the whole tree fills with staggered bands and the spirals above reveal only their own shape of them: a striped spiral for the phrase head, eight times |

### Anti-patterns

- **Speed above 3.** `effect_meta` allows 1–8; the corpus stops at 3. Faster smears the bands.
- **Thickness 1 on the matrix.** Invisible from the street; the matrix frame is 3–10.
- **One color.** 2% of the corpus: with one color nothing chases. Two or three, or black as the
  gap color.
- **A Marquee per beat.** Never under 2 s; the motion is inside the effect. Hold 8 beats and
  flip Reverse on the cut.
- **`Per Preview` on a group.** Our fallback for Marquee; a box round the yard's bounding
  rectangle. `Single Line` / `Per Model Single Line` on lines, `Default` on the matrix.
- **Wrap, Scale or Center moved.** Never in the corpus.
- **Reverse never flipped.** The LoC intro is the lesson: 40 s on one effect because the
  direction changes every two bars.

### What code can realize today

- `look_id` + `knobs`: `Marquee#2` (the free one: `E_CHECKBOX_Marquee_Reverse`,
  `E_SLIDER_Marquee_Band_Size` 3–5, `_Skip_Size` 0–23, `_Speed` 1–3, `_Stagger` 0–29,
  `_Thickness` 1–9, `B_CHOICE_BufferStyle` — use the `render_style` field), `Marquee#1`
  (Thickness 1–25, Blur 4–9, fades as knobs — use the fields), `Marquee#14` / `#12` (the
  Thickness-1 chase frozen; Reverse and Speed), `Marquee#11` (Single Line + Reverse frozen),
  `Marquee#8` (buffer knob, Speed, fade-in), `Marquee#3` / `#4` / `#7` (the dotted ring,
  Layered frozen), `Marquee#5` (the band sweep, everything frozen incl. `Per Preview`,
  `Layered` and both transition curves), `Marquee#9` (deep border frozen), `Marquee#0` (soft
  bands). Thickness 10 is reachable through `Marquee#1` (1–25); Thickness 100 only through
  `Marquee#5`.
- `settings`: the Skip Size `TT=Beats` curve and the two Rotation ramps (above),
  `B_SLIDER_Blur`; `blend: "Layered"`, `render_style`, `fade_in` / `fade_out` are fields.
  `direction` ltr / rtl maps onto Reverse 0 / 1 (`effect_meta`); `direction: "alternate"`
  flips it on odd *bars*, so with `cell_beats: 4` every cell flips and with `cell_beats: 8`
  every cell lands on an even bar and nothing flips — for the LoC 8-beat flip use
  `cell_beats: 4` and accept the chase restarting each bar, or two sections. `twin: "color"`
  is the doubled frame in a second palette exactly (LoC 2:56: identical settings, two
  palettes).
- `effect_meta.py`: speed `E_SLIDER_Marquee_Speed` 1–8 (`int` — keep knobs at 1–3), energy
  band 2–3, no duration class (free), `chase_family`; `render_style.py` `_SWEEP` → `Per
  Preview` fallback. Nothing synthesizes a Marquee frame, the face border or the striped
  reveal; the weave can direct and speed one as a chase-family carrier if a recipe names it.
