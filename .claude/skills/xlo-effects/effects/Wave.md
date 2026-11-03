# Wave

A travelling sine line: the pixel-field and matrix streamer, twinned Left to Right against Right to Left (or with opposite YOffset), and a `True Unmask` window that cuts a wave out of an On, a Shader or a VU Meter.

---

## Corpus facts

> Generated 2026-11-03 from the deduped corpus: **22 community sequences, 14 distinct songs** (xLights 2020.45–2025.08; 0 byte-identical files dropped). 15 sequences / 11 songs use Wave: **408 placements, 847 overlapping pairs.** Every share carries its breadth (sequences / songs); a habit in one sequence is one sequencer's habit, however many placements it has.
>
> Sources by placements: Kid On Christmas (Eliot Wisser) 94 · Uptown Funk (Updated 11.25) 55 · Shut Up and Dance (Bill Jenkins) 41 · Danger Zone (XATW) 40 · Believer (XATW R2.1) 36 · Baby Shark (John Storms) 34 · Sounding Joy (XATW R2.1) 29 · Light Of Christmas (main) 26 · the other 7 files 53 together.

### Where it is placed

| Prop class | Share | Breadth | Example model names |
|---|---|---|---|
| megatree | 29% | 6 seq / 6 songs | MegaTree Singing Faces, MegaTree1, MegaTree 1 |
| pixels | 26% | 4 seq / 4 songs | Pixel Field |
| matrix | 21% | 4 seq / 4 songs | Matrix1, Matrix2, P10 |
| group_all | 6% | 4 seq / 4 songs | *Entire Display no Floods, Entire House Face, Entire Display |
| spinner | 5% | 2 seq / 2 songs | Spinner, Spinners |
| stake | 4% | 3 seq / 2 songs | Pixel Stakes |
| tree | 3% | 3 seq / 3 songs | _TREELINE, Mini Trees |
| other | 3% | 2 seq / 2 songs | _DEER, Frozen Brillance |
| snowflake | 2% | 1 seq / 1 song | _SNOWFLAKES-WREATHS-PIXELS |
| arch | 1% | 1 seq / 1 song | Arch Fans |
| flood | 0% | 1 seq / 1 song | Flood Lights |
| roofline | 0% | 1 seq / 1 song | Bulb Outlines |

### Dials observed

Share · breadth per value; `curved` = that key has an active value curve instead of a static value.

| Key | Values |
|---|---|
| `Mirror_Wave` (checkbox) | 0: 78% · 15 seq / 11 songs — 1: 22% · 2 seq / 2 songs — range 0…1 |
| `Fill_Colors` (choice) | None: 74% · 13 seq / 10 songs — Palette: 26% · 7 seq / 5 songs |
| `Direction` (choice) | Right to Left: 70% · 15 seq / 11 songs — Left to Right: 30% · 10 seq / 9 songs |
| `Type` (choice) | Sine: 84% · 14 seq / 11 songs — Square: 9% · 2 seq / 2 songs — Triangle: 8% · 4 seq / 3 songs |
| `Number_Waves` (slider) | 900: 48% · 10 seq / 8 songs — 798: 9% · 1 seq / 1 song — 429: 8% · 1 seq / 1 song — 436: 7% · 1 seq / 1 song — 225: 5% · 1 seq / 1 song — 656: 4% · 1 seq / 1 song — 1800: 4% · 2 seq / 2 songs — 729: 2% · 1 seq / 1 song — range 180…2700 |
| `Thickness_Percentage` (slider) | **curved 10% · 1 seq / 1 song** — 5: 30% · 3 seq / 3 songs — 0: 9% · 1 seq / 1 song — 9: 7% · 1 seq / 1 song — 25: 5% · 4 seq / 4 songs — 15: 5% · 4 seq / 3 songs — 4: 4% · 1 seq / 1 song — 42: 4% · 3 seq / 2 songs — 50: 3% · 2 seq / 2 songs — range 0…60 |
| `Height` (slider) | **curved 10% · 1 seq / 1 song** — 50: 28% · 7 seq / 6 songs — 100: 19% · 3 seq / 3 songs — 19: 9% · 1 seq / 1 song — 64: 8% · 1 seq / 1 song — 10: 5% · 1 seq / 1 song — 56: 4% · 1 seq / 1 song — 81: 3% · 3 seq / 3 songs — 75: 2% · 1 seq / 1 song — range 7…100 |
| `YOffset` (slider) | **curved 1% · 1 seq / 1 song** — 0: 88% · 13 seq / 11 songs — -124: 0% · 1 seq / 1 song — -5: 0% · 1 seq / 1 song — 127: 0% · 1 seq / 1 song — -78: 0% · 2 seq / 2 songs — -89: 0% · 1 seq / 1 song — -83: 0% · 1 seq / 1 song — 53: 0% · 1 seq / 1 song — range -124…127 |
| `Speed` (textctrl) | 10.00: 46% · 9 seq / 6 songs — 10: 15% · 5 seq / 4 songs — 20: 12% · 2 seq / 2 songs — 6.16: 7% · 1 seq / 1 song — 7.59: 4% · 1 seq / 1 song — 13.48: 4% · 1 seq / 1 song — 15: 3% · 2 seq / 2 songs — 8.82: 2% · 1 seq / 1 song — range 0…50 |
| `B_CHOICE_BufferStyle` | <absent>: 51% · 10 seq / 8 songs — Stacked X Horizontally: 9% · 2 seq / 2 songs — Overlaid X: 8% · 2 seq / 2 songs — Default: 8% · 1 seq / 1 song — Per Preview: 7% · 2 seq / 2 songs — Stacked Y Horizontally: 7% · 1 seq / 1 song — Per Model Default: 3% · 2 seq / 1 song — Per Model Per Preview: 3% · 3 seq / 2 songs |
| `B_CHOICE_BufferTransform` | <absent>: 88% · 15 seq / 11 songs — Flip Horizontal: 9% · 1 seq / 1 song — Rotate CC 90: 2% · 3 seq / 3 songs — Rotate CW 90: 0% · 1 seq / 1 song — Rotate 180: 0% · 1 seq / 1 song |
| `T_CHOICE_LayerMethod` | <absent>: 79% · 13 seq / 9 songs — 1 is True Unmask: 8% · 3 seq / 3 songs — 2 is True Unmask: 6% · 1 seq / 1 song — Max: 4% · 1 seq / 1 song — Normal: 2% · 1 seq / 1 song — 1 reveals 2: 1% · 1 seq / 1 song — Effect 1: 1% · 1 seq / 1 song — Layered: 0% · 1 seq / 1 song |
| `T_TEXTCTRL_Fadein` | <absent>: 75% · 13 seq / 10 songs — 0.5: 5% · 1 seq / 1 song — 1: 5% · 5 seq / 4 songs — 0.25: 4% · 1 seq / 1 song — .75: 3% · 1 seq / 1 song — 0.30: 2% · 1 seq / 1 song — .5: 2% · 1 seq / 1 song — .5 : 2% · 1 seq / 1 song — range 0.2…1 |
| `T_TEXTCTRL_Fadeout` | <absent>: 73% · 14 seq / 11 songs — .5: 12% · 3 seq / 3 songs — 0.25: 4% · 1 seq / 1 song — .4: 3% · 1 seq / 1 song — 0.20: 2% · 2 seq / 2 songs — 0.50: 2% · 1 seq / 1 song — .75: 1% · 1 seq / 1 song — 1: 1% · 3 seq / 2 songs — range 0.2…2 |
| `T_CHOICE_In_Transition_Type` | <absent>: 98% · 15 seq / 11 songs — Wipe: 2% · 1 seq / 1 song |
| `T_CHOICE_Out_Transition_Type` | <absent>: 98% · 15 seq / 11 songs — Wipe: 2% · 1 seq / 1 song |
| `B_SLIDER_Blur` | <absent>: 84% · 15 seq / 11 songs — 15: 7% · 1 seq / 1 song — 2: 6% · 1 seq / 1 song — 5: 1% · 1 seq / 1 song — 8: 1% · 1 seq / 1 song — range 2…15 |

### Value curves

| Parameter | Share · breadth | Shapes |
|---|---|---|
| any curve | 19% · 5 seq / 4 songs | |
| `B_VALUECURVE_Rotation` | 8% · 3 seq / 3 songs | Ramp 27 · Sine 4 |
| `E_VALUECURVE_Thickness_Percentage` | 10% · 1 seq / 1 song | Saw Tooth 36 · Timing Track Fade Proportional 5 |
| `E_VALUECURVE_Wave_Height` | 10% · 1 seq / 1 song | Saw Tooth 36 · Timing Track Fade Fixed 5 |
| `E_VALUECURVE_Wave_YOffset` | 1% · 1 seq / 1 song | Ramp 4 |
| timing-track curves (`TT=`) | 1% · 1 seq / 1 song | Drums |

Most-used exact strings (copy verbatim; `Min`/`Max` are the parameter range, `P*` the real values):

```
B_VALUECURVE_Rotation (11, 1 seq / 1 song): Active=TRUE|Id=ID_VALUECURVE_Rotation|Type=Ramp|Min=0.00|Max=100.00|P2=100.00|RV=TRUE|
B_VALUECURVE_Rotation (6, 1 seq / 1 song): Active=TRUE|Id=ID_VALUECURVE_Rotation|Type=Ramp|Min=0.00|Max=100.00|P1=100.00|RV=TRUE|
B_VALUECURVE_Rotation (5, 1 seq / 1 song): Active=TRUE|Id=ID_VALUECURVE_Rotation|Type=Ramp|Min=0.00|Max=100.00|P2=50.00|RV=TRUE|
B_VALUECURVE_Rotation (5, 1 seq / 1 song): Active=TRUE|Id=ID_VALUECURVE_Rotation|Type=Ramp|Min=0.00|Max=100.00|P1=50.00|RV=TRUE|
E_VALUECURVE_Thickness_Percentage (17, 1 seq / 1 song): Active=TRUE|Id=ID_VALUECURVE_Thickness_Percentage|Type=Saw Tooth|Min=0.00|Max=100.00|P1=10.00|P2=50.00|P3=64.00|TO=75|RV=TRUE|
E_VALUECURVE_Thickness_Percentage (14, 1 seq / 1 song): Active=TRUE|Id=ID_VALUECURVE_Thickness_Percentage|Type=Saw Tooth|Min=0.00|Max=100.00|P1=10.00|P2=50.00|P3=32.00|TO=75|RV=TRUE|
E_VALUECURVE_Thickness_Percentage (5, 1 seq / 1 song): Active=TRUE|Id=ID_VALUECURVE_Thickness_Percentage|Type=Timing Track Fade Proportional|Min=0.00|Max=100.00|TT=Drums|P2=50.00|P3=50.00|TO=75|RV=TRUE|
E_VALUECURVE_Thickness_Percentage (3, 1 seq / 1 song): Active=TRUE|Id=ID_VALUECURVE_Thickness_Percentage|Type=Saw Tooth|Min=0.00|Max=100.00|P1=10.00|P2=35.00|P3=32.00|TO=75|RV=TRUE|
E_VALUECURVE_Wave_Height (17, 1 seq / 1 song): Active=TRUE|Id=ID_VALUECURVE_Wave_Height|Type=Saw Tooth|Min=0.00|Max=100.00|P2=75.00|P3=64.00|RV=TRUE|
E_VALUECURVE_Wave_Height (16, 1 seq / 1 song): Active=TRUE|Id=ID_VALUECURVE_Wave_Height|Type=Saw Tooth|Min=0.00|Max=100.00|P2=75.00|P3=32.00|RV=TRUE|
E_VALUECURVE_Wave_Height (5, 1 seq / 1 song): Active=TRUE|Id=ID_VALUECURVE_Wave_Height|Type=Timing Track Fade Fixed|Min=0.00|Max=100.00|TT=Drums|P2=100.00|P3=10.00|RV=TRUE|
E_VALUECURVE_Wave_Height (3, 1 seq / 1 song): Active=TRUE|Id=ID_VALUECURVE_Wave_Height|Type=Saw Tooth|Min=0.00|Max=100.00|P2=60.00|P3=32.00|RV=TRUE|
E_VALUECURVE_Wave_YOffset (2, 1 seq / 1 song): Active=TRUE|Id=ID_VALUECURVE_Wave_YOffset|Type=Ramp|Min=-250.00|Max=250.00|P1=150.00|P2=50.00|RV=TRUE|
E_VALUECURVE_Wave_YOffset (2, 1 seq / 1 song): Active=TRUE|Id=ID_VALUECURVE_Wave_YOffset|Type=Ramp|Min=-250.00|Max=250.00|P1=-150.00|P2=-50.00|RV=TRUE|
```

### Palette habits

Colors per placement: 1: 63% · 2: 12% · 3: 14% · 4: 0% · 5: 0% · 6: 0% · 7: 10%.
Black as a color: 19% · 5 seq / 5 songs. Sparkles on: 28% · 2 seq / 2 songs.
Top palettes: #FFFFFF 93 · #FF0000 62 · #FF80FF+#80FFFF+#8000FF 47 · #FF0000+#00FF00+#0000FF+#FFFF00+#000000+#00FFFF+#FF00FF 37 · #000000 26 · #FFFFFF+#FF0000 18 · #FFFF00 16 · (gradient) 15.

### Duration

Median 2.96 s. <1 s 6% · 1–2 s 17% · 2–4 s 47% · 4–8 s 21% · 8–16 s 8% · ≥16 s 1%.
In beats (408 placements with a beat track): 4 beats 30% · 8 beats 16% · 5 beats 11% · 3 beats 6% · 2 beats 5% · 6 beats 4% · 9 beats 4% · 16 beats 3%.

### Stacking

**87% of placements share the model with at least one concurrent effect (14 seq / 11 songs); 29% with three or more (7 seq / 6 songs).**

Partner types (pairs · sequences): Wave 319 · 7 · Off 106 · 4 · On 92 · 5 · Fan 54 · 1 · VU Meter 41 · 1 · Shader 37 · 2 · Spirals 35 · 4 · Warp 34 · 4 · Shockwave 27 · 3 · Pinwheel 24 · 1 · Butterfly 14 · 1 · Color Wash 14 · 1 · Kaleidoscope 10 · 1 · Curtain 10 · 1 · Faces 10 · 1 · Garlands 8 · 1 · Shape 4 · 2 · Plasma 2 · 1 · Twinkle 2 · 1 · Snowflakes 1 · 1.

Above Wave (partner type, the partner's blend): Wave 160 Normal · On 69 2 is Unmask · VU Meter 41 2 is True Unmask · Spirals 27 Normal · Pinwheel 24 Normal · Warp 20 Normal · Kaleidoscope 10 Normal · Faces 10 Normal · Garlands 8 Layered · Color Wash 8 Normal · Shockwave 5 Normal · Warp 4 1 reveals 2 · Shape 3 Normal · Wave 2 Layered · Plasma 2 2 reveals 1 · Twinkle 2 Normal · Morph 1 Normal.

Beneath Wave (partner type, Wave's own blend over it): Wave 155 Normal · Fan 54 Normal · Off 51 Normal · Off 31 1 is True Unmask · Shader 24 2 is True Unmask · Off 24 2 is True Unmask · Shockwave 17 Normal · On 16 1 is True Unmask · Butterfly 14 Normal · Shader 13 1 is True Unmask · Warp 10 Normal · Curtain 10 Normal · Spirals 8 Normal · On 7 Normal · Color Wash 6 Normal · Shockwave 4 2 is True Unmask · Wave 2 Layered · Snowflakes 1 Normal · Circles 1 Normal · Shape 1 Normal.

Recurring full stacks (top → bottom, `*` = the mined effect): *Wave (52) · On > *Wave > Off (45) · VU Meter > *Wave (31) · *Wave > Shader > Off (31) · On > *Wave (16) · *Wave > On > Off (16) · *Wave > Wave (14) · Wave > *Wave (14) · *Wave > Shockwave (12) · Faces > VU Meter > *Wave (10) · Warp > *Wave (6) · *Wave > Wave > Wave > Fan > Fan > Fan (6) · Wave > *Wave > Wave > Fan > Fan > Fan (6) · Wave > Wave > *Wave > Fan > Fan > Fan (6) · Spirals > Spirals > *Wave > Butterfly (6) · Spirals > *Wave > Butterfly (6).

Same-type twins (162 top-over-bottom pairs): identical effect settings 27%; buffer transform differs 9%; `YOffset` (slider) opposite sign 23%.

---

## Craft

### Identity and role

Wave draws one line of **Type** Sine (84%), Triangle (4 seq) or Square (2 seq) travelling
across the buffer (Fractal/Ivy and Decaying Sine exist in xLights and never appear here) in
**Direction** Right to Left (70%) or Left to Right (30%) at **Speed** (10 in 61% of placements).
**Number of Waves** is the wavelength count (900 in 48%; 429–656 longer waves, 1800–2700
tighter); **Height** the amplitude in % of the buffer (50 most, 100 full, 19 a ripple);
**Thickness** the line's weight in % (5 a line, 0 a hairline, 42–55 a band); **Fill Colors**
`None` draws the line (74%), `Palette` fills under it with the palette (26%, 7 seq / 5 songs);
**Mirror** reflects it about the horizontal centre (22%, 2 seq); **YOffset** moves it up or down
(0 in 88%, and the twin's opposite sign in 23% of same-type pairs).

Roles: **feature** on a pixel field, matrix or mega tree, held 4–8 beats and flipped in
direction every phrase; **twin** (160 same-type pairs: identical settings 27%, opposite YOffset
23%, transform 9%); **mask** with `1 is True Unmask` / `2 is True Unmask` so an On, a Shader
or an Off-based texture shows only inside the moving line (Wave's own blend in 15% of
placements, 3 seq / 3 songs); and the **masked layer** under a VU Meter `2 is True Unmask` (41
pairs) or an On `2 is Unmask` (69 pairs) that colours it. Not a carrier (4 beats 30%, 8 beats
16%, under a second 6%) and not a bed: a line is not a floor, and 87% of placements have
something else on the model.

### Thematic fit

Wave says *water, wind, signal, breath*: a sea line crossing a pixel field, an oscilloscope on
a matrix, a flag (Triangle with Mirror). It fits songs with a sway, a riff that scrolls (Uptown
Funk's red line through every chorus), lyrics about the sea, the air, radio, a heartbeat.
Mirror with a Palette fill is a lattice, not a line. Christmas: a white or #80FFFF sine on the
matrix. Halloween: a green hairline (a monitor trace), a purple Square band, a red line on the
stakes. One colour in 63% of placements; the four-colour rainbow lives under a VU Meter.
Sparkles on 28% (2 seq / 2 songs).

### Anchors (starting points, not a menu)

| Anchor | Settings | Catalog look | Where | Dials to move |
|---|---|---|---|---|
| **Streamer** | Sine, Number of Waves 900, Thickness 5, Height 50, Speed 13.48, Fill None, Right to Left, `Overlaid X`, red, 7–8 beats, flip the direction on the next phrase | `Wave#1` (Direction, Sine or Triangle, 300–900, Thickness 5–54, Height 14–100, YOffset −89…99, Speed 6.16–13.48, buffer incl. Overlaid X / Z) | Uptown Funk Pixel Field, every chorus, under an On `2 is Unmask`, over an Off | Number of Waves 526, Speed 11.24, `Overlaid Z` for the bridge's 4-beat cells |
| **Plain sine** | Sine 900, Speed 10.00, YOffset 0, `Default` buffer, one or four colours | `Wave#8` (900–1800, Direction; the Saw Tooth curves as knobs) | Shut Up and Dance (Bill Jenkins) Pixel Stakes under a VU Meter, 6–35 beats | 1800 for twice the waves |
| **Texture window** | Sine 900, Thickness 9, Height 100, Speed 10, `Stacked X Horizontally`, **`2 is True Unmask`** over a Shader; or 656 / 4 / 56 / Speed 7.59, `Overlaid X`, `1 is True Unmask` over an On | `Wave#44` (656–900, Thickness 4–9, Height 56–100, Speed 7.59–10, blend as a knob) | the XATW R2.1 files: *Wave > Shader > Off (31 stacks) | the texture beneath decides the look; the wave only decides where it shows |
| **Lattice twin** | Mirror, Fill Palette, Sine 798, Thickness 0, Height 19, Speed 20, `Flip Horizontal`, three colours; two to four layers alternating Right to Left / Left to Right, each on a SubBuffer half | `Wave#12` / `#27` (SubBuffer halves and Direction as knobs; `#9` / `#22` add a buffer Rotation Ramp) | Kid On Christmas (Eliot Wisser) Matrix2, 4-beat cells | fade in 0.75 on the first cell, out 0.5 on the last |
| **Fat triangle** | Mirror, Triangle, 900, Thickness 11, Height 77, Speed 10, Blur 8, `Flip Horizontal`, fades 0.75 / 0.5, Wipe out, one colour | `Wave#13` / `#29` (frozen) | Kid On Christmas Matrix2, 9 beats, between Spirals above and a Butterfly below | |
| **Square band** | Square, 900, Thickness 55, Height 75, Speed 15, Right to Left, fades 0.25 / 0.25, buffer Rotation Ramp 0 → 50 | `Wave#34` (frozen; the Rotation curve as a knob) | one sequence, 10 placements | Thickness 42, Height 50 (`#21`, with Rotate CW / CC 90) |
| **Mirrored thirds** | Mirror, Fill Palette, Square 900, Thickness 5, Height 50, Speed 10, three SubBuffer thirds | `Wave#11` (Flip Horizontal) / `#25` | one sequence, 18 placements | |
| **Max waves** | Sine 429, Thickness 5, Height 64, Speed 10, Right to Left, `Max`, four layers | `Wave#39` (429–1825, Thickness 5–28, Height 64–81; blend Effect 1 / Max / Normal as a knob) | the Danger Zone file: four Wave layers under the star (Shape file, 0:23–0:29) | |

**Dials** — pick from the observed values, then move one:

| Dial | Sane range | Moving it | Corpus picks |
|---|---|---|---|
| Type | Sine / Triangle / Square | the line's profile | Sine 84% · Square (2 seq) · Triangle (4 seq) |
| Fill Colors | None / Palette | a line, or the area under it filled | None 74% · Palette 26% |
| Direction | Right to Left / Left to Right | flip it every phrase | R→L 70% · L→R 30% |
| Mirror | off / on | reflected about the middle | off 78% · on (2 seq) |
| Number of Waves | 180–2700 | wavelength count: 900 standard, 429–656 long, 1800+ tight | 900 · 798 · 429 · 436 · 1800 |
| Height | 7–100 | amplitude | 50 · 100 · 19 · 64 · 81 |
| Thickness | 0–60 | 0 hairline, 5 line, 25 thick, 42–55 band | 5 · 0 · 9 · 25 · 15 · 42 · 50 |
| YOffset | −124…127 | vertical shift; opposite signs for the twin | 0 · −78 |
| Speed | 0–50 | travel rate | 10 · 20 · 13.48 · 6.16 · 15 |
| Buffer | Default / Overlaid X / Overlaid Z / Stacked X Horizontally / Stacked Y Horizontally / Per Model Per Preview | one wave across the group vs each prop its own | |
| Transform | Flip Horizontal / Rotate CC 90 | the twin; vertical waves on a tree | Flip Horizontal (1 seq) · Rotate CC 90 (3 seq) |
| Blend | Normal / 1 is True Unmask / 2 is True Unmask / Max | a line, or a window | |
| Blur | 2–15 | softens the line | 15 · 2 · 5 · 8 (1 seq each) |
| Fades | 0; 0.25 / 0.25 on the band; 0.75 in / 0.5 out on sheets | | out .5 12% (3 seq) · in 1 (5 seq) |

**How to permute.** Flip Direction at every phrase (Uptown Funk: 8 beats Right to Left, 7 beats
Left to Right, every chorus). Lengthen the waves for the bridge (900 → 526) and slow it (13.48 →
11.24). Give the twin the other direction and the opposite YOffset. Turn a line into a window by
adding `2 is True Unmask` and a texture beneath. Go from a Thickness 5 line to a Thickness 55
Square band for the peak. One colour per section.

### Layering recipes

| Name | Stack (top → bottom) | Blend | Use |
|---|---|---|---|
| **Coloured line on black** | On `2 is Unmask` · Wave · Off | as named | Uptown Funk Pixel Field (45 stacks): the On's colour only where the wave is; the Off kills everything else |
| **Meter window on a rainbow** | VU Meter `2 is True Unmask` · Wave (four colours) | as named | Shut Up and Dance BJ Pixel Stakes (31): the wave shows only where the meter is lit |
| **Texture through a wave** | Wave `2 is True Unmask` · Shader · Off | as named | the R2.1 files (31): the shader shows inside the moving line |
| **Twin lines** | Wave Left to Right (YOffset +) · Wave Right to Left (YOffset −) | Normal | 160 same-type pairs: a crossing pair |
| **Lattice** | Wave ×2–4 alternating direction, SubBuffer halves, Mirror, Palette fill | Normal | Kid On Christmas Matrix2 |
| **Wave over a hit** | Wave · Shockwave | Normal | 12 stacks: the line runs through the pop |
| **Fans under waves** | Wave ×3 · Fan ×3 | Normal | 6 stacks, one file |
| **Sheet between a twin and a bed** | Spirals · Wave Triangle Mirror · Butterfly | Normal | Kid On Christmas Matrix2 |

### Value curves

| Want | Curve | Dial |
|---|---|---|
| the line's weight pulsing | Thickness_Percentage Saw Tooth 10 → 50, 32 or 64 teeth | Thickness |
| the amplitude pumping | Wave_Height Saw Tooth 0 → 75, 32 or 64 teeth | Height |
| thickness and height jumping on drum hits | Thickness Timing Track Fade Proportional `TT=Drums`; Height Timing Track Fade Fixed `TT=Drums` 100 → 10 | both |
| the wave field turning | B_VALUECURVE_Rotation Ramp 0 → 100 (3 seq / 3 songs), or 0 → 50 | buffer rotation |
| the line sliding | Wave_YOffset Ramp 150 → 50, and −150 → −50 on the twin | YOffset |

```
E_VALUECURVE_Thickness_Percentage: Active=TRUE|Id=ID_VALUECURVE_Thickness_Percentage|Type=Saw Tooth|Min=0.00|Max=100.00|P1=10.00|P2=50.00|P3=64.00|TO=75|RV=TRUE|
E_VALUECURVE_Wave_Height: Active=TRUE|Id=ID_VALUECURVE_Wave_Height|Type=Saw Tooth|Min=0.00|Max=100.00|P2=75.00|P3=64.00|RV=TRUE|
E_VALUECURVE_Thickness_Percentage: Active=TRUE|Id=ID_VALUECURVE_Thickness_Percentage|Type=Timing Track Fade Proportional|Min=0.00|Max=100.00|TT=Drums|P2=50.00|P3=50.00|TO=75|RV=TRUE|
E_VALUECURVE_Wave_Height: Active=TRUE|Id=ID_VALUECURVE_Wave_Height|Type=Timing Track Fade Fixed|Min=0.00|Max=100.00|TT=Drums|P2=100.00|P3=10.00|RV=TRUE|
B_VALUECURVE_Rotation: Active=TRUE|Id=ID_VALUECURVE_Rotation|Type=Ramp|Min=0.00|Max=100.00|P2=100.00|RV=TRUE|
E_VALUECURVE_Wave_YOffset: Active=TRUE|Id=ID_VALUECURVE_Wave_YOffset|Type=Ramp|Min=-250.00|Max=250.00|P1=150.00|P2=50.00|RV=TRUE|
E_VALUECURVE_Wave_YOffset: Active=TRUE|Id=ID_VALUECURVE_Wave_YOffset|Type=Ramp|Min=-250.00|Max=250.00|P1=-150.00|P2=-50.00|RV=TRUE|
```

The Saw Tooth and the `TT=Drums` curves are one sequence's; the buffer rotation has breadth.
`TT=Drums` names that file's own track; for us `TT=Beats` only works after `xlo finalize` patches
the Beats track.

### Prop fit and render style

Mega tree 29% (6 seq / 6 songs), pixel fields 26% (4 seq), matrix 21% (4 seq), whole-house
groups 6%, spinners 5%, stakes 4% (3 seq / 2 songs), small trees 3%. On a matrix or a pixel
field a wave is a line; on a tree a line crossing the cone; on a single-row prop (roofline,
arch, a stake group at per-model) the buffer is one row high and the sine becomes a chase of lit
segments — fine on stakes (Shut Up and Dance BJ holds it on Pixel Stakes 6–35 beats), wrong for
a roofline you want calm. `Stacked X Horizontally` makes a stake row one long strip so a single
wave crosses all of them; `Overlaid X` draws the same wave on each prop. Rob's layout: the
tombstone stakes as a strip, the matrix as a sheet, never the characters.

### Timing

4 beats (30%), 8 (16%), 5 (11%); 2.96 s median. Phrase-length cells abutting, with the direction
flipping at the boundary; 9-beat sheets with 0.75 in / 0.5 out; the band 0.25 / 0.25; stakes
held 6–35 beats under a meter.

### Exemplars

No Light of Christmas run in the profile (26 placements in the main file, none among the top
three by model).

| Where | Stack top → bottom | Why it works |
|---|---|---|
| **Uptown Funk (Radio Edit).xsq** 0:58–1:15, pre-chorus into chorus, Pixel Field | On `2 is Unmask` · Wave Sine 900, Thickness 5, Height 50, Speed 13.48, `Overlaid X`, red, Right to Left 8 beats then Left to Right 7 beats · Off | a red line crossing the field, reversing every phrase, coloured by the On |
| Uptown Funk 2:55–3:10, bridge, Pixel Field | the same at Number of Waves 526, Speed 11.24, `Overlaid Z`, 4-beat cells alternating direction | longer waves and shorter cells for the bridge |
| **XATW Kid On Christmas (Eliot Wisser).xsq** 0:49–0:56, 1:44–1:50, 2:45–2:52, Matrix2 | Pinwheel · Wave ×2 then ×4, Mirror, Palette fill, Sine 798, Thickness 0, Height 19, Speed 20, Flip Horizontal, directions alternating, #FF80FF #80FFFF #8000FF, 4-beat cells, fade in 0.75 then out 0.5 | a filled lattice that thickens from two layers to four on the second cell |
| Kid On Christmas (Eliot Wisser) 0:34–0:41, 1:28–1:35, 2:24–2:30, Matrix2 | Spirals · Wave Mirror Triangle 900, Thickness 11, Height 77, Speed 10, Flip Horizontal, fades 0.75 / 0.5, Wipe out, #80FFFF, 9 beats · Butterfly | a soft mirrored triangle sheet between the spirals and the bed, once per chorus |
| **XATW Shut Up and Dance (Bill Jenkins).xsq** 0:25–0:41, 1:06–1:22, Pixel Stakes | VU Meter `2 is True Unmask` · Wave Sine 1800, Speed 10, Right to Left, red + green + blue + yellow, 34–35 beats | the stakes show a rainbow wave only where the meter lights: audio-reactive without a re-cut |

### Anti-patterns

- **Direction flipped every cell** (ours, from the weave's ltr/rtl alternation on a chase-family
  effect): a line that jitters. 4–8 beats per direction.
- **Speed 30–50 on a tight wave.** A strobe.
- **Thickness 50, Height 100 and a Palette fill together.** A flat wash with a wobble; keep one.
- **A single wave at Normal over a textured bed.** It just draws a line across it; for
  interaction use `2 is True Unmask`.
- **Rainbow on a bare wave.** One colour (63%); the rainbow belongs under a meter.
- **Wave alone on a group canvas.** 52 of 408 placements are alone, and those are stakes.

### What code can realize today

- `look_id` + `knobs`: `Wave#1` is the free look (Direction, Type, Number_Waves 300–900,
  Thickness 5–54, Height 14–100, YOffset −89…99, Speed, buffer incl. Overlaid X / Z); `#8` the
  Default-buffer sine with the Saw Tooth curves as knobs; `#44` the window (blend as a knob:
  `1 is True Unmask` / `2 is True Unmask`, or set `blend`); `#35` (Mirror, Fill, 429–2136, YOffset
  −78…0); `#39` the Max blend; `#12` / `#27` the lattice (SubBuffer halves as a knob); `#13` /
  `#29` the fat triangle; `#34` the square band; `#31` (Blur 15, fades). pick_pool: `#1 #35 #8
  #31 #6 #34`.
- `effect_meta.py`: speed `E_TEXTCTRL_Wave_Speed` 5–35; `ltr` / `rtl` →
  `E_CHOICE_Wave_Direction`; energy 2–3; cellable and chase-family, so the weave uses it as a
  carrier (which is where the jitter comes from). On a layer, `direction` sets it, `twin:
  "counter"` reverses it, `twin: "flip"` is Flip Horizontal.
- `settings`: the curve strings, `B_SLIDER_Blur`,
  `B_CUSTOM_SubBuffer=0.00x50.00x100.00x100.00x0.00x0.00` (not a reserved key); `blend`,
  `transform`, `fade_in` / `fade_out`, `render_style` are fields.
- Not synthesized: the opposite-YOffset twin (write two layers with `E_SLIDER_Wave_YOffset`
  knobs on `#1`); the On-over-Wave-over-Off sandwich (three layers, the On with `blend: "2 is
  Unmask"`); the VU Meter window (a VU Meter layer above with `blend: "2 is True Unmask"`).
