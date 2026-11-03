# Kaleidoscope

An overlay, not a picture: with Canvas on it tiles a wedge of whatever is beneath it into a mandala on the matrix, so the Pinwheel or Bars under it becomes the design.

---

## Corpus facts

> Generated 2026-11-03 from the deduped corpus: **22 community sequences, 14 distinct songs** (xLights 2020.45–2025.08; 0 byte-identical files dropped). 5 sequences / 4 songs use Kaleidoscope: **35 placements, 86 overlapping pairs.** Every share carries its breadth (sequences / songs); a habit in one sequence is one sequencer's habit, however many placements it has.
>
> Sources by placements: Kid On Christmas (Greg Colburn) 13 · Shut Up and Dance (Tammy Ghee) 12 · Light Of Christmas (main) 5 · Light Of Christmas (XATW sharer A) 4 · Save Your Tears (AG) 1.

### Where it is placed

| Prop class | Share | Breadth | Example model names |
|---|---|---|---|
| matrix | 94% | 5 seq / 4 songs | Matrix1, Matrix2, P10 |
| megatree | 6% | 1 seq / 1 song | MegaTree Singing Faces, MegaTree1 |

### Dials observed

Share · breadth per value; `curved` = that key has an active value curve instead of a static value.

| Key | Values |
|---|---|
| `Type` (choice) | Square: 60% · 4 seq / 4 songs — Triangle: 40% · 3 seq / 3 songs |
| `Rotation` (slider) | **curved 9% · 1 seq / 1 song** — 0: 37% · 4 seq / 3 songs — 106: 37% · 1 seq / 1 song — 28: 9% · 1 seq / 1 song — 359: 9% · 1 seq / 1 song — range 0…359 |
| `Size` (slider) | 32: 37% · 1 seq / 1 song — 47: 14% · 1 seq / 1 song — 25: 11% · 1 seq / 1 song — 100: 11% · 2 seq / 2 songs — 23: 9% · 1 seq / 1 song — 86: 9% · 1 seq / 1 song — 33: 9% · 1 seq / 1 song — range 23…100 |
| `X` (slider) | 50: 100% · 5 seq / 4 songs |
| `Y` (slider) | 50: 91% · 5 seq / 4 songs — 0: 9% · 1 seq / 1 song — range 0…50 |
| `E_TEXTCTRL1` | The warp effect distorts the pixels in the layers below it. The Canvas option in Layer Blending must be enabled for it to work.: 60% · 3 seq / 2 songs — The Kaleidoscope effect distorts the pixels in the layers below it. The Canvas option in Layer Blending must be enabled for it to work.: 40% · 2 seq / 2 songs |
| `T_CHOICE_LayerMethod` | <absent>: 89% · 4 seq / 4 songs — Brightness: 11% · 1 seq / 1 song |
| `T_TEXTCTRL_Fadein` | <absent>: 80% · 4 seq / 4 songs — 0.25: 14% · 1 seq / 1 song — 0.75: 6% · 1 seq / 1 song — range 0.25…0.75 |
| `T_TEXTCTRL_Fadeout` | <absent>: 69% · 3 seq / 3 songs — 0.25: 23% · 2 seq / 2 songs — 4.00: 6% · 1 seq / 1 song — 5: 3% · 1 seq / 1 song — range 0.25…5 |
| `B_SLIDER_Blur` | <absent>: 63% · 4 seq / 3 songs — 5: 29% · 1 seq / 1 song — 3: 9% · 1 seq / 1 song — range 3…5 |

### Value curves

| Parameter | Share · breadth | Shapes |
|---|---|---|
| any curve | 17% · 1 seq / 1 song | |
| `B_VALUECURVE_Rotation` | 9% · 1 seq / 1 song | Ramp 3 |
| `E_VALUECURVE_Kaleidoscope_Rotation` | 9% · 1 seq / 1 song | Ramp Up/Down 3 |

Most-used exact strings (copy verbatim; `Min`/`Max` are the parameter range, `P*` the real values):

```
B_VALUECURVE_Rotation (3, 1 seq / 1 song): Active=TRUE|Id=ID_VALUECURVE_Rotation|Type=Ramp|Min=0.00|Max=100.00|P2=100.00|RV=TRUE|
E_VALUECURVE_Kaleidoscope_Rotation (3, 1 seq / 1 song): Active=TRUE|Id=ID_VALUECURVE_Kaleidoscope_Rotation|Type=Ramp Up/Down|Min=0.00|Max=359.00|P2=359.00|RV=TRUE|
```

### Palette habits

Colors per placement: 0: 9% · 1: 26% · 3: 46% · 4: 11% · 5: 9%.
Black as a color: 17% · 1 seq / 1 song. Sparkles on: 0% · 0 seq / 0 songs.
Top palettes: (gradient) 17 · #0000FF 5 · #07DA61+#1B47FA+#FDEF48+#E903C0 4 · #800080+#00FF00+#000000 3 · #00FFFF 3 · #00FFFF+#000000+#FF00FF+#00FFFF+#000000 3.

### Duration

Median 10.00 s. 2–4 s 40% · 4–8 s 9% · 8–16 s 34% · ≥16 s 17%.
In beats (35 placements with a beat track): 8 beats 23% · 15 beats 14% · 13 beats 11% · 7 beats 9% · 5 beats 9% · 32 beats 6% · 31 beats 6% · 78 beats 6%.

### Stacking

**91% of placements share the model with at least one concurrent effect (5 seq / 4 songs); 43% with three or more (4 seq / 3 songs).**

Partner types (pairs · sequences): Faces 16 · 1 · Pinwheel 14 · 2 · Wave 10 · 1 · Bars 10 · 2 · Shape 10 · 1 · SingleStrand 6 · 1 · Warp 5 · 1 · Curtain 5 · 1 · Spirals 4 · 1 · Ripple 4 · 1 · Video 1 · 1 · Off 1 · 1.

Above Kaleidoscope (partner type, the partner's blend): Faces 16 Normal · Ripple 4 Layered · Video 1 Normal · Off 1 Normal.

Beneath Kaleidoscope (partner type, Kaleidoscope's own blend over it): Pinwheel 14 Normal · Wave 10 Normal · Shape 10 Normal · SingleStrand 6 Normal · Bars 6 Normal · Warp 5 Normal · Curtain 5 Normal · Bars 4 Brightness · Spirals 4 Brightness.

Recurring full stacks (top → bottom, `*` = the mined effect): *Kaleidoscope > SingleStrand (6) · *Kaleidoscope > Wave > Wave > Warp > Curtain (5) · *Kaleidoscope > Pinwheel (3) · Faces > Faces > *Kaleidoscope > Pinwheel (3) · *Kaleidoscope > Bars > Bars (3) · *Kaleidoscope (3) · *Kaleidoscope > Bars > Spirals (2) · Ripple > Ripple > *Kaleidoscope > Bars > Spirals (2) · *Kaleidoscope > Shape > Pinwheel (2) · Faces > Faces > *Kaleidoscope > Shape > Pinwheel (2) · *Kaleidoscope > Shape > Shape (1) · Faces > Faces > *Kaleidoscope > Shape > Shape (1) · Faces > Faces > Faces > Faces > *Kaleidoscope > Shape > Shape (1) · Video > Off > *Kaleidoscope > Pinwheel > Pinwheel > Pinwheel > Pinwheel (1).

---

## Craft

### Identity and role

Kaleidoscope renders nothing of its own. With the layer's **Canvas** box on
(`T_CHECKBOX_Canvas=1`, frozen into every catalog look) it samples the composite beneath it and
reflects the sample around the buffer. From the corpus: **Type** is the shape of the sample,
`Square` (60%, 4 seq / 4 songs) or `Triangle` (40%, 3 seq / 3 songs); **Size** is how big the
sample is (23–47 in most placements; 86–100 at the end of Shut Up and Dance); **Rotation** turns
the sample (0 in 4 seq / 3 songs; 106 in Greg Colburn's 13 placements; 28 and 359 once each);
**X / Y** is the sample's centre (50 / 50; Y 0 in three placements). Not from the corpus,
xLights' documented behaviour: a smaller Size tiles more copies, so 23–32 is a fine mandala and
100 is one fold, close to a Warp mirror; Triangle gives six-fold symmetry, Square four-fold;
Rotation turns the symmetry axes, and a Rotation curve spins the whole mandala.

Role: **overlay**, on top of the design layers and, in Greg Colburn's file, beneath the singing
Faces. Its own palette is saved but mostly meaningless (0 colours in 9%); the colours come from
beneath. 91% of placements share the model, 43% with three or more layers. Five of 22 sequences
on four songs, 35 placements: thin, so the anchors are two sequencers' habits (Kid on Christmas
Greg Colburn 13, Shut Up and Dance Tammy Ghee 12) plus Light of Christmas (main) 5 and XATW
sharer A 4.

### Thematic fit

A mandala says *ornament*, *snowflake*, *stained glass*, *hypnosis*, *a spell*. It makes a
plain Pinwheel or a pair of Bars look designed, which is what a chorus on a matrix needs.
Christmas: Triangle over a Pinwheel in blue → purple → red gradients is a rose window; Square
Size 47 over Waves is a soft ornament. Halloween: a Square mandala over orange-and-black Bars is
a spider's web; Triangle Size 25 over Spirals or a Fire layer (Fire not from the corpus) is a
burning rune; a Rotation curve turns it like a spell being cast. It belongs on the hero matrix
(94%), never the video panel, and it has nothing to tile on a line prop.

### Anchors (starting points, not a menu)

| Anchor | Settings | Catalog look | Where | Dials to move |
|---|---|---|---|---|
| **Mandala** | Square or Triangle, Rotation 106, Size 32, X / Y 50, Canvas on, no fades, over a Pinwheel, 14–78 beats | `Kaleidoscope#0` (Type Square / Triangle and Blur 3–5 as knobs; n=11) · `#1` (fades 0.75 / 4.00 frozen) | XATW Kid on Christmas Greg Colburn, Matrix1, four sections | Square ↔ Triangle at the section change; Blur 5 for softer glass |
| **Soft tile** | Square, Rotation 0, Size 47, fades 0.25 / 0.25, 8 beats, over Wave ×2 + Warp + Curtain | `Kaleidoscope#6` (frozen) | Light of Christmas verse 1, MegaTree Singing Faces and the matrix (5) | |
| **Brightness mandala** | Triangle, Rotation 0, Size 25, `Brightness` blend | `Kaleidoscope#5` (frozen) | Light Of Christmas XATW sharer A (4), one sequence | the mandala becomes a brightness envelope on the layers beneath instead of replacing them |
| **Spinning tile** | Square, Size 33, `E_VALUECURVE_Kaleidoscope_Rotation` Ramp Up/Down 0 → 359 → 0, over a SingleStrand; or Square Rotation 28 Size 23 with a buffer Rotation Ramp over Bars ×2 | `Kaleidoscope#8` · `#2` | Shut Up and Dance Tammy Ghee, Matrix1 (3 + 2) | |
| **One big fold** | Size 100, Rotation 0, Y 0 or 50, fade out 0.25 or 5 | `Kaleidoscope#7` (Type, Y 0–50 and the fade out as knobs; 2 seq / 2 songs) · `#4` (Triangle, Rotation 359, Size 86) | the last section of Shut Up and Dance | |

**Dials** — pick from the observed values, then move one:

| Dial | Sane range | Moving it | Corpus picks |
|---|---|---|---|
| Type | Square / Triangle | four-fold or six-fold symmetry | Square 60% (4 seq / 4 songs) · Triangle 40% (3 / 3) |
| Size | 23–100 | the sample: small = many tiles, 100 = one fold | 32 · 47 · 25 · 100 (2 / 2) · 23 · 86 · 33 |
| Rotation | 0–359 | turns the sample | 0 (4 / 3) · 106 · 28 · 359 · curved 9% |
| X / Y | 50 / 0–50 | the sample's centre | 50 / 50 (91%) · 50 / 0 |
| Canvas | on | REQUIRED: tiles the layers below | 100% |
| Blend | Normal / Brightness | | Brightness 11% (one sequence) |
| Blur | 3–5 | softens the tiles | 5 (one sequence, 29%) · 3 |
| Fades | 0.25 · 0.75 / 4.00 · 5 | | 0.25 out (2 / 2) |

**How to permute.** Change what is beneath it first. Then Type at the section change (Greg
Colburn: Square in one section, Triangle in the next); Size down a step on the last chorus
(47 → 32 → 23 as the tiles multiply); a Rotation curve on the final chorus only.

### Layering recipes

| Name | Stack (top → bottom) | Blend | Use |
|---|---|---|---|
| **Mandala on the wheel** | (Faces · Faces ·) Kaleidoscope · Pinwheel | Normal | Greg Colburn: the singing face over a mandala over a pinwheel (3 + 3) |
| **Mandala on a shape** | Kaleidoscope · Shape · Pinwheel, or Kaleidoscope · Shape · Shape | Normal | the same with a Shape pulsing inside the tiles (2 + 2 + 1) |
| **Tile on the chase** | Kaleidoscope · SingleStrand | Normal | Tammy Ghee: a chase tiled into a lattice (6) |
| **Tile on the bars** | Kaleidoscope · Bars · Bars, or Kaleidoscope · Bars · Spirals | Normal; the Bars beneath also as `Brightness` (4) | the Shut Up and Dance green / red section (3 + 2) |
| **Tile on a warped wash** | Kaleidoscope · Wave · Wave · Warp · Curtain | Normal | Light of Christmas verse 1 (5): the kaleidoscope over the mirror |
| **Rings over the tile** | Ripple · Ripple · Kaleidoscope · Bars · Spirals | Ripple: `Layered` | a beat ring on top of the mandala (2) |

### Value curves

| Want | Curve | Dial |
|---|---|---|
| the mandala turning and coming back | E_VALUECURVE_Kaleidoscope_Rotation Ramp Up/Down 0 → 359 → 0 | Rotation (`#8`, one sequence) |
| the whole buffer turning | B_VALUECURVE_Rotation Ramp 0 → 100 | buffer rotation (`#2`, one sequence) |

```
E_VALUECURVE_Kaleidoscope_Rotation: Active=TRUE|Id=ID_VALUECURVE_Kaleidoscope_Rotation|Type=Ramp Up/Down|Min=0.00|Max=359.00|P2=359.00|RV=TRUE|
B_VALUECURVE_Rotation: Active=TRUE|Id=ID_VALUECURVE_Rotation|Type=Ramp|Min=0.00|Max=100.00|P2=100.00|RV=TRUE|
```

Neither needs a timing track; a `TT=Beats` curve works only after `xlo finalize` has patched the
Beats track.

### Prop fit and render style

Matrix 94% (5 seq / 4 songs), mega tree 6% (one sequence). It needs a 2D buffer; on a line or a
group of small props it tiles nothing you can see. The default buffer in every placement. On the
Halloween layout: the hero matrix (the seed matrices behind `SEM_FOCAL`), never the video panel.
One Kaleidoscope per model; it is a render-cost overlay.

### Timing

Median 10 s: 8 beats 23%, 15 beats 14%, 13 beats 11%; Greg Colburn holds one for 78 beats. It is
held for a section and re-cut at the section, never per beat. Fades 0 or 0.25; a long fade out
(4–5 s) when the section ends on it.

### Exemplars

| Where | Stack top → bottom | Why it works |
|---|---|---|
| **Light of Christmas.xsq** 0:21–0:25, verse 1, MegaTree Singing Faces | Kaleidoscope Square, Rotation 0, Size 47, fades 0.25, blue · Wave · Wave · Warp · Curtain | eight beats of a soft blue ornament: the tree's wave wash tiled and mirrored at once |
| **XATW Kid on Christmas Greg Colburn.xsq** 0:29–0:51 then 0:51–1:11, Matrix1 | Kaleidoscope Square, Rotation 106, Size 32 · Pinwheel; then Kaleidoscope Triangle (same dials) · Shape · Pinwheel; gradient palettes blue → purple → red | the pinwheel's stripes become a four-fold mandala, then a six-fold one with a shape pulsing inside; the only thing that changes at the section is the Type |
| XATW Kid on Christmas Greg Colburn.xsq 2:16–3:16, Matrix1 | Kaleidoscope Square, Rotation 106, Size 32 · Shape · Shape | 78 beats of one mandala with two shapes beneath it: the shapes do the moving |
| **XATW Shut Up and Dance Tammy Ghee.xsq** 1:03–1:10, GREEN/RED, Matrix1 | Kaleidoscope Square, Rotation 28, Size 23, buffer Rotation Ramp, purple + green + black · Bars · Bars | two bars layers become a turning fine lattice for 15 beats |
| XATW Shut Up and Dance Tammy Ghee.xsq 2:56–3:07, Matrix1 | Kaleidoscope Square Size 33 with the Rotation curve · SingleStrand; then Triangle, Rotation 359, Size 86, alone; then Triangle Size 100, Y 0, fade out 0.25 · SingleStrand | the outro: the tile grows 33 → 86 → 100 as the song closes, from mandala to one fold |

### Anti-patterns

- **Canvas off, or nothing beneath.** An empty layer; three corpus placements are alone and show
  nothing.
- **Below the design.** It must sit above the Pinwheel / Bars it tiles; above it belong only
  Faces, a beat Ripple or Video.
- **Size 100 as the default.** That is a mirror; the mandala lives at 23–47.
- **Re-cut per beat.** Held for a section in every placement.
- **Our own use: never.** Rob named it as the effect that goes on other effects; zero placements
  in our shows.

### What code can realize today

- `look_id` + `knobs`: `Kaleidoscope#0` (`E_CHOICE_Kaleidoscope_Type` Square / Triangle,
  `B_SLIDER_Blur` 3–5; Rotation 106 and Size 32 frozen), `#6` (the Size 47 soft tile), `#5`
  (Triangle Size 25 with `Brightness` frozen), `#7` (Size 100; Type, `E_SLIDER_Kaleidoscope_Y`
  0–50 and the fade out as knobs), `#4` (Triangle 86), `#8` (the Rotation curve frozen), `#2`
  (the buffer rotation frozen). Every look freezes `T_CHECKBOX_Canvas=1`. A Size or Rotation
  outside the frozen values goes in `settings` as `E_SLIDER_Kaleidoscope_Size` / `_Rotation`.
- `effect_meta` knows only an energy band (3–4): no speed, direction or duration class, and
  nothing places it as an overlay. Write it as the top `stack` layer with `role: "overlay"` and
  `look_id: "Kaleidoscope#0"` over the Pinwheel / Bars / Spirals layers of the same stack; the
  layer clamp counts it as one of four.
- The miner records `E_TEXTCTRL1` (the panel's help text, which still says "warp" in older
  builds) as a dial, and `#7` carries it as a knob; ignore it.
