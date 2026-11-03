# VU Meter

Not an audio meter in practice: 95% of placements are `Timing Event …` types that fire on a timing track's marks — a per-beat color change, pulse, sweep or spike — the community's way to cut a layer to the beat without re-cutting it.

---

## Corpus facts

> Generated 2026-11-03 from the deduped corpus: **22 community sequences, 14 distinct songs** (xLights 2020.45–2025.08; 0 byte-identical files dropped). 12 sequences / 7 songs use VU Meter: **1,674 placements, 1,270 overlapping pairs.** Every share carries its breadth (sequences / songs); a habit in one sequence is one sequencer's habit, however many placements it has.
>
> Sources by placements: Shut Up and Dance (Bill Jenkins) 1035 · Shut Up and Dance (Tammy Ghee) 235 · Light Of Christmas (main) 99 · Christmas Just Ain't Christmas 74 · Danger Zone (XATW) 66 · Baby Shark (John Storms) 50 · Kid On Christmas (Greg Colburn) 40 · Light Of Christmas (XATW sharer A) 32 · the other 4 files 43 together.

### Where it is placed

| Prop class | Share | Breadth | Example model names |
|---|---|---|---|
| tree | 15% | 10 seq / 7 songs | Mini Trees, MiniTree 1, MiniTree 2 |
| flood | 14% | 7 seq / 5 songs | Flood Lights, FloodLight 1, FloodLight 2 |
| cane | 13% | 6 seq / 3 songs | Candy Canes, Candy Cane 1, Candy Cane 2 |
| other | 12% | 5 seq / 4 songs | Diag 1, Horizontals, Verticals |
| arch | 11% | 4 seq / 3 songs | Arches, Arch Fans, Arch Fan 1 |
| matrix | 10% | 3 seq / 2 songs | P10, Matrix1, Matrix2 |
| megatree | 9% | 8 seq / 6 songs | MegaTree Singing Faces, MegaTree 1, Boscoyo 46 MegaSpinner |
| star | 6% | 3 seq / 2 songs | Star 1, Star 2, Star1 |
| spinner | 2% | 3 seq / 2 songs | Spinners, Spinner |
| snowflake | 2% | 6 seq / 5 songs | Snowflakes, SnowFlakes, 5pt Flake L |
| stake | 1% | 1 seq / 1 song | Pixel Stakes |
| icicle | 1% | 1 seq / 1 song | Icicles |

### Dials observed

Share · breadth per value; `curved` = that key has an active value curve instead of a static value.

| Key | Values |
|---|---|
| `Regex` (checkbox) | 0: 77% · 4 seq / 2 songs — <absent>: 23% · 9 seq / 6 songs |
| `LogarithmicX` (checkbox) | <absent>: 100% · 12 seq / 7 songs — 0: 0% · 2 seq / 2 songs |
| `SlowDownFalls` (checkbox) | <absent>: 97% · 12 seq / 7 songs — 1: 3% · 3 seq / 3 songs — 0: 0% · 1 seq / 1 song — range 0…1 |
| `Shape` (choice) | <absent>: 99% · 12 seq / 7 songs — Filled Diamond: 1% · 1 seq / 1 song — Filled Circle: 0% · 1 seq / 1 song — Circle: 0% · 1 seq / 1 song |
| `TimingTrack` (choice) | Timings: 18% · 1 seq / 1 song — Beats 256bpm: 16% · 1 seq / 1 song — Beats 128bpm: 14% · 1 seq / 1 song — Beat Count: 10% · 2 seq / 2 songs — Beats: 10% · 7 seq / 5 songs — Drums: 8% · 1 seq / 1 song — GUITAR: 5% · 1 seq / 1 song — Note Onsets pt2: 4% · 1 seq / 1 song |
| `Type` (choice) | Timing Event Color: 49% · 5 seq / 4 songs — Timing Event Pulse Color: 15% · 7 seq / 5 songs — Timing Event Alternate Timed Sweep: 13% · 2 seq / 2 songs — Timing Event Pulse: 10% · 5 seq / 5 songs — Timing Event Spike: 3% · 1 seq / 1 song — Timing Event Timed Chase From Middle: 1% · 2 seq / 2 songs — Spectrogram: 1% · 1 seq / 1 song — Timing Event Bar: 1% · 3 seq / 3 songs |
| `E_FILEPICKERCTRL_SVGFile` | : 65% · 2 seq / 2 songs — <absent>: 35% · 11 seq / 6 songs |
| `Bars` (slider) | <absent>: 50% · 5 seq / 4 songs — 6: 20% · 7 seq / 6 songs — 8: 10% · 3 seq / 2 songs — 50: 5% · 1 seq / 1 song — 25: 4% · 2 seq / 2 songs — 10: 2% · 3 seq / 3 songs — 3: 1% · 2 seq / 2 songs — 100: 1% · 1 seq / 1 song — range 1…100 |
| `EndNote` (slider) | <absent>: 98% · 12 seq / 7 songs — 84: 2% · 2 seq / 2 songs |
| `Gain` (slider) | <absent>: 99% · 12 seq / 7 songs — 0: 1% · 2 seq / 2 songs — 100: 0% · 1 seq / 1 song — range 0…100 |
| `Sensitivity` (slider) | <absent>: 51% · 12 seq / 7 songs — 70: 48% · 4 seq / 3 songs — 25: 0% · 1 seq / 1 song — 40: 0% · 1 seq / 1 song — 15: 0% · 1 seq / 1 song — 100: 0% · 1 seq / 1 song — range 15…100 |
| `StartNote` (slider) | <absent>: 98% · 12 seq / 7 songs — 36: 2% · 2 seq / 2 songs |
| `XOffset` (slider) | <absent>: 97% · 12 seq / 7 songs — 0: 3% · 3 seq / 3 songs |
| `YOffset` (slider) | <absent>: 97% · 12 seq / 7 songs — 0: 3% · 3 seq / 3 songs |
| `Filter` (textctrl) | : 77% · 4 seq / 2 songs — <absent>: 23% · 9 seq / 6 songs |
| `Gain` (textctrl) | <absent>: 99% · 12 seq / 7 songs — 0: 1% · 2 seq / 2 songs — 100: 0% · 1 seq / 1 song — range 0…100 |
| `B_CHOICE_BufferStyle` | <absent>: 81% · 11 seq / 7 songs — Per Model Default: 7% · 4 seq / 2 songs — Default: 6% · 2 seq / 1 song — Single Line: 2% · 1 seq / 1 song — Layer Star: 2% · 1 seq / 1 song — Single Line Model As A Pixel: 1% · 1 seq / 1 song — Per Model Single Line: 1% · 2 seq / 2 songs — Vertical Stack: 0% · 2 seq / 2 songs |
| `B_CHOICE_BufferTransform` | <absent>: 94% · 12 seq / 7 songs — Rotate 180: 4% · 4 seq / 4 songs — Rotate CC 90: 2% · 4 seq / 3 songs — Rotate CW 90: 0% · 1 seq / 1 song — Flip Horizontal: 0% · 1 seq / 1 song |
| `T_CHOICE_LayerMethod` | <absent>: 84% · 12 seq / 7 songs — 2 is True Unmask: 12% · 1 seq / 1 song — 1 is True Unmask: 1% · 2 seq / 2 songs — Normal: 1% · 1 seq / 1 song — Brightness: 1% · 1 seq / 1 song — Layered: 1% · 2 seq / 2 songs — Effect 1: 0% · 1 seq / 1 song |
| `T_TEXTCTRL_Fadein` | <absent>: 85% · 11 seq / 7 songs — 0.25: 6% · 2 seq / 2 songs — .4: 4% · 2 seq / 2 songs — .2: 3% · 1 seq / 1 song — 1.00: 0% · 1 seq / 1 song — 0.75: 0% · 1 seq / 1 song — .5: 0% · 1 seq / 1 song — 00: 0% · 1 seq / 1 song — range 0…7 |
| `T_TEXTCTRL_Fadeout` | <absent>: 87% · 11 seq / 7 songs — 0.25: 8% · 2 seq / 2 songs — .4: 3% · 1 seq / 1 song — .3: 1% · 1 seq / 1 song — 0.75: 0% · 1 seq / 1 song — 1.00: 0% · 1 seq / 1 song — .5: 0% · 1 seq / 1 song — 9: 0% · 1 seq / 1 song — range 0.2…12 |
| `T_CHOICE_Out_Transition_Type` | <absent>: 100% · 12 seq / 7 songs — Square Explode: 0% · 1 seq / 1 song |
| `B_SLIDER_Blur` | <absent>: 99% · 12 seq / 7 songs — 3: 1% · 1 seq / 1 song |

### Value curves

| Parameter | Share · breadth | Shapes |
|---|---|---|
| any curve | 11% · 4 seq / 3 songs | |
| `B_VALUECURVE_Rotation` | 7% · 3 seq / 2 songs | Ramp 105 · Ramp Up/Down 7 |
| `T_VALUECURVE_In_Transition_Adjust` | 4% · 1 seq / 1 song | Ramp 64 |
| `T_VALUECURVE_Out_Transition_Adjust` | 1% · 1 seq / 1 song | Custom 12 |

Most-used exact strings (copy verbatim; `Min`/`Max` are the parameter range, `P*` the real values):

```
B_VALUECURVE_Rotation (54, 2 seq / 2 songs): Active=TRUE|Id=ID_VALUECURVE_Rotation|Type=Ramp|Min=0.00|Max=100.00|P2=100.00|RV=TRUE|
B_VALUECURVE_Rotation (51, 2 seq / 2 songs): Active=TRUE|Id=ID_VALUECURVE_Rotation|Type=Ramp|Min=0.00|Max=100.00|P1=100.00|RV=TRUE|
B_VALUECURVE_Rotation (7, 1 seq / 1 song): Active=TRUE|Id=ID_VALUECURVE_Rotation|Type=Ramp Up/Down|Min=0.00|Max=100.00|P2=100.00|RV=TRUE|
T_VALUECURVE_In_Transition_Adjust (64, 1 seq / 1 song): Active=TRUE|Id=ID_VALUECURVE_In_Transition_Adjust|Type=Ramp|Min=0.00|Max=100.00|P1=33.00|P2=67.00|RV=TRUE|
T_VALUECURVE_Out_Transition_Adjust (12, 1 seq / 1 song): Active=TRUE|Id=ID_VALUECURVE_Out_Transition_Adjust|Type=Custom|Min=0.00|Max=100.00|RV=TRUE|Values=0.00:0.30;0.14:0.50;0.22:0.63;0.31:0.78;0.42:0.85;0.51:0.78;0.57:0.69;0.64:0.56;0.73:0.40;0.80:0.28;0.89:0.20;0.93:0.20;1.00:0.29|
```

### Palette habits

Colors per placement: 1: 13% · 2: 21% · 3: 5% · 4: 2% · 5: 0% · 6: 1% · 7: 4% · 8: 54%.
Black as a color: 24% · 2 seq / 1 song. Sparkles on: 8% · 4 seq / 4 songs.
Top palettes: #FFFFFF+#FF0000+#00FF00+#0000FF+#FFFF00+#8000FF+#00FFFF+#FF00FF 366 · #FF00FF+#00FFFF+#8000FF+#FFFF00+#0000FF+#00FF00+#FF0000+#FFFFFF 259 · #FFFFFF+#000000+#00FF00+#000000+#FFFF00+#000000+#00FFFF+#000000 134 · #000000+#FF0000+#000000+#0000FF+#000000+#8000FF+#000000+#FF00FF 134 · #FFFFFF 87 · #00FF00+#0000FF 51 · #0000FF+#FFFF00 41 · #FF00FF+#00FFFF+#000000+#FFFF00+#0000FF+#FF0000+#FFFFFF 40.

### Duration

Median 3.80 s. <1 s 2% · 1–2 s 21% · 2–4 s 38% · 4–8 s 12% · 8–16 s 19% · ≥16 s 8%.
In beats (1664 placements with a beat track): 8 beats 16% · 5 beats 14% · 2 beats 11% · 4 beats 8% · 34 beats 6% · 3 beats 5% · 7 beats 4% · 12 beats 4%.

### Stacking

**30% of placements share the model with at least one concurrent effect (10 seq / 7 songs); 6% with three or more (2 seq / 1 song).**

Partner types (pairs · sequences): VU Meter 867 · 6 · Shader 109 · 1 · Warp 58 · 3 · Pinwheel 41 · 2 · Wave 41 · 1 · SingleStrand 36 · 3 · Meteors 26 · 2 · Faces 24 · 2 · Bars 16 · 2 · Shockwave 12 · 1 · Spirals 7 · 3 · On 6 · 1 · Ripple 5 · 1 · Twinkle 5 · 1 · Marquee 5 · 2 · Snowflakes 4 · 1 · Butterfly 4 · 2 · Color Wash 2 · 1 · Fan 2 · 1.

Above VU Meter (partner type, the partner's blend): VU Meter 425 Normal · Warp 58 Normal · SingleStrand 28 Normal · Meteors 24 Normal · Faces 24 Normal · VU Meter 16 2 is True Unmask · Bars 15 2 is Unmask · Shockwave 12 Normal · Spirals 7 Normal · Butterfly 2 Normal · Butterfly 2 2 is Unmask · Fan 2 Normal · Pinwheel 1 Brightness · Snowflakes 1 Normal · Bars 1 Normal.

Beneath VU Meter (partner type, VU Meter's own blend over it): VU Meter 410 Normal · Shader 109 2 is True Unmask · Wave 41 2 is True Unmask · Pinwheel 40 2 is True Unmask · VU Meter 16 2 is True Unmask · SingleStrand 8 2 is True Unmask · On 6 Normal · Twinkle 5 Normal · Marquee 5 Normal · Ripple 4 Brightness · Color Wash 2 Brightness · Snowflakes 2 Brightness · Meteors 2 2 is True Unmask · Ripple 1 Normal · Snowflakes 1 Layered.

Recurring full stacks (top → bottom, `*` = the mined effect): *VU Meter (1169) · *VU Meter > Shader (99) · VU Meter > *VU Meter (76) · *VU Meter > VU Meter (61) · *VU Meter > Wave (31) · *VU Meter > Pinwheel > Pinwheel (20) · Bars > *VU Meter (15) · Shockwave > *VU Meter (12) · SingleStrand > *VU Meter (11) · Faces > *VU Meter > Wave (10) · Faces > *VU Meter > Shader (10) · SingleStrand > SingleStrand > *VU Meter (8) · *VU Meter > SingleStrand (8) · *VU Meter > VU Meter > VU Meter > VU Meter > VU Meter > VU Meter > VU Meter > VU Meter (6) · VU Meter > *VU Meter > VU Meter > VU Meter > VU Meter > VU Meter > VU Meter > VU Meter (6) · VU Meter > VU Meter > *VU Meter > VU Meter > VU Meter > VU Meter > VU Meter > VU Meter (6).

Same-type twins (441 top-over-bottom pairs): identical effect settings 86%; buffer transform differs 51%.

---

## Craft

### Identity and role

VU Meter is a family chosen by **Type**. The audio-driven members (Spectrogram, Level Shape,
Waveform, Level Bar, On, …) are rendered by xLights from the song's audio at render time and
need no track. The timing-event members (`Timing Event Color`, `… Pulse`, `… Pulse Color`,
`… Alternate Timed Sweep`, `… Spike`, `… Bar`, `… Timed Chase From Middle` / `To Middle`,
`… Jump 100`, `… Random Bar`, `… Sweep`) fire once on every mark of the track named in
**TimingTrack** and do nothing between marks. The corpus is 95% timing-event: Timing Event
Color 49% (5 seq / 4 songs) fills the buffer with the *next* palette color on each mark; Pulse
Color 15% (7 / 5) flashes and decays into the next color; Alternate Timed Sweep 13% (2 / 2) runs
a bar across the buffer and reverses on each mark; Pulse 10% (5 / 5) is the one-color flash;
Spike 3%, Timed Chase From Middle 1% (2 / 2), Bar 1% (3 / 3); Spectrogram 1% (1 / 1). **Bars**
is the segment count (6 for pulses in 7 seq / 6 songs; 8; 25–50 for sweeps and spikes on a
per-model buffer). **Sensitivity** (70 rides along on the Color placements, 4 seq / 3 songs)
and **Gain**, **StartNote** / **EndNote** (36 / 84) and **SlowDownFalls** drive only the audio
types; **Shape** (Filled Diamond, Filled Circle) belongs to Level Shape.

Roles: **carrier** first — one placement of 2–8 beats, or a 34-beat phrase, does the per-beat
work because the track fires inside it (median 3.8 s, 2% under a second); **mask source** —
12% of placements carry `2 is True Unmask` (1 seq / 1 song, 1,035 placements): a Timing Event
Color above a Shader, Wave or Pinwheel shows only where the texture is lit, so the texture is
recolored on every drum hit; **feature** on the matrix (the Light of Christmas eight-strip
sweep); **overlay** for the audio types on a matrix. Never a bed: Pulse types are black between
marks, and a Color type is a bed only under a mask.

### Thematic fit

It says *on the beat* or *on the drum*, because the track is the music. It serves any song with
a strict grid (Shut Up and Dance holds 1,270 of 1,674 placements), drum-led verses, fills, and
sections where two instruments should own two layers: a BASS sweep in purple under a GUITAR
spike in green (Tammy Ghee). Palettes are long: 8 colors 54% — the full rainbow cycles one
color per mark through Timing Event Color — and the alternating-black lists (white / black /
green / black …, 134 each) make every other mark dark, a half-time feel from the same track.
Two colors (green + blue) for sweeps. Halloween: four theme colors with black between them for
half-time pulses; an orange-purple-green-white cycle for the drum-hit stamp over a vortex.
Christmas: the rainbow on the mega tree is the Shut Up and Dance tree.

### Anchors (starting points, not a menu)

Every catalog look freezes or offers *that sequencer's* track names (`Timings`, `Beats 128bpm`,
`Beats 256bpm`, `Beat Count`, `Drums`, `Drum Beats`, `GUITAR`, `BASS`, `LYRIC BEATS`, `Note
Onsets pt2`). Ours are `Beats`, `Bars`, `Onsets (drums)` (one `Onsets (<stem>)` per prominent
stem, drums always when present; plain `Onsets` without stems), `Sections`, `Lyrics` — written
by `xlo finalize`. `Beats` itself appears in 7 seq / 5 songs and in the knob sets of `#12`,
`#48`, `#0`, `#15`, `#14`; everywhere else override the track in `settings`.

| Anchor | Settings | Catalog look | Where | Dials to move |
|---|---|---|---|---|
| **Beat color** | Timing Event Color, TimingTrack = the beat track, 8-color palette, 2–8 beats or the phrase | `VU Meter#45` (Type frozen; knob TimingTrack {Beats 128bpm|Beats 256bpm|Drums|Note Onsets pt2|Timings}) with `settings` `E_CHOICE_VUMeter_TimingTrack=Beats`; or `#61` (Beats + `1 is True Unmask` frozen) | Shut Up and Dance (Bill Jenkins) everywhere: 288 on `Timings`, 180 on 128 bpm beats, 92 on 256 bpm | the track per phrase (drums for the fill, eighths for the run); 4 colors instead of 8 |
| **Beat pulse** | Timing Event Pulse (one color) or Pulse Color, Bars 6, fades .4/.4 or .2/0 | `#40` (knobs TimingTrack, Type {Pulse|Pulse Color|Timed Chase To Middle}, Bars 6–12); `#68` (Beat Count, Pulse, Bars 8, fade-in .2 frozen); `#38` (Drum Beats, Pulse Color, Bars 6, fades .4 frozen) | Danger Zone XATW on Beat Count; Christmas Just Ain't Christmas on Drum Beats | Bars 6 → 12; fade .4 for a soft pulse, 0 for a hard one |
| **Stamp through a texture** | Timing Event Color or Pulse Color with `2 is True Unmask` one layer above a Shader / Wave / Pinwheel pair | `#46` (Color; knobs TimingTrack + LayerMethod {2 is True Unmask|Normal}), `#41` (Pulse Color Bars 6, blend frozen), `#10`, `#5` | Shut Up and Dance (Bill Jenkins) MegaTree 1 for the whole song (109 Shader, 41 Wave, 40 Pinwheel pairs) | what sits beneath; the track |
| **Alternate sweep** | Alternate Timed Sweep, Bars 25–50, Per Model Default, two colors with black, 25–45 beats | `#12` (knobs BufferStyle, TimingTrack {BASS|Beats|GUITAR|LYRIC BEATS|Measures}, Type {Alternate Timed Sweep|… Sweep 2|Bar|Pulse Color|Spike|Sweep}, Bars 2–79) | Shut Up and Dance (Tammy Ghee) Arch Fans on BASS and Beats | Bars 25 vs 50; the stem track |
| **Strip sweep** | 8 layers of Alternate Timed Sweep, Beat Count, Bars 8, fades 0.25, each on a SubBuffer third or half with a Rotation ramp, half of them Rotate 180, green + blue | `#31` and `#24` (Rotate 180) (frozen; knobs SubBuffer strips + Rotation curve) | Light of Christmas Matrix1 0:25–0:37 | two strips on a prop instead of eight on the matrix |
| **Stem spike** | Timing Event Spike on a stem track, one color, Bars 25–50, over a sweep on another stem | `#12`, `#48`, `#0` (Spike in their Type knobs) | Tammy Ghee: GUITAR spikes green over BASS sweep purple (1 seq / 1 song) | Bars; Rotate CC 90 for a vertical spike |
| **Spectrogram / Level Shape** | Spectrogram, Bars 6–13, StartNote 36, EndNote 84, SlowDownFalls; or Level Shape Filled Diamond, Sensitivity 25–100 | `#59`; `#56`, `#18` | matrix and mega tree, 1 seq each: the only truly audio-reactive placements | Sensitivity |
| **Jump with a tail** | Timing Event Jump 100 on Beats, Bars 6–24, fade-out 9–12 s | `#35`, `#34` (one 2022.24 file) | a long decaying jump | |

**Dials** — pick from the observed values, then move one:

| Dial | Sane range | Moving it | Corpus picks |
|---|---|---|---|
| Type | the timing-event family vs the audio types | what fires per mark; Color holds, Pulse decays, Sweep travels, Spike jumps | Color 49% · Pulse Color 15% · Alternate Timed Sweep 13% · Pulse 10% · Spike · Bar · Timed Chase From Middle · Spectrogram |
| TimingTrack | a track in the sequence | which marks fire | Beats (7 seq / 5 songs) · the others are per-sequencer names |
| Bars | 1–100 | 6–8 segments for pulses; 25–50 for sweeps, spikes and chases | 6 · 8 · 25 · 50 · 10 · 3 |
| Sensitivity | 15–100 | audio types only | 70 |
| SlowDownFalls | on / off | slower fall of spectrum and level | 1 (3 seq / 3 songs) |
| StartNote / EndNote | 36 / 84 | the spectrogram's band | |
| Shape | Filled Diamond / Filled Circle / Circle | Level Shape | |
| Buffer | Per Model Default / Default / Single Line / Layer Star / Per Preview | sweeps per prop vs across the group; Color and Pulse fill the whole buffer either way | Per Model Default 7% (4 / 2) |
| Transform | Rotate 180 (4 / 4) / Rotate CC 90 (4 / 3) | reverses a sweep; makes it vertical on a tree | |
| Blend | Normal / 2 is True Unmask / 1 is True Unmask / Brightness / Layered | the stamp; VU as a brightness envelope over Ripple or Color Wash (4 + 2) | 2 is True Unmask 12% |
| Fades | 0.25/0.25 sweeps · .4/.4 pulses · .2/0 · 9–12 out for the Jump | | |

**How to permute.** Change the track, not the type: `Beats` in the verse, `Onsets (drums)` in
the fills, `Bars` for a half-time chorus (Bill Jenkins swaps Drums → 256 bpm → Note Onsets
between phrases). Change the Type on a section boundary (Color → Pulse Color). Rotate which
color the 8-color list starts on. For a twin, 51% of same-type pairs differ only by transform:
the same sweep Rotate 180 on the layer above.

### Layering recipes

| Name | Stack (top → bottom) | Blend | Use |
|---|---|---|---|
| **Beat stamp over a texture** | VU Meter Color / Pulse Color · Shader, or Wave, or Pinwheel · Pinwheel | VU: `2 is True Unmask` | the texture recolored on every mark (109 + 41 + 40); the Shut Up and Dance tree |
| **Two stems, one prop** | VU Spike (GUITAR, one color) · VU Alternate Timed Sweep (BASS, color + black) | Normal | each instrument its own motion and color for a whole verse |
| **Strip sweep** | VU × 8 on SubBuffer strips, alternating Rotate 180 | Normal | the matrix kaleidoscope from one beat track |
| **Warp over the meter** | Warp · VU Meter | Normal (58 pairs, 3 seq) | the sweep mirrored |
| **Bars over the meter** | Bars · VU Meter | Bars: `2 is Unmask` (15) | the pulse cut into bars |
| **Meter over a fill** | VU Pulse · On / Twinkle | Normal | pulses on a dim fill; or VU `Brightness` over Ripple / Color Wash as an envelope |

### Value curves

The beat is in `TimingTrack`, never in a curve. 11% of placements are curved (4 seq / 3 songs),
almost all the buffer rotation under a sweep.

| Want | Curve | Dial |
|---|---|---|
| the sweep's buffer turning over the phrase | `B_VALUECURVE_Rotation` Ramp 0 → 100 or 100 → 0 (3 seq / 2 songs, 105) | buffer rotation (`#24`, `#31`, `#26`) |
| turning there and back | Ramp Up/Down 0 → 100 → 0 (7, `#39`) | buffer rotation |
| a wiped-in pulse | `T_VALUECURVE_In_Transition_Adjust` Ramp 33 → 67 (`#68`, 1 seq) | transition |

```
B_VALUECURVE_Rotation: Active=TRUE|Id=ID_VALUECURVE_Rotation|Type=Ramp|Min=0.00|Max=100.00|P2=100.00|RV=TRUE|
B_VALUECURVE_Rotation: Active=TRUE|Id=ID_VALUECURVE_Rotation|Type=Ramp|Min=0.00|Max=100.00|P1=100.00|RV=TRUE|
B_VALUECURVE_Rotation: Active=TRUE|Id=ID_VALUECURVE_Rotation|Type=Ramp Up/Down|Min=0.00|Max=100.00|P2=100.00|RV=TRUE|
T_VALUECURVE_In_Transition_Adjust: Active=TRUE|Id=ID_VALUECURVE_In_Transition_Adjust|Type=Ramp|Min=0.00|Max=100.00|P1=33.00|P2=67.00|RV=TRUE|
```

No `TT=` curve rides on a VU Meter in the corpus; like `TimingTrack`, a `TT=Beats` curve only
works after `xlo finalize` patches the Beats track in.

### Prop fit and render style

Mini trees 15% (10 seq / 7 songs), floods 14% (7 / 5), canes 13% (6 / 3), arches 11% (4 / 3),
matrix 10% (3 / 2), mega tree 9% (8 / 6), stars 6%, snowflakes 2% (6 / 5), stakes 1%. Per Model
Default on arch and cane groups so each prop sweeps alone; Default on the mega tree; SubBuffer
strips on the matrix; Rotate CC 90 for a vertical sweep on a tree. Color and Pulse types fill
whatever buffer they get, so on floods and stakes the buffer does not matter. Our code's own VU
layer uses Per Preview on a wide ground band so bars span the group.

### Timing

Median 3.8 s: 8 beats 16%, 5 beats 14%, 2 beats 11%, 4 beats 8%, a 34-beat phrase 6%. One
placement does the per-beat work: cut it on phrase boundaries (2–8 beats, or the section) and
let the track fire inside. Fades 0.25 for sweeps, .4 for pulses, 0 for Color. Bill Jenkins
abuts a 2–3 beat Pulse Color fill to a 5–13 beat Color run and back, all on the same layer.

### Exemplars

| Where | Stack top → bottom | Why it works |
|---|---|---|
| **Light of Christmas.xsq** 0:25–0:37, verse 1, Matrix1 | 8 × VU Meter Alternate Timed Sweep, Beat Count, Bars 8, fades 0.25, each on a third or half strip with a Rotation ramp, layers 2/3/6/7 Rotate 180, green + blue then #008040 + blue; Warp on top from 0:33 | one beat track drives eight strips sweeping in opposite directions: a kaleidoscope with no kaleidoscope effect |
| **XATW Shut Up and Dance Bill Jenkins.xsq** 0:46–1:04 and on through 3:04, MegaTree 1 | VU Meter `2 is True Unmask` · Shader (Fly Through / Blue Streaks): Pulse Color on `Beats 256bpm` Bars 6 for the 2–3 beat fills, Timing Event Color on `Drums` Sensitivity 70 for the 5–13 beat runs; white / red / green / blue, then magenta / cyan / purple / yellow | the shader never changes; the beat stamp recolors it on every drum hit, and the track swaps at every phrase |
| **XATW Shut Up and Dance Tammy Ghee.xsq** 0:19–0:40, Arch Fans | VU Spike on `GUITAR` Bars 25 green · VU Alternate Timed Sweep on `BASS` Bars 25 purple + black, Per Model Default, 45 beats; then Timed Chase From Middle on BASS (4 beats) and Timing Event Bar on `LYRIC BEATS` Bars 2 | bass and guitar each own a layer of the arches for the whole verse; the lyric track takes the turnaround |

### Anti-patterns

- **A timing-event VU on a track the sequence does not have.** Nothing fires. The catalog's
  track names are other sequencers'; before `xlo finalize` the sequence has no tracks at all,
  so the pipeline's own VU layer (`place_vu_meter`: intensity ≥ 0.55, Per Preview on
  `SEM_BAND_GROUND` / `SEM_HOUSE` / `SEM_ALL`, rotating `#45`, `#40`, `#12`, `#68`, `#38`, `#48`)
  fires on nothing unless the look's track name happens to match ours.
- **Spectrogram or Level Shape on a small prop.** Six bars of spectrum on a cane is noise; matrix
  and mega tree only.
- **Re-cutting a VU every beat.** The track already does that; cut on phrases.
- **Eight arbitrary colors.** The cycle is visible: pick the eight from the theme, or four with
  black between them.
- **A VU alone on a group canvas.** It is the beat, not the look; the stamp idiom needs the
  texture beneath.

### What code can realize today

- `look_id` + `knobs` with our `Beats` track in the knob set: `#12` (Sweep / Spike / Bar / Pulse
  Color, Bars 2–79, buffer styles), `#48` (Pulse / Pulse Color / Spike / Sweep, Bars 2–50), `#0`
  (Sweep / Spike / Pulse Color, Bars 1–100, transforms), `#15` (Beats | Measures; chases and
  sweep, Bars 3–50), `#14` (chases from / to middle), `#51` / `#16` / `#52` (Bars 50 chases and
  sweeps), `#61` (Color with `1 is True Unmask` frozen). `#45`, `#40`, `#46`, `#41`, `#10`, `#5`
  carry Bill Jenkins' track names: add `settings: {"E_CHOICE_VUMeter_TimingTrack": "Beats"}` (or
  `"Onsets (drums)"`), which is merged after the knobs at placement. `#59` (Spectrogram) and
  `#56` / `#18` (Level Shape) need no track.
- `settings`: the Rotation curve strings and `B_CUSTOM_SubBuffer` strips (`#24` / `#31`
  knobs); `blend`, `transform`, `render_style` and the fades are fields.
- Tracks: `xlo finalize` writes `Sections`, `Beats`, `Bars`, `Onsets (<stem>)` per prominent
  stem or `Onsets`, `Chords`, `Lyrics` (and the Faces track). `xlo apply` places into a
  sequence with none, so judge any timing-event VU after finalize and a re-render.
- `effect_meta.py`: energy 2–5 only — no speed, no direction, not cellable. Code's
  `place_vu_meter` is withheld when the section has a stack. The two-stem recipe needs two
  layers naming different `Onsets (<stem>)` tracks and is authored only; nothing synthesizes a
  per-stem VU.
