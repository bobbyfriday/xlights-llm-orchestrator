# Fireworks

A burst of particles on the beat — Fire Timing on the Beats track, one beat long, a Shockwave over it — or a falling three-colour finale; nine placements in two sequences, so the craft is mostly labelled.

---

## Corpus facts

> Generated 2026-11-03 from the deduped corpus: **22 community sequences, 14 distinct songs** (xLights 2020.45–2025.08; 0 byte-identical files dropped). 2 sequences / 2 songs use Fireworks: **9 placements, 11 overlapping pairs.** Every share carries its breadth (sequences / songs); a habit in one sequence is one sequencer's habit, however many placements it has.
>
> Sources by placements: Uptown Funk (Updated 11.25) 7 · Kid On Christmas (Jeremy Poling) 2.

### Where it is placed

| Prop class | Share | Breadth | Example model names |
|---|---|---|---|
| snowflake | 78% | 1 seq / 1 song | Snowflakes (Important - Any house prop group) |
| group_all | 22% | 1 seq / 1 song | *Entire Display no Floods |

### Dials observed

Share · breadth per value; `curved` = that key has an active value curve instead of a static value.

| Key | Values |
|---|---|
| `FIRETIMING` (checkbox) | 1: 78% · 1 seq / 1 song — 0: 22% · 1 seq / 1 song — range 0…1 |
| `Gravity` (checkbox) | 0: 78% · 1 seq / 1 song — 1: 22% · 1 seq / 1 song — range 0…1 |
| `HoldColour` (checkbox) | 1: 100% · 2 seq / 2 songs |
| `UseMusic` (checkbox) | 0: 100% · 2 seq / 2 songs |
| `FIRETIMINGTRACK` (choice) | Beats: 78% · 1 seq / 1 song — <absent>: 22% · 1 seq / 1 song |
| `Count` (slider) | 100: 78% · 1 seq / 1 song — 50: 22% · 1 seq / 1 song — range 50…100 |
| `Explosions` (slider) | <absent>: 78% · 1 seq / 1 song — 3: 22% · 1 seq / 1 song |
| `Fade` (slider) | 53: 78% · 1 seq / 1 song — 50: 22% · 1 seq / 1 song — range 50…53 |
| `Velocity` (slider) | 2: 100% · 2 seq / 2 songs |
| `XLocation` (slider) | 50: 78% · 1 seq / 1 song — -1: 22% · 1 seq / 1 song — range -1…50 |
| `XVelocity` (slider) | 0: 100% · 2 seq / 2 songs |
| `YLocation` (slider) | 50: 78% · 1 seq / 1 song — -1: 22% · 1 seq / 1 song — range -1…50 |
| `YVelocity` (slider) | 0: 100% · 2 seq / 2 songs |
| `XLocation` (textctrl) | 50: 78% · 1 seq / 1 song — -1: 22% · 1 seq / 1 song — range -1…50 |
| `XVelocity` (textctrl) | 0: 100% · 2 seq / 2 songs |
| `YLocation` (textctrl) | 50: 78% · 1 seq / 1 song — -1: 22% · 1 seq / 1 song — range -1…50 |
| `YVelocity` (textctrl) | 0: 100% · 2 seq / 2 songs |
| `B_CHOICE_BufferStyle` | Per Model Per Preview: 78% · 1 seq / 1 song — Per Model Default: 22% · 1 seq / 1 song |

### Value curves

| Parameter | Share · breadth | Shapes |
|---|---|---|
| any curve | 0% · 0 seq / 0 songs | |

Most-used exact strings (copy verbatim; `Min`/`Max` are the parameter range, `P*` the real values):

```
```

### Palette habits

Colors per placement: 1: 78% · 3: 22%.
Black as a color: 0% · 0 seq / 0 songs. Sparkles on: 0% · 0 seq / 0 songs.
Top palettes: #FFFFFF 7 · #FFFFFF+#DAA520+#00FF00 2.

### Duration

Median 0.33 s. <1 s 78% · 2–4 s 22%.
In beats (9 placements with a beat track): 1 beats 78% · 3 beats 22%.

### Stacking

**100% of placements share the model with at least one concurrent effect (2 seq / 2 songs); 0% with three or more (0 seq / 0 songs).**

Partner types (pairs · sequences): Shockwave 7 · 1 · Fireworks 2 · 1 · Bars 2 · 1.

Above Fireworks (partner type, the partner's blend): Shockwave 7 Normal · Fireworks 1 Normal.

Beneath Fireworks (partner type, Fireworks's own blend over it): Bars 2 Normal · Fireworks 1 Normal.

Recurring full stacks (top → bottom, `*` = the mined effect): Shockwave > *Fireworks (7) · *Fireworks > Fireworks > Bars (1) · Fireworks > *Fireworks > Bars (1).

Same-type twins (1 top-over-bottom pairs): identical effect settings 100%; buffer transform differs 0%.

---

## Craft

### Identity and role

Particles launched from a point and flung outward, fading as they fly. From the corpus:
**Count** is the particles per burst (100 on the Uptown Funk snowflakes, 50 on Jeremy Poling's
whole house); **Explosions** is how many bursts the effect fires on its own (3 in Jeremy's,
absent in Uptown Funk's, where the timing track fires them instead); **Velocity** 2 in all 9;
**Fade** 53 / 50 is how fast the particles die; **XLocation / YLocation** 50 / 50 is a burst at
the buffer's centre, −1 / −1 is a random position per burst (Jeremy's); **X / YVelocity** 0 (no
drift); **Gravity** on in Jeremy's (the sparks fall), off in Uptown Funk's; **HoldColour** on in
all 9 (each particle keeps its launch colour); **UseMusic** off in all 9; **FIRETIMING** on
with **FIRETIMINGTRACK** `Beats` in Uptown Funk's 7 (78%): a burst on every mark of the Beats
track. Not from the corpus, xLights' behaviour: with Fire Timing on the Explosions count is
ignored and each timing mark fires one burst; Use Music fires on the audio level instead.

Role: **accent** in the corpus — 78% are one beat (median 0.33 s), each cut to a single
beat-triggered burst with a Shockwave over it; the other two are a 3-beat twin over Bars at a
section end. 100% share the model. Two sequences on two songs: the anchors are two sequencers'
habits and the rest is labelled.

### Thematic fit

The finale, the drop, the Fourth of July, "light up the sky". The sequencing skill lists it
under peak / celebration and counts it as a high-attention feature (one per moment, with
Kaleidoscope, Shader and Shockwave). White is the corpus colour (7 of 9); white + goldenrod +
green on Jeremy's Christmas house. Halloween: orange + purple bursts on the hero matrix at the
last chorus, a Gravity burst on the whole yard as the song ends (the sparks fall onto the
graves), white at the scream. Christmas: a Beats-triggered white burst on the snowflakes through
the intro of a party song (Uptown Funk). Save it: a Fireworks in a verse spends the finale.

### Anchors (starting points, not a menu)

| Anchor | Settings | Catalog look | Where | Dials to move |
|---|---|---|---|---|
| **Beat burst** | Fire Timing on, track `Beats`, Count 100, Fade 53, Velocity 2, X / Y 50, Gravity off, HoldColour, `Per Model Per Preview`, white, 1 beat, a Shockwave above | `Fireworks#1` (frozen) | Uptown Funk (Updated 11.25) intro 0:00–0:07, Snowflakes (Important - Any house prop group), seven times | the colour; which beats get one (Uptown Funk: every second beat) |
| **Falling finale** | Fire Timing off, Explosions 3, Count 50, Fade 50, Velocity 2, X / Y −1 (random), Gravity on, HoldColour, `Per Model Default`, white + goldenrod + green, 3 beats, two identical layers over Bars | `Fireworks#0` (frozen) | XATW Kid On Christmas Jeremy Poling, *Entire Display no Floods, 2:00–2:02 | Explosions with the length (3 in 3 beats); the palette |
| **Music burst** | Use Music on | none; not from the corpus (0 of 9) | | the sensitivity; verify in xLights |

**Dials** — pick from the observed values, then move one:

| Dial | Sane range | Moving it | Corpus picks |
|---|---|---|---|
| Count | 50–100 | particles per burst | 100 (one seq) · 50 (one seq) |
| Explosions | 3 | bursts per effect when Fire Timing is off | 3 · absent |
| Velocity | 2 | how far they fly | 2 (2 / 2) |
| Fade | 50–53 | how fast they die | 53 · 50 |
| X / YLocation | 50 / 50 · −1 / −1 | centre burst vs random | 50 (one seq) · −1 (one seq) |
| X / YVelocity | 0 | drift | 0 (2 / 2) |
| Gravity | on / off | sparks fall | off 78% · on (one seq) |
| HoldColour | on | each spark keeps its colour | on 100% (2 / 2) |
| Fire Timing / track | on + `Beats` · off | a burst per timing mark | on 78% (one seq) |
| UseMusic | off | bursts on the audio level | off 100% |
| Buffer | Per Model Per Preview · Per Model Default | a burst on every prop vs each prop's own | 78% · 22% |

**How to permute.** Fire Timing on and the placement cut to the beats you want (Uptown Funk:
one beat, every second beat, seven times through the intro); Gravity on and X / Y −1 for the
finale so the bursts land somewhere new and the sparks fall; Count down to 50 on a whole-house
group, up to 100 on the hero; the colour with the section.

### Layering recipes

| Name | Stack (top → bottom) | Blend | Use |
|---|---|---|---|
| **Ring over the burst** | Shockwave · Fireworks | Normal | Uptown Funk: the ring and the sparks on the same beat (7) |
| **Double finale** | Fireworks · Fireworks · Bars | Normal | Jeremy: two identical burst layers over a Bars carrier (1 + 1) |
| **Burst over a bed** | Fireworks · a slow Color Wash or Spirals | Normal | not from the corpus: the black between sparks is transparent, so the bed stays lit |
| **Burst over black** | Fireworks · Off | Normal | not from the corpus: a dark house for the finale, only the sparks |

### Value curves

None observed (0 of 9). The burst is its own motion; Fire Timing is the rhythm dial.

### Prop fit and render style

Snowflakes 78% (one sequence, `Per Model Per Preview`: a burst on every flake at once) and the
whole house 22% (`Per Model Default`: each prop its own random burst). It needs a 2D buffer to
fly in; on a line it is a flicker. On the Halloween layout: the hero matrix (the default
buffer) for a centred burst, the stakes `Per Model Default` with X / Y −1 so each stone gets
its own, `SEM_ALL` for the finale. Not the video panel.

### Timing

1 beat 78% (median 0.33 s: one burst, cut off before it fades), 3 beats 22%. Uptown Funk fires
every second beat (0.65, 1.70, 2.75, 3.77, 4.83, 5.88, 6.90 s). No fades on any of the 9. A
finale burst in `xlo-sequencing` terms is a hit (≤ 1 bar) or a short phrase; `effect_meta`
classes it as a phrase.

### Exemplars

| Where | Stack top → bottom | Why it works |
|---|---|---|
| **Uptown Funk (Radio Edit) Updated 11.25.xsq** 0:00–0:07, intro, Snowflakes (Important - Any house prop group) | Shockwave · Fireworks Fire Timing `Beats`, Count 100, Fade 53, Velocity 2, X / Y 50, HoldColour, `Per Model Per Preview`, white, 1 beat, every second beat | seven white bursts on the beat with a ring over each: the sparks are the beat's decay, the ring its attack |
| **XATW Kid On Christmas Jeremy Poling.xsq** 2:00–2:02, *Entire Display no Floods | Fireworks Gravity, Explosions 3, Count 50, Fade 50, Velocity 2, X / Y −1, HoldColour, `Per Model Default`, white + goldenrod + green ×2 · Bars | three random bursts per prop, doubled, falling under gravity for three beats over the bars: the end of the section lands |

### Anti-patterns

- **Fireworks as a bed.** Nine placements, none longer than three beats.
- **Fire Timing on with no matching track.** The bursts never fire. `Fireworks#1` freezes the
  track name `Beats`, which is Uptown Funk's own track and happens to match the one
  `xlo finalize` writes; until the .xsq is patched the look is silent, and the emitter rebinds
  only VU Meter's track key, not `E_CHOICE_FIRETIMINGTRACK`.
- **Fireworks on every beat for a section.** Uptown Funk gives it seven beats of an intro, not
  the song.
- **Fireworks with a Shader or Kaleidoscope at the same moment.** One high-attention feature
  per moment (`xlo-sequencing`).
- **A one-colour burst on the finale.** Jeremy's three colours with HoldColour give sparks of
  three kinds; white alone is the beat burst.

### What code can realize today

- `look_id`: `Fireworks#1` (the beat burst, every key frozen including the `Beats` track and
  `Per Model Per Preview`) and `#0` (the falling finale, frozen); no knobs on either, so a
  different Count, Explosions or X / Y goes in `settings` as `E_SLIDER_Fireworks_Count`,
  `E_SLIDER_Fireworks_Explosions`, `E_SLIDER_Fireworks_XLocation` / `_YLocation` (each slider
  has a matching `E_TEXTCTRL_` twin in the look; set both). The picker rotates `#1`, `#0`.
- `effect_meta`: energy band 3–5, `duration_class="phrase"`; no speed, no direction. Nothing
  synthesizes the beat burst: write a `stack` layer with `role: "accent"`,
  `look_id: "Fireworks#1"`, `cell_beats: 2` for the every-second-beat pattern (the cell holds
  the burst for two beats where Uptown Funk cuts it at one), on the hero or the snowflake-class
  group, and a Shockwave accent layer above it; `#0` with `cell_beats: 0` and
  `render_style: "Per Model Default"` on `SEM_ALL` for the last three beats of the finale.
