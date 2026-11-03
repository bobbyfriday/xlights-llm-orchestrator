# Curtain

A drape drawn across the buffer: in the corpus a one-beat open-then-close twitch on the Light of Christmas matrix and tree, a black close-and-open over the tree's stack, and a slow blue close over the whole house.

---

## Corpus facts

> Generated 2026-11-03 from the deduped corpus: **22 community sequences, 14 distinct songs** (xLights 2020.45–2025.08; 0 byte-identical files dropped). 10 sequences / 6 songs use Curtain: **742 placements, 2,219 overlapping pairs.** Every share carries its breadth (sequences / songs); a habit in one sequence is one sequencer's habit, however many placements it has.
>
> Sources by placements: Light Of Christmas (main) 673 · Light Of Christmas (Bill Jenkins) 17 · Kid On Christmas (Greg Colburn) 16 · Shut Up and Dance (Jeremy Poling) 13 · Kid On Christmas (Jeremy Poling) 9 · Christmas Just Ain't Christmas 5 · Light Of Christmas (XATW sharer B) 3 · Kid On Christmas (Eliot Wisser) 3 · the other 2 files 3 together.

### Where it is placed

| Prop class | Share | Breadth | Example model names |
|---|---|---|---|
| matrix | 54% | 1 seq / 1 song | Matrix1, Matrix2, P10 |
| megatree | 39% | 5 seq / 4 songs | MegaTree Singing Faces, MegaTree1, MegaTree 1 |
| group_all | 4% | 4 seq / 3 songs | *Entire Display no Floods, Entire Display 180, Entire Display |
| flood | 2% | 3 seq / 3 songs | Flood Lights |
| roofline | 1% | 2 seq / 2 songs | House_Outline, Outlines |
| spinner | 1% | 2 seq / 1 song | Spinner |
| snowflake | 0% | 1 seq / 1 song | Snowflakes |
| cane | 0% | 1 seq / 1 song | Candy Canes |
| tree | 0% | 1 seq / 1 song | Mini Trees |

### Dials observed

Share · breadth per value; `curved` = that key has an active value curve instead of a static value.

| Key | Values |
|---|---|
| `Repeat` (checkbox) | 0: 96% · 9 seq / 6 songs — 1: 4% · 2 seq / 2 songs — range 0…1 |
| `Edge` (choice) | middle: 86% · 1 seq / 1 song — center: 8% · 4 seq / 4 songs — top: 3% · 2 seq / 2 songs — bottom: 2% · 4 seq / 3 songs — right: 0% · 2 seq / 2 songs — left: 0% · 1 seq / 1 song |
| `Effect` (choice) | open then close: 88% · 3 seq / 3 songs — open: 6% · 6 seq / 4 songs — close: 5% · 7 seq / 5 songs — close then open: 1% · 2 seq / 2 songs |
| `Swag` (slider) | 0: 94% · 7 seq / 3 songs — 3: 5% · 6 seq / 4 songs — 1: 1% · 2 seq / 2 songs — range 0…3 |
| `Speed` (textctrl) | 1.0: 53% · 8 seq / 5 songs — 0.2: 43% · 1 seq / 1 song — 8.0: 3% · 1 seq / 1 song — 2.0: 1% · 1 seq / 1 song — 2: 0% · 1 seq / 1 song — 1.2: 0% · 1 seq / 1 song — range 0.2…8 |
| `B_CHOICE_BufferStyle` | <absent>: 96% · 10 seq / 6 songs — Per Model Per Preview: 1% · 2 seq / 2 songs — Per Model Default: 1% · 2 seq / 2 songs — Per Preview: 1% · 2 seq / 2 songs — Default: 0% · 1 seq / 1 song — Default Model As A Pixel: 0% · 1 seq / 1 song — Vertical Stack: 0% · 1 seq / 1 song |
| `B_CHOICE_BufferTransform` | <absent>: 99% · 9 seq / 5 songs — Rotate CC 90: 1% · 4 seq / 4 songs |
| `T_CHOICE_LayerMethod` | <absent>: 99% · 9 seq / 5 songs — Layered: 1% · 1 seq / 1 song — 1 is True Unmask: 0% · 1 seq / 1 song |
| `T_TEXTCTRL_Fadein` | 0.10: 86% · 1 seq / 1 song — <absent>: 10% · 9 seq / 5 songs — 0.25: 3% · 1 seq / 1 song — 0.20: 1% · 1 seq / 1 song — 2: 0% · 2 seq / 2 songs — range 0.1…2 |
| `T_TEXTCTRL_Fadeout` | 0.10: 86% · 1 seq / 1 song — <absent>: 9% · 10 seq / 6 songs — 0.25: 3% · 1 seq / 1 song — 0.20: 1% · 1 seq / 1 song — .2: 0% · 1 seq / 1 song — 1.00: 0% · 1 seq / 1 song — 1: 0% · 1 seq / 1 song — range 0.1…1 |

### Value curves

| Parameter | Share · breadth | Shapes |
|---|---|---|
| any curve | 91% · 2 seq / 2 songs | |
| `B_VALUECURVE_Rotation` | 90% · 1 seq / 1 song | Ramp 669 |
| `T_VALUECURVE_Out_Transition_Adjust` | 0% · 1 seq / 1 song | Custom 3 |

Most-used exact strings (copy verbatim; `Min`/`Max` are the parameter range, `P*` the real values):

```
B_VALUECURVE_Rotation (322, 1 seq / 1 song): Active=TRUE|Id=ID_VALUECURVE_Rotation|Type=Ramp|Min=0.00|Max=100.00|P2=50.00|RV=TRUE|
B_VALUECURVE_Rotation (242, 1 seq / 1 song): Active=TRUE|Id=ID_VALUECURVE_Rotation|Type=Ramp|Min=0.00|Max=100.00|P1=50.00|RV=TRUE|
B_VALUECURVE_Rotation (80, 1 seq / 1 song): Active=TRUE|Id=ID_VALUECURVE_Rotation|Type=Ramp|Min=0.00|Max=100.00|P1=50.00|P2=10.00|RV=TRUE|
B_VALUECURVE_Rotation (15, 1 seq / 1 song): Active=TRUE|Id=ID_VALUECURVE_Rotation|Type=Ramp|Min=0.00|Max=100.00|P2=100.00|RV=TRUE|
T_VALUECURVE_Out_Transition_Adjust (3, 1 seq / 1 song): Active=TRUE|Id=ID_VALUECURVE_Out_Transition_Adjust|Type=Custom|Min=0.00|Max=100.00|RV=TRUE|Values=0.00:0.30;0.14:0.50;0.22:0.63;0.31:0.78;0.42:0.85;0.51:0.78;0.57:0.69;0.64:0.56;0.73:0.40;0.80:0.28;0.89:0.20;0.93:0.20;1.00:0.29|
```

### Palette habits

Colors per placement: 0: 0% · 1: 4% · 2: 5% · 3: 89% · 4: 0% · 5: 0% · 6: 1%.
Black as a color: 93% · 3 seq / 3 songs. Sparkles on: 93% · 5 seq / 3 songs.
Top palettes: #00FF00+#0000FF+#000000 320 · #0080C0+#FFFF00+#000000 240 · #0080C0+#00FF00+#000000 80 · #00FF00+#000000 23 · #000000 16 · #0080FF+#0080C0+#0080FF 6 · #000000+#000000 5 · #FF0000+#000000 5.

### Duration

Median 0.47 s. <1 s 89% · 1–2 s 3% · 2–4 s 7% · 4–8 s 1% · 8–16 s 0%.
In beats (742 placements with a beat track): 1 beats 83% · 2 beats 5% · 8 beats 4% · 0 beats 3% · 3 beats 2% · 7 beats 1% · 6 beats 1% · 4 beats 1%.

### Stacking

**97% of placements share the model with at least one concurrent effect (10 seq / 6 songs); 92% with three or more (4 seq / 4 songs).**

Partner types (pairs · sequences): Curtain 1940 · 1 · Warp 101 · 1 · Pinwheel 46 · 4 · Spirals 36 · 3 · SingleStrand 14 · 2 · Snowflakes 13 · 3 · Shape 12 · 1 · Wave 10 · 1 · Faces 10 · 1 · Meteors 7 · 4 · Butterfly 7 · 2 · Kaleidoscope 5 · 1 · Shockwave 5 · 2 · Shader 4 · 1 · On 3 · 2 · Twinkle 2 · 2 · Pictures 2 · 1 · Fan 1 · 1 · Color Wash 1 · 1.

Above Curtain (partner type, the partner's blend): Curtain 970 Normal · Warp 101 Normal · Pinwheel 40 Layered · Wave 10 Normal · Faces 10 Normal · Snowflakes 7 Normal · Kaleidoscope 5 Normal · Butterfly 5 2 is Mask · Meteors 2 Layered · Pictures 2 Normal · SingleStrand 1 Normal · Meteors 1 Normal · Shockwave 1 Layered · Twinkle 1 Normal.

Beneath Curtain (partner type, Curtain's own blend over it): Curtain 970 Normal · Spirals 36 Normal · SingleStrand 13 Normal · Shape 12 1 is True Unmask · Pinwheel 6 Normal · Snowflakes 4 Normal · Shader 4 Normal · Meteors 4 Normal · Shockwave 4 Normal · On 3 Normal · Butterfly 2 Normal · Snowflakes 2 1 is True Unmask · Fan 1 Normal · Twinkle 1 Normal · Color Wash 1 Normal.

Recurring full stacks (top → bottom, `*` = the mined effect): *Curtain > Curtain > Curtain > Curtain (136) · Curtain > *Curtain > Curtain > Curtain (136) · Curtain > Curtain > *Curtain > Curtain (136) · Curtain > Curtain > Curtain > *Curtain (136) · Warp > *Curtain > Curtain > Curtain > Curtain (24) · Warp > Curtain > *Curtain > Curtain > Curtain (24) · Warp > Curtain > Curtain > *Curtain > Curtain (24) · Warp > Curtain > Curtain > Curtain > *Curtain (24) · *Curtain (23) · Pinwheel > Pinwheel > *Curtain > Curtain (10) · Pinwheel > Pinwheel > Curtain > *Curtain (10) · Faces > Snowflakes > *Curtain > SingleStrand > Spirals > Spirals (7) · *Curtain > Spirals (6) · Kaleidoscope > Wave > Wave > Warp > *Curtain (5) · Butterfly > *Curtain (5) · *Curtain > Snowflakes (4).

Same-type twins (970 top-over-bottom pairs): identical effect settings 100%; buffer transform differs 0%.

---

## Craft

### Identity and role

Curtain draws the palette as a drape from an **Edge** and `open`s it (withdraws it), `close`s
it (draws it across) or does both in one placement. `left` / `center` / `right` travel
horizontally (center = two halves parting left and right); `bottom` / `top` / `middle` travel
vertically (middle = parting up and down). **Swag** 0–3 bends the leading edge into a hanging
drape (0 is a flat shutter). **Speed** is cycles per placement: 1.0 is one full travel, 0.2 a
fifth of one (the drape barely moves), 2 a double, 8 a flutter; **Repeat** loops it. The
palette lays across the drape as bands, and the corpus almost always gives it three colors with
black as one of them (89% three colors, black in 93%): black is the gap between the bands.
Sparkles are on in 93%.

The corpus is one sequence's habit plus a handful of gestures: Light of Christmas (main) holds
673 of 742 placements, so every share below is read against that. The roles that survive the
breadth check:

- **Carrier / twitch** (83% one beat): four Curtain layers, one per SubBuffer quarter, `middle`
  / `open then close` at Speed 0.2 on one beat and 1.0 on the next, fades 0.10, re-cut every
  beat (640 placements, 1 seq / 1 song).
- **Mask / wipe**: a black Curtain `top` / `close` with Swag 3 over the tree's stack for two
  beats, then `bottom` / `open` for three — the Kid On Christmas blackout (`top` / `close` in
  2 seq / 2 songs; `bottom` / `open` with Swag 3 in Greg Colburn's file).
- **Phrase gesture**: a 5–16 beat `top` / `close` in blue across the whole display (Light of
  Christmas Entire Display 180, nine times) — what our `place_phrase_gesture` means by a
  Curtain.
- A center `open` on a spinner or flood (2 seq / 1 song) as a reveal.

It is never a bed: it ends, and a finished `close` is a flat fill.

### Thematic fit

A curtain says *reveal* and *conceal*: the show opening (center `open` on the first downbeat),
the verse ending (`close`), a scene change, a blackout before the drop. Swag 3 reads as fabric,
Swag 0 as a blind. A black curtain is the stage going dark — on Halloween, a black `close` with
Swag 3 over the hero's stack on a door slam or a scream, then `open` from the bottom as the
verse returns; orange + purple + black bands opening from center on the intro. Christmas is
the Light of Christmas green + blue + black and #0080C0 + yellow + black twitches on the tree,
and a blue close over the house for a lull. Keep the black entry: without it the curtain is a
solid wipe.

### Anchors (starting points, not a menu)

| Anchor | Settings | Catalog look | Where | Dials to move |
|---|---|---|---|---|
| **Beat twitch** | Edge middle, open then close, Swag 0, Speed 0.2 (or 1.0 on alternate beats), fades 0.10, 1 beat, three colors with black, one layer per SubBuffer quarter with a Rotation ramp 0 → 50 or 50 → 0 | `Curtain#9` (640; frozen middle / open then close / Swag 0 / fades 0.10; knobs SubBuffer quarters, Rotation curves, Speed {0.2|1.0}) | Light of Christmas matrix and mega tree, verse 2 into the chorus | Speed 0.2 vs 1.0 beat by beat; one quarter instead of four |
| **Black close / open** | Edge top, close, Swag 3, Speed 1.0, black, 2 beats; then Edge bottom, open, Swag 3, 3 beats | `Curtain#12` (knobs Repeat, Edge {bottom|center|right|top}, Effect {close|close then open|open}, Swag 0–3, Speed {1.0|2}) | Kid On Christmas (Greg Colburn) MegaTree Singing Faces, six times | Swag 0 for a shutter; the close alone as an exit |
| **House close** | Edge top, close, Swag 0, Speed 1.0, blue (#0080FF + #0080C0 + #0080FF, or blue + #8000FF + blue), 5–16 beats, fade in 2 on the long one, fade out 1 on the last | `Curtain#12` / `#3` (Repeat 0, Speed 1.0 frozen; knobs buffer style, Edge {center|top}, Effect {close|open}, Swag 0–3); `#16` (top / close / fade-out 1 frozen) | Light of Christmas Entire Display 180, nine placements | a bar to four bars; Edge bottom to close upward |
| **Center open** | Edge center, open, Swag 3, Speed 1.0, Per Preview, fades 0.20 | `Curtain#5` (frozen) | 1 seq / 1 song: the reveal | Swag 0; a downbeat start |
| **Flutter** | Repeat on, Edge center, open, Swag 0, Speed 8.0, fades 0.25 | `Curtain#11` (knobs Repeat, Effect {open|open then close}, Speed {2.0|8.0}, Rotation curve) | Light of Christmas (20, 1 seq) | Speed 2.0 for a double open |
| **Vertical per model** | Edge center, close (or open, open then close), Rotate CC 90, Per Model Per Preview | `Curtain#1` (transform frozen; knobs buffer {Per Model Per Preview|Vertical Stack}, Effect) | 2 seq / 2 songs on trees and spinners | Effect per phrase |
| **Curtain in a shape** | the drape with `1 is True Unmask` over a Shape, or `Curtain#8` (right / close / Swag 3 / Speed 1.2, blend and Rotate CC 90 frozen) | `Curtain#8`; or any look + `blend` | 12 Shape pairs, 1 seq | |

**Dials** — pick from the observed values, then move one:

| Dial | Sane range | Moving it | Corpus picks |
|---|---|---|---|
| Edge | left / center / right (horizontal) · bottom / top / middle (vertical) | where the drape hangs from and which way it travels | middle (the twitch) · center (4 seq / 4 songs) · top (2 / 2) · bottom (4 / 3) · right (2 / 2) |
| Effect | open / close / open then close / close then open | | open then close (3 / 3) · open (6 / 4) · close (7 / 5) · close then open (2 / 2) |
| Swag | 0–3 | 0 flat edge, 3 deep drape | 0 · 3 (6 / 4) · 1 (2 / 2) |
| Speed | 0.2–8 | how far it travels: 0.2 a twitch, 1.0 one full travel, 2 a double, 8 a flutter | 1.0 (8 / 5) · 0.2 · 2.0 · 8.0 · 1.2 |
| Repeat | off / on | loops the travel | off 96% |
| Buffer | Default / Per Preview / Per Model Per Preview / Per Model Default / Vertical Stack / Default Model As A Pixel | one drape across the group vs one per prop | absent 96% |
| Transform | Rotate CC 90 (4 / 4) | turns a horizontal edge into a vertical travel | |
| Blend | Normal / Layered / 1 is True Unmask | | Normal 99% |
| Fades | 0.10 (the twitch) · 0.25 · 0.20 · in 2 / out 1 on long closes | | |
| Colors | 3, one of them black | the bands across the drape | green + blue + black · #0080C0 + yellow + black · black alone |

**How to permute.** Alternate the edge between phrases: close from the top, open from the
bottom. Use Speed to decide how far it gets (0.2 twitch, 1.0 full, 2 double). Give the next
section the other axis (center → middle). Swag 3 for the chorus drape, 0 for the verse
shutter. Keep the bands; change the middle color.

### Layering recipes

| Name | Stack (top → bottom) | Blend | Use |
|---|---|---|---|
| **Four-quarter twitch** | Warp (optional) · Curtain × 4, one per SubBuffer quarter | Normal | the Light of Christmas beat shimmer (136 × 4; Warp over it 24) |
| **Blackout over the body** | Faces · Snowflakes · Curtain black top / close then bottom / open · SingleStrand · Spirals · Spirals | Curtain: Normal; SingleStrand: `2 is Unmask` | the face keeps singing while everything beneath wipes to black and returns |
| **House drop** | Curtain top / close blue · Shader / Meteors / Pinwheel / On | Normal | a slow blue drape over the whole display's texture |
| **Curtain under the pinwheel** | Pinwheel · Pinwheel · Curtain · Curtain | Pinwheel: `Layered` (40 pairs) | the drape behind a spinning pair |
| **Curtain in a shape** | Curtain · Shape | Curtain: `1 is True Unmask` (12) | the drape only inside the shape |
| **Butterfly through the drape** | Butterfly · Curtain | Butterfly: `2 is Mask` (5) | |

### Value curves

No Curtain dial is curved in the corpus. The 91% figure is the Light of Christmas buffer
rotation under every twitch (1 seq / 1 song, 669): with `B_SLIDER_Rotations=10` the buffer
makes a half turn, or half a turn back, during the one-beat open-then-close.

| Want | Curve | Dial |
|---|---|---|
| the drape turning a half turn over the beat | `B_VALUECURVE_Rotation` Ramp 0 → 50 (322) or 50 → 0 (242) | buffer rotation |
| a quarter back | Ramp 50 → 10 (80) | buffer rotation |
| a full turn | Ramp 0 → 100 (15) | buffer rotation |

```
B_VALUECURVE_Rotation: Active=TRUE|Id=ID_VALUECURVE_Rotation|Type=Ramp|Min=0.00|Max=100.00|P2=50.00|RV=TRUE|
B_VALUECURVE_Rotation: Active=TRUE|Id=ID_VALUECURVE_Rotation|Type=Ramp|Min=0.00|Max=100.00|P1=50.00|RV=TRUE|
B_VALUECURVE_Rotation: Active=TRUE|Id=ID_VALUECURVE_Rotation|Type=Ramp|Min=0.00|Max=100.00|P1=50.00|P2=10.00|RV=TRUE|
B_VALUECURVE_Rotation: Active=TRUE|Id=ID_VALUECURVE_Rotation|Type=Ramp|Min=0.00|Max=100.00|P2=100.00|RV=TRUE|
```

None runs on a timing track; a `TT=Beats` curve on any dial only works after `xlo finalize`
patches the Beats track in.

### Prop fit and render style

Matrix 54% (one sequence's Matrix1 / Matrix2 / P10), mega tree 39% (5 seq / 4 songs), whole
display 4% (4 / 3), floods 2% (3 / 3), roofline 1% (2 / 2), spinners (2 / 1). A curtain needs
height or width: the matrix and the tree as a canvas (Default), the whole house as one buffer
(Per Preview) for the house close, Per Model Per Preview with Rotate CC 90 for a vertical drape
on each tree. On a line it is a fill from one end, which is fine as a wipe. On our layout: the
hero matrix for the quarter twitch, `SEM_ALL` for the close, the mega-tree-class seed matrices
for the black close / open over their stack.

### Timing

One beat (83%) for the twitch, re-cut every beat with fades 0.10; 2 beats to close and 3 to
open for the blackout; 5–16 beats for the house close (fade in 2 for the 16-beat one, fade out
1 for the last). The 8-beat double open-close (Speed 2.0, fades 0.25) sits under a kaleidoscope
in the verse.

### Exemplars

| Where | Stack top → bottom | Why it works |
|---|---|---|
| **Light of Christmas.xsq** 1:11–1:15, verse 2 into the chorus, MegaTree Singing Faces | four Curtain layers, middle / open then close / Swag 0 / fades 0.10, 1 beat, green + blue + black: layers 0–3 at Speed 0.2 on one beat, layers 4–7 at Speed 1.0 on the next, alternating; #0080C0 + yellow + black from 1:13 | the drape twitches a fifth of the way on one beat and all the way on the next, with the buffer turning under it |
| Light of Christmas.xsq 0:21–0:25, verse 1, MegaTree Singing Faces | Kaleidoscope · Wave · Wave · Warp · Curtain center / open then close / Swag 0 / Speed 2.0 / fades 0.25, yellow → blue gradient + black + black, 8 beats | a double open-close under the kaleidoscope for the verse's first phrase |
| Light of Christmas.xsq 2:43–2:52, Entire Display 180 | Meteors · Curtain top / close / Swag 0 / Speed 1.0, blue + #8000FF + blue, 16 beats, fade in 2 | the whole house closes down in blue over four bars under the meteors |
| **XATW Kid on Christmas Greg Colburn.xsq** 0:49–0:53 (again at 1:20, 1:43, 2:13, 2:38), MegaTree Singing Faces | Faces · Snowflakes · Curtain black top / close / Swag 3 (2 beats) then bottom / open / Swag 3 (3 beats) · SingleStrand `2 is Unmask` · Spirals · Spirals | the tree's body blacks out from the top and returns from the bottom while the face keeps singing above it |

### Anti-patterns

- **A Curtain alone on a group for a phrase.** Speed 1.0, Swag 0: a slow fill and then a dead
  prop. Our phrase gesture can produce this; give it a texture beneath, or make it the black
  close over the stack.
- **One color.** A solid wipe; the corpus runs three with black.
- **The wrong edge for the prop.** `top` / `open` on a tree lifts from the bottom and reads
  upside down; the corpus closes from the top and opens from the bottom.
- **open then close over 8 beats at Speed 1.0.** Four beats of nothing, then a fill; the twitch
  is a one-beat thing and the long form is Speed 2.0.
- **Repeat at Speed 8 for more than a bar.** A strobe.

### What code can realize today

- `look_id` + `knobs`: `Curtain#12` (Edge, Effect, Swag, Repeat, Speed as knobs — the general
  anchor), `#3` (adds buffer styles; Edge center | top; close | open), `#9` (the twitch:
  SubBuffer quarters, Rotation curves, Speed {0.2|1.0}), `#11` (Repeat, Speed 2–8, Rotation
  curve), `#5` (center open, Per Preview), `#1` (Rotate CC 90 per model), `#16` (top close,
  fade-out 1), `#14` (fade-in 2). The picker rotates `#12`, `#11`, `#3`, `#1`, `#5`, `#10`. The
  three-color palette with black goes in the layer's `palette`.
- `settings`: the Rotation curve strings and `B_CUSTOM_SubBuffer`; `blend` (`1 is True Unmask`
  for the shape recipe), `transform` (`Rotate CC 90`), `render_style` and the fades are fields;
  `cell_beats: 1` makes the twitch.
- `effect_meta.py`: Curtain has a speed key (`E_TEXTCTRL_Curtain_Speed` 0.5–4), energy 2–3,
  `phrase` class, no direction map — `direction: "up"` does nothing; set `E_CHOICE_Curtain_Edge`
  and `E_CHOICE_Curtain_Effect` as knobs on `#12`. Code synthesizes one Curtain on its own as
  the phrase gesture (`place_phrase_gesture`: the Morph / Curtain / Fill rotation, entering at
  bar 2 for four bars), withheld when the section has a stack. The black close / open pair and
  the four-quarter twitch are authored stacks only.
