# Fill

A line prop filling from one end on a `Fill_Position` curve — 100% curved, 2–4 beat cells on stars, arches, the roofline and icicles, alternating ends or converging from both under a Spirals `Brightness`; four sequencers only.

---

## Corpus facts

> Generated 2026-11-03 from the deduped corpus: **22 community sequences, 14 distinct songs** (xLights 2020.45–2025.08; 0 byte-identical files dropped). 4 sequences / 4 songs use Fill: **295 placements, 192 overlapping pairs.** Every share carries its breadth (sequences / songs); a habit in one sequence is one sequencer's habit, however many placements it has.
>
> Sources by placements: Light Of Christmas (XATW sharer A) 136 · Shut Up and Dance (Tammy Ghee) 84 · Danger Zone (XATW) 53 · Save Your Tears (AG) 22.

### Where it is placed

| Prop class | Share | Breadth | Example model names |
|---|---|---|---|
| star | 29% | 2 seq / 2 songs | Star1, Star2, Star 1 |
| roofline | 22% | 2 seq / 2 songs | Outlines, House Outline |
| arch | 21% | 2 seq / 2 songs | Arches, Arch Fans |
| icicle | 9% | 2 seq / 2 songs | Icicles, Icicles All |
| other | 6% | 1 seq / 1 song | Props A, Props B, Frozen Brillance |
| stake | 5% | 1 seq / 1 song | Pixel Stakes |
| megatree | 2% | 1 seq / 1 song | MegaTree 1, MegaTree Singing Faces |
| spinner | 2% | 1 seq / 1 song | Spinners, Spinner |
| snowflake | 1% | 1 seq / 1 song | 6pt Flake L, 6pt Flake R |
| cane | 1% | 1 seq / 1 song | Candy Canes |
| tree | 1% | 1 seq / 1 song | Mini Trees |

### Dials observed

Share · breadth per value; `curved` = that key has an active value curve instead of a static value.

| Key | Values |
|---|---|
| `Color_Time` (checkbox) | 0: 100% · 4 seq / 4 songs |
| `Offset_In_Pixels` (checkbox) | 1: 100% · 4 seq / 4 songs |
| `Wrap` (checkbox) | 1: 100% · 4 seq / 4 songs |
| `Direction` (choice) | Up: 75% · 3 seq / 3 songs — Left: 15% · 3 seq / 3 songs — Right: 11% · 3 seq / 3 songs — Down: 0% · 1 seq / 1 song |
| `Band_Size` (slider) | 0: 100% · 4 seq / 4 songs |
| `Offset` (slider) | 0: 100% · 4 seq / 4 songs |
| `Skip_Size` (slider) | 0: 100% · 4 seq / 4 songs |
| `B_CHOICE_BufferStyle` | Default: 45% · 1 seq / 1 song — <absent>: 19% · 2 seq / 2 songs — Per Model Single Line: 11% · 1 seq / 1 song — Per Preview: 8% · 1 seq / 1 song — Per Model Per Preview: 7% · 1 seq / 1 song — Single Line: 6% · 1 seq / 1 song — Per Model Default: 1% · 1 seq / 1 song — Per Model Vertical Per Strand: 1% · 1 seq / 1 song |
| `B_CHOICE_BufferTransform` | <absent>: 53% · 4 seq / 4 songs — None: 27% · 1 seq / 1 song — Rotate CC 90: 17% · 2 seq / 2 songs — Rotate CW 90: 3% · 1 seq / 1 song |
| `T_TEXTCTRL_Fadein` | <absent>: 100% · 4 seq / 4 songs — 0.50: 0% · 1 seq / 1 song |
| `T_TEXTCTRL_Fadeout` | <absent>: 56% · 4 seq / 4 songs — 0.10: 33% · 1 seq / 1 song — .25: 5% · 1 seq / 1 song — 0.25: 4% · 1 seq / 1 song — 0.20: 1% · 1 seq / 1 song — 1: 1% · 1 seq / 1 song — 0.50: 0% · 1 seq / 1 song — range 0.1…1 |
| `B_SLIDER_Blur` | <absent>: 74% · 3 seq / 3 songs — 4: 18% · 1 seq / 1 song — 5: 8% · 1 seq / 1 song — range 4…5 |

### Value curves

| Parameter | Share · breadth | Shapes |
|---|---|---|
| any curve | 100% · 4 seq / 4 songs | |
| `E_VALUECURVE_Fill_Position` | 100% · 4 seq / 4 songs | Custom 112 · Ramp Up/Down 92 · Ramp 91 |

Most-used exact strings (copy verbatim; `Min`/`Max` are the parameter range, `P*` the real values):

```
E_VALUECURVE_Fill_Position (112, 1 seq / 1 song): Active=TRUE|Id=ID_VALUECURVE_Fill_Position|Type=Custom|Min=0.00|Max=100.00|RV=TRUE|Values=0.00:0.00;0.75:1.00;1.00:1.00|
E_VALUECURVE_Fill_Position (89, 3 seq / 3 songs): Active=TRUE|Id=ID_VALUECURVE_Fill_Position|Type=Ramp|Min=0.00|Max=100.00|P2=100.00|RV=TRUE|
E_VALUECURVE_Fill_Position (68, 2 seq / 2 songs): Active=TRUE|Id=ID_VALUECURVE_Fill_Position|Type=Ramp Up/Down|Min=0.00|Max=100.00|P2=100.00|RV=TRUE|
E_VALUECURVE_Fill_Position (24, 1 seq / 1 song): Active=TRUE|Id=ID_VALUECURVE_Fill_Position|Type=Ramp Up/Down|Min=0.00|Max=100.00|P2=40.00|RV=TRUE|
```

### Palette habits

Colors per placement: 1: 43% · 2: 25% · 3: 32%.
Black as a color: 17% · 1 seq / 1 song. Sparkles on: 25% · 2 seq / 2 songs.
Top palettes: #E903C0 40 · #00FFFF+#FFFF00+#000000 33 · #008000+#00AA00+#00FF00 30 · (gradient) 22 · #FFFFFF 16 · #FF0000 16 · #07DA61 16 · #1B47FA 16.

### Duration

Median 1.05 s. <1 s 46% · 1–2 s 43% · 2–4 s 10% · 4–8 s 1%.
In beats (295 placements with a beat track): 2 beats 46% · 4 beats 22% · 3 beats 15% · 1 beats 6% · 0 beats 6% · 5 beats 3% · 9 beats 1% · 6 beats 0%.

### Stacking

**42% of placements share the model with at least one concurrent effect (3 seq / 3 songs); 10% with three or more (2 seq / 2 songs).**

Partner types (pairs · sequences): Spirals 96 · 2 · VU Meter 40 · 1 · Fill 28 · 1 · Shockwave 20 · 1 · SingleStrand 5 · 1 · Twinkle 2 · 1 · Bars 1 · 1.

Above Fill (partner type, the partner's blend): Spirals 78 Brightness · VU Meter 40 1 is True Unmask · Fill 14 Normal.

Beneath Fill (partner type, Fill's own blend over it): Shockwave 20 Normal · Spirals 18 Normal · Fill 14 Normal · SingleStrand 5 Normal · Twinkle 2 Normal · Bars 1 Normal.

Recurring full stacks (top → bottom, `*` = the mined effect): *Fill (170) · VU Meter > *Fill (40) · Spirals > *Fill (32) · *Fill > Shockwave (15) · Spirals > *Fill > Spirals > Fill (14) · Spirals > Fill > Spirals > *Fill (14) · Spirals > *Fill > Spirals (4) · *Fill > Shockwave > SingleStrand (3) · *Fill > SingleStrand > Bars (1) · *Fill > Shockwave > SingleStrand > Twinkle (1) · *Fill > Shockwave > Twinkle (1).

Same-type twins (14 top-over-bottom pairs): identical effect settings 0%; buffer transform differs 0%.

---

## Craft

### Identity and role

Fill lights a line prop from one end up to **Position** (0–100% of the buffer) and nothing
else: no bands (Band Size 0 and Skip Size 0 in 100% of placements), no offset (Offset 0,
`Offset_In_Pixels` on, Wrap on, Color Time off in 100%). The whole effect is the **Position
value curve**: every one of the 295 placements (4 seq / 4 songs) curves it, none holds it
static. So a Fill *is* the shape of that curve — a rise, a rise-and-hold, or a fill-and-drain
— travelling in **Direction** (Up 75%, 3 seq / 3 songs; Left 15% and Right 11%, 3 / 3 each;
Down once, 1 seq) over 2–4 beats. With Color Time off the palette spreads along the fill
(the first color at the start edge, the last at the fill's front), so three shades of one hue
(the Danger Zone greens) read as a gradient rising up the prop.

Four sequencers use it, which is thin breadth: 136 of the placements are one Light Of
Christmas file (XATW sharer A), 84 Shut Up and Dance, 53 Danger Zone, 22 Save Your Tears.
Where they agree: Fill is a **carrier** (2 beats 46%, 4 beats 22%, 3 beats 15%; re-cut in runs
of 5–6 identical cells) on stars, the roofline, arches and icicles, and 58% of the time it is
alone. The other 42%: a Spirals `Brightness` above it (78 pairs, 2 seq / 2 songs) textures the
fill, a VU Meter `1 is True Unmask` above it (40, 1 seq) gates it to the beat, a second Fill
from the other end runs toward it (14 + 14 pairs, 1 seq). It never carries a blend of its own
(0 placements with a LayerMethod) and is never a bed (4–8 s is 1%).

### Thematic fit

Fill says *rising*, *filling up*, *arriving*: a level climbing a star on the backbeat, a wave of
green running up the roofline, the icicles filling from both ends until they meet. Rise-and-hold
on the hit, fill-and-drain for a breath, a 40% rise that falls back for a tease. Halloween: an
orange fill rising from the ground on the stakes (the stakes are 5% of placements, 1 seq);
purple with a black third color so the front of the fill goes dark before it drains; the
outline filling in three oranges then switching to three purples the way Danger Zone switches
greens to reds. One color 43%, three 32%, two 25%; black as a color 17% (1 seq); sparkles on
25% (2 seq / 2 songs) — the LoC white fills sparkle.

### Anchors (starting points, not a menu)

| Anchor | Settings | Catalog look | Where | Dials to move |
|---|---|---|---|---|
| **Rise and hold** | Up, Position Custom (0 → 100 over the first 75% of the cell, then held), `Default` buffer, fade-out 0.10, 2 beats, one color | `Fill#2` (110; the Custom curve, Up and Default frozen; knobs transform {None|Rotate 180|Rotate CC 90|Rotate CW 90}, fade-out {.25|0.10}) | LoC XATW sharer A stars, arches, roofline (1 seq / 1 song) | the transform (which end the fill starts from); fade-out .25 under a Spirals |
| **Alternating ends** | the rise-and-hold with `Rotate CC 90` on one 2-beat cell and `Rotate CW 90` on the next, fade-out .25, white, under a Spirals `Brightness` | `Fill#2` with the transform knob | LoC XATW arches, verse 2 1:34–1:50 | the second color per cell (Bridge 2: white + red / green / magenta / blue) |
| **Fill and drain** | Up, Position Ramp Up/Down 0 → 100 → 0, 4 beats, three shades of one hue, alone | `Fill#3` (87; knobs buffer {Layer Star|Per Model Default|Per Model Per Preview|Per Model Single Line|Per Preview|Single Line}, Direction {Left|Right|Up}, curve {Ramp Up/Down|Ramp}) or `Fill#8` (Blur 4 frozen; Direction incl. Down) | Danger Zone outlines: runs of 5–6 cells, greens then reds (1 seq / 1 song) | rotate the direction per cell (Left, Right, Up, Down at 2:38); the shade triplet |
| **Converging pair** | Fill Right on one layer, Fill Left on the layer above starting half a cell later, `Per Model Single Line`, 2–3 beats, three colors ending in black, both under Spirals `Brightness` | `Fill#4` (Ramp frozen; knobs buffer {Per Model Per Preview|Per Model Single Line|Single Line}, Direction {Left|Right}, fade-out {0.25|1}) | SUAD icicles 0:00–0:03 and 2:19–2:26 (1 seq / 1 song) | the stagger; the end color |
| **Partial rise** | Up, Position Ramp Up/Down to 40 (P2=40): climbs 40% and falls back | `Fill#1` (Up frozen; knobs buffer {Default|Per Model Vertical Per Strand}, transform, curve {Ramp Up/Down P2=40|Ramp P2=100}) | 24 placements, 1 seq / 1 song | P2 40 → 100 as the section builds; Per Model Vertical Per Strand + Rotate CC 90 on a tree (3, 1 seq) |
| **Beat-gated** | any rise beneath a VU Meter `1 is True Unmask` | any look; the VU Meter is the layer above (see VU Meter.md) | 40 pairs, 1 seq / 1 song | the meter's timing track |
| **Soft fill** | Blur 5 with the Custom curve and fade-out 0.10 | `Fill#0` (29, all frozen; knob transform) · `Fill#8` (Blur 4) | 26% of placements carry a Blur (1 seq / 1 song each) | Blur 4 → 5 |

**Dials** — pick from the observed values, then move one:

| Dial | Sane range | Moving it | Corpus picks |
|---|---|---|---|
| Position (curve) | the four strings below | the whole gesture: rise, rise-and-hold, fill-and-drain, partial | Custom (112, 1 seq) · Ramp 0 → 100 (89, 3 seq / 3 songs) · Ramp Up/Down (68, 2 / 2) · Ramp Up/Down to 40 (24, 1 seq) |
| Direction | Up / Left / Right (Down) | the start edge on the buffer; on a line prop Left/Right is the string's own order | Up 75% · Left 15% · Right 11% · Down 0% |
| Transform | None / Rotate CC 90 / Rotate CW 90 / Rotate 180 | with Up: the end the fill starts from (CC 90 one end, CW 90 the other) | absent 53% · None 27% · Rotate CC 90 17% (2 seq / 2 songs) · CW 90 3% |
| Buffer | Default / Per Model Single Line / Single Line / Per Preview / Per Model Per Preview | Default on a single prop; Single Line variants so the fill runs along the string; Per Model Per Preview so every prop in a group fills in yard orientation | Default 45% · PMSL 11% · Per Preview 8% · PMPP 7% · Single Line 6% (1 seq each) |
| Band Size / Skip Size / Offset | 0 | bands turn the fill into a striped chase (not from the corpus) | 0 in 100% |
| Blur | 0 / 4 / 5 | softens the fill's front | absent 74% · 4 (18%) · 5 (8%), 1 seq each |
| Fade out | 0 / 0.10 / .25 | the held fill does not click off | 0.10 33% (1 seq) · .25 / 0.25 9% · 0.20 · 1 |
| Fade in | 0 / 0.50 | on the first cell of a run only | 0.50 (1 seq) |
| Blend | Normal | never set; the layer above carries it | absent 100% |
| Colors | 1–3 | one for the plain rise; three shades of a hue for the gradient; white + an answering color per cell | 1: 43% · 3: 32% · 2: 25% |

**How to permute.** Keep the curve for a section and change the end: CC 90 on one cell, CW 90
on the next (LoC arches); Left, Right, Up, Down on consecutive cells (Danger Zone outline at
2:38). Change the curve between sections: rise-and-hold in the verse, fill-and-drain in the
chorus, the 40% tease in the build. Change the shade triplet every 5–6 cells, not every cell.
Put a Spirals `Brightness` over it in the chorus so the same fill arrives textured.

### Layering recipes

| Name | Stack (top → bottom) | Blend | Use |
|---|---|---|---|
| **Plain carrier** | Fill, 2–4 beats, re-cut | Normal | 58% of the corpus: the star / arch / outline rise, alone |
| **Textured fill** | Spirals · Fill | Spirals: `Brightness` | the spirals become the brightness envelope of the fill (78 pairs, 2 seq / 2 songs): the fill rises with stripes in it |
| **Converging twin** | Spirals `Brightness` · Fill Left (starts half a cell late) · Spirals `Brightness` · Fill Right | Fills: Normal | SUAD icicles (14 + 14, 1 seq): two fills meet in the middle |
| **Beat-gated fill** | VU Meter · Fill | VU Meter: `1 is True Unmask` | the fill shows only on the meter's timing events (40, 1 seq) |
| **Fill over the ring** | Fill · Shockwave | Normal | the fill rises through a decaying ring (20 pairs, 1 seq); `Fill > Shockwave > SingleStrand` 3 |

### Value curves

| Want | Curve | Dial |
|---|---|---|
| a hit that arrives in three-quarters of the cell and holds | Custom 0 → 1 at 0.75, hold (112, 1 seq / 1 song) | Position |
| a plain rise across the cell | Ramp 0 → 100 (89, 3 seq / 3 songs — the breadth pick) | Position |
| fill then drain | Ramp Up/Down 0 → 100 → 0 (68, 2 seq / 2 songs) | Position |
| a 40% tease | Ramp Up/Down to 40 (24, 1 seq / 1 song) | Position |

```
E_VALUECURVE_Fill_Position: Active=TRUE|Id=ID_VALUECURVE_Fill_Position|Type=Custom|Min=0.00|Max=100.00|RV=TRUE|Values=0.00:0.00;0.75:1.00;1.00:1.00|
E_VALUECURVE_Fill_Position: Active=TRUE|Id=ID_VALUECURVE_Fill_Position|Type=Ramp|Min=0.00|Max=100.00|P2=100.00|RV=TRUE|
E_VALUECURVE_Fill_Position: Active=TRUE|Id=ID_VALUECURVE_Fill_Position|Type=Ramp Up/Down|Min=0.00|Max=100.00|P2=100.00|RV=TRUE|
E_VALUECURVE_Fill_Position: Active=TRUE|Id=ID_VALUECURVE_Fill_Position|Type=Ramp Up/Down|Min=0.00|Max=100.00|P2=40.00|RV=TRUE|
```

No timing-track curve in the corpus. A `TT=Beats` Timing Track Fade on Position (a fill that
pumps on every beat) would only work after `xlo finalize` patches the Beats track in; `xlo
apply` has no tracks.

### Prop fit and render style

Stars 29% (2 seq / 2 songs), roofline 22% (2 / 2), arches 21% (2 / 2), icicles 9% (2 / 2),
stakes 5% (1 seq), mega tree 2% (1 seq). A line effect: `Default` on a star or arch with a
transform choosing the end; `Per Model Single Line` / `Single Line` on icicles and the outline
so the fill follows the string; `Per Model Per Preview` on a group so each prop fills upward
in the yard; `Per Model Vertical Per Strand` + `Rotate CC 90` on a tree (3 placements, 1 seq).
On our layout: `SEM_STAKE` groups per model (Up — orange from the ground), the house outline
(Left / Right along the string), arches if the layout has them. Not the hero matrix: a Fill
on a matrix is a flat wipe, which is Morph's or Curtain's job, and the corpus puts 2% of
Fills on a tree-class prop.

### Timing

2 beats 46%, 4 beats 22%, 3 beats 15%, 1 beat 6%; median 1.05 s. Cells abut and repeat 5–6
times before the color changes (Danger Zone: ×5 greens at 4 beats, ×3 reds at 6 beats).
Fade-out 0.10–.25 so the held fill does not click off (1 seq each); fade-in 0.50 on the first
cell of a run only (Danger Zone 3:20). The converging twin starts its second layer about 0.7 s
after the first (0.75 s at 0:00, 0.67 s at 2:19).

### Exemplars

| Where | Stack top → bottom | Why it works |
|---|---|---|
| **Light Of Christmas XATW.xsq** (sharer A) 1:34–1:50 (94.90–110.38), Verse 2, Arches | Spirals `Brightness` · Fill Up, Custom rise-and-hold, `Default`, `Rotate CC 90` on one 2-beat cell then `Rotate CW 90` on the next, fade-out .25, white, re-cut every 2 beats for 16 beats | a white fill arrives from the left end of the arch, then the right, every two beats, textured by the spirals above it: one effect, one color, and the ends alternating is all the variety it needs |
| Light Of Christmas XATW.xsq 2:21–2:26 (141.38–146.22), Bridge 2, Arches | Fill Up, Custom, `Rotate CC 90`, fade-out 0.10, 2 beats: white + red, white + #07DA61, white + #E903C0, white + #1B47FA, white + red, alone | the same rise with the second color answering per cell; the gradient puts white at the start edge and the answer at the front |
| **XATW Shut Up and Dance Tammy Ghee.xsq** 0:00–0:03 (0.15–3.48) and 2:19–2:26 (138.95–145.78), Icicles | Spirals `Brightness` · Fill Left, `Per Model Single Line`, 2–3 beats, starting about 0.7 s late · Spirals `Brightness` · Fill Right, 3 beats; purple + blue + black, then cyan + yellow + black; fade-out 0.25 on the last cells | two fills run toward each other along every icicle, staggered so they never start together, ending in black so the front goes dark before the drain |
| **Danger Zone XATW.xsq** 0:29–0:43 (29.50–43.25) and 2:38–2:55 (158.10–174.90), Outlines | Fill Up, 4-beat cells ×5 in three greens (#008000 #00AA00 #00FF00), then ×3 at 6 beats in three reds; later Left, Right, Up, Down, Left, Right in green + silver, then silver + green + red, then reds, then greens with fade-out 0.20 on the last; alone | the roofline fills in a green gradient on every bar for a phrase, then turns red; the late run rotates the start edge every bar — direction is the variety, the curve never changes |

### Anti-patterns

- **A static Fill.** 0% of the corpus. A Fill without a Position curve is a prop half-lit and
  motionless. Always name the curve (frozen in `Fill#2` / `#0`, a knob on `#3` / `#8` / `#1`).
- **A 4-bar Fill on the hero as a phrase gesture.** `PHRASE_ROTATION` places Fill from the
  section's 2nd bar for 4 bars on the hero group at `Per Preview`, adding only a speed setting (Fill
  has none) and no Position curve of its own. The corpus Fill is a 2–4 beat cell on a line prop
  (1 beat to 4 beats: 89%); on the hero it is one sequencer's 6 placements. Write it as a
  carrier layer with `cell_beats` 2–4 on the stakes or the outline instead.
- **Band Size or Skip Size above 0.** 100% zero in the corpus; bands are Marquee's job.
- **Fill Down.** 0% (one sequencer, a handful of cells in a direction rotation). Fills rise.
- **A blend on the Fill.** Never set in the corpus; put the Spirals `Brightness` or the VU
  Meter `1 is True Unmask` *above* it.
- **A new color every cell for a whole section.** The pros hold a shade triplet 5–6 cells;
  LoC's per-cell answer is a 5-cell bridge figure, not a verse.
- **The same end every cell.** Alternate the transform (CC / CW 90) or the direction.

### What code can realize today

- `look_id` + `knobs`: `Fill#2` (rise-and-hold frozen; knobs `B_CHOICE_BufferTransform`
  {None|Rotate 180|Rotate CC 90|Rotate CW 90}, `T_TEXTCTRL_Fadeout` {.25|0.10} — but
  `transform` and `fade_out` are layer fields; write `Fill#2` + fields), `Fill#3` (knobs
  `B_CHOICE_BufferStyle`, `E_CHOICE_Fill_Direction` {Left|Right|Up}, `E_VALUECURVE_Fill_Position`
  {Ramp Up/Down|Ramp} — the curve knob takes one of the two strings verbatim), `Fill#8` (Blur
  4 frozen; Direction incl. Down; three curve strings), `Fill#1` (Up frozen; the P2=40 tease),
  `Fill#4` (Ramp frozen; Left/Right; line buffers), `Fill#0` (Blur 5 + Custom + fade 0.10 all
  frozen). The catalog records a default per knob, so a `Fill#3` without the curve knob set
  still places with one of its observed curves; name it anyway.
- `settings`: the four `E_VALUECURVE_Fill_Position` strings when the look does not expose the
  curve (`Fill#2`'s is frozen), `B_SLIDER_Blur`, `C_SLIDER_SparkleFrequency`;
  `render_style` (Single Line / Per Model Single Line / Per Model Per Preview are
  `KNOWN_STYLES`; `Per Model Vertical Per Strand` is not and falls back), `transform`,
  `fade_in` / `fade_out`, `cell_beats` 2–4, `direction` ltr / rtl / up / down (`effect_meta`
  maps them onto `E_CHOICE_Fill_Direction` Right / Left / Up / Down); `direction: "alternate"`
  flips Right / Left on odd bars (not CC / CW 90 — the transform alternation has no field; two
  layers both at `cell_beats` 2 light together, so the LoC alternating ends need one layer per
  section and the end chosen per section).
- `effect_meta.py`: Fill has no speed, four directions, energy band 2–3, duration class
  `phrase`; `beats.py` rotates it with Morph and Curtain as the phrase gesture (above),
  `SIMPLE_COLOR` keeps it to 1–2 colors, `FEATURE_BASE_EFFECTS` lets it be a feature base;
  `generate.py` treats a ≥3 s Fill as an opaque wash and forces `Max` on features over it;
  `phrasing.py` puts it in the dissolve family; `value_curves.py` `MOTION_CURVES` knows
  ("Fill", "position") as a 0–100 sweep for a weave recipe naming `motion_curve`, not for the
  phrase gesture. The converging twin's 0.7 s stagger, the VU gate and the Spirals
  `Brightness` texture are stack layers, not synthesis.
