# Shimmer

The whole prop blinking in palette bands — a 5-beat gold glitter on the snowflakes or a 2-beat white hit on the icicles, always alone and never on the beat: 16 placements from two sequencers.

---

## Corpus facts

> Generated 2026-11-03 from the deduped corpus: **22 community sequences, 14 distinct songs** (xLights 2020.45–2025.08; 0 byte-identical files dropped). 2 sequences / 2 songs use Shimmer: **16 placements, 0 overlapping pairs.** Every share carries its breadth (sequences / songs); a habit in one sequence is one sequencer's habit, however many placements it has.
>
> Sources by placements: Light Of Christmas (main) 8 · Shut Up and Dance (Bill Jenkins) 8.

### Where it is placed

| Prop class | Share | Breadth | Example model names |
|---|---|---|---|
| other | 31% | 1 seq / 1 song | Horizontals, Verticals, Horiz 4 |
| snowflake | 25% | 1 seq / 1 song | Snowflakes |
| tree | 25% | 1 seq / 1 song | Mini Tree Stars All |
| star | 12% | 1 seq / 1 song | Star 1, Star 2 |
| icicle | 6% | 1 seq / 1 song | Icicles |

### Dials observed

Share · breadth per value; `curved` = that key has an active value curve instead of a static value.

| Key | Values |
|---|---|
| `PRE_2017_7` (checkbox) | 1: 50% · 1 seq / 1 song — 0: 50% · 1 seq / 1 song — range 0…1 |
| `Use_All_Colors` (checkbox) | 1: 100% · 2 seq / 2 songs |
| `Duty_Factor` (slider) | 21: 50% · 1 seq / 1 song — 50: 50% · 1 seq / 1 song — range 21…50 |
| `Cycles` (textctrl) | 600.0: 50% · 1 seq / 1 song — 4: 50% · 1 seq / 1 song — range 4…600 |
| `B_CHOICE_BufferStyle` | Per Model Default: 50% · 1 seq / 1 song — <absent>: 50% · 1 seq / 1 song |
| `T_TEXTCTRL_Fadein` | .3: 50% · 1 seq / 1 song — <absent>: 50% · 1 seq / 1 song |
| `T_TEXTCTRL_Fadeout` | .75: 50% · 1 seq / 1 song — <absent>: 50% · 1 seq / 1 song |
| `B_SLIDER_Blur` | 8: 50% · 1 seq / 1 song — <absent>: 50% · 1 seq / 1 song |

### Value curves

| Parameter | Share · breadth | Shapes |
|---|---|---|
| any curve | 0% · 0 seq / 0 songs | |

Most-used exact strings (copy verbatim; `Min`/`Max` are the parameter range, `P*` the real values):

```
```

### Palette habits

Colors per placement: 2: 50% · 4: 50%.
Black as a color: 50% · 1 seq / 1 song. Sparkles on: 0% · 0 seq / 0 songs.
Top palettes: #000000+#F5D80A 8 · #FFFFFF+#FFFFFF+#FFFFFF+#FFFFFF 8.

### Duration

Median 1.61 s. <1 s 50% · 2–4 s 50%.
In beats (16 placements with a beat track): 5 beats 50% · 2 beats 50%.

### Stacking

**0% of placements share the model with at least one concurrent effect (0 seq / 0 songs); 0% with three or more (0 seq / 0 songs).**

Partner types (pairs · sequences): .

Above Shimmer (partner type, the partner's blend): .

Beneath Shimmer (partner type, Shimmer's own blend over it): .

Recurring full stacks (top → bottom, `*` = the mined effect): *Shimmer (16).

---

## Craft

### Identity and role

The whole prop blinking on and off in bands of the palette: not random pixels (that is Twinkle),
not a flat fill with a flicker box ticked (that is On's `Shimmer` checkbox), but its own effect
with a duty cycle. From the corpus: **Duty_Factor** is the share of each cycle the lights are on
(21 in Light of Christmas, 50 in Shut Up and Dance); **Cycles** is how many on / off cycles the
effect runs (4 over two beats in Bill Jenkins' icicle hit; 600.0 in Light of Christmas with
**PRE_2017_7** on, where the number reads as a rate, not a count — not from the corpus, xLights'
behaviour: the pre-2017.7 box keeps the older render, under which a big Cycles value is a fast
flicker); **Use_All_Colors** on in all 16 lights every palette colour at once in bands instead
of cycling one colour per blink, which is why Light of Christmas' black + gold palette gives
gold bands with black gaps (black as a colour in 50%: the thinning dial). Blur 8 on the Light of
Christmas look softens the bands.

Role: **accent** — a 2-beat white hit (Bill Jenkins) or a 5-beat gold glitter that comes and
goes through a bridge (Light of Christmas); never a bed. 0 of 16 placements share the model: it
is placed alone, in the gaps, on props that are otherwise dark in that moment. Two sequences on
two songs, 16 placements: two sequencers' habits, nothing more, so the recipes below are
labelled where they are not from the corpus.

### Thematic fit

Glitter. Shimmer says *sparkle*, *tinsel*, *stars*, *a spell flickering*; the sequencing skill
caps it at two bars. Christmas: gold + black on the snowflakes and the mini-tree stars through a
bridge (Light of Christmas), white on the icicles for a two-beat hit (Shut Up and Dance).
Halloween: orange + black on the tombstone stakes as a spell catches, purple + black on the
cats, a white two-beat shimmer on the hero at a scream. It is the glitter alternative to a
Twinkle pop: Twinkle scatters pixels, Shimmer blinks the prop. Against palette sparkles
(`C_CHECKBOX_Palette_Sparkles` inside another layer's render): Shimmer is a layer with its own
timing and palette; use it when the shimmer is the event.

### Anchors (starting points, not a menu)

| Anchor | Settings | Catalog look | Where | Dials to move |
|---|---|---|---|---|
| **Gold glitter** | PRE_2017_7 on, Use All Colors, Duty 21, Cycles 600.0, `Per Model Default`, Blur 8, fades .3 / .75, black + gold (#F5D80A), 5 beats | `Shimmer#0` (frozen) | Light of Christmas bridge 3 → pre-chorus, Snowflakes, Mini Tree Stars All, Star 1 / 2 (8 placements) | the palette (black + one colour); the prop |
| **Two-beat blink** | PRE_2017_7 off, Use All Colors, Duty 50, Cycles 4, white ×4, 2 beats, no fades | `Shimmer#1` (frozen) | XATW Shut Up and Dance Bill Jenkins, Icicles, Horizontals, Verticals, Horiz 4 (8 placements) | Cycles 4 → 8 for a faster blink (not from the corpus; `effect_meta` allows 4–12) |

**Dials** — pick from the observed values, then move one:

| Dial | Sane range | Moving it | Corpus picks |
|---|---|---|---|
| Duty_Factor | 21–50 | the on-share of each cycle: 21 a glint, 50 a square blink | 21 (one seq) · 50 (one seq) |
| Cycles | 4–12 with PRE_2017_7 off | blinks per effect | 4 · 600.0 (old render only) |
| PRE_2017_7 | on / off | the older render; keep it with Cycles 600 or drop both | 1 (one seq) · 0 (one seq) |
| Use_All_Colors | on | every palette colour at once in bands | on 100% (2 / 2) |
| Palette | 2–4 colours, black to thin | black + gold · white ×4 | |
| Buffer | Per Model Default · default | each prop blinks its own bands vs one set across the group | 50% / 50% |
| Blur | 8 | softens the bands | 8 (one seq) |
| Fades | .3 / .75 · none | the catch and the decay | |

**How to permute.** Change the prop, not the blink: Light of Christmas puts the same gold
glitter on the snowflakes, then the mini-tree stars, then the stars, a phrase apart. Change the
colour with the section (black + the section's accent colour). Duty 21 for a glitter, 50 for a
blink; two beats for a hit, five for a glitter that fades in and out.

### Layering recipes

The corpus places Shimmer alone (16 of 16). The rest is not from the corpus, built from the
blend semantics in SKILL.md:

| Name | Stack (top → bottom) | Blend | Use |
|---|---|---|---|
| **Alone in the gap** | Shimmer | — | the corpus habit: props that are otherwise dark blink gold for five beats |
| **Glitter over a bed** | Shimmer (black + one colour) · a slow Color Wash or Spirals | Normal | the black bands are transparent, so the bed shows between the blinks (not from the corpus) |
| **Shimmer as a brightness gate** | Shimmer `Brightness` · a feature | Brightness | the feature blinks at the Shimmer's duty cycle (not from the corpus) |
| **Twinkle over Shimmer** | Twinkle (white, Count 2–6) · Shimmer | Normal | glints on a blinking prop (not from the corpus) |

### Value curves

None observed (0 of 16). Not from the corpus: a Duty_Factor curve is possible under
`E_VALUECURVE_Shimmer_Duty_Factor`; verify in xLights before relying on it.

### Prop fit and render style

Small props and lines: snowflakes 25%, mini-tree stars 25%, stars 12%, icicles 6%, and Bill
Jenkins' roofline segments (Horizontals, Verticals, Horiz 4: 31%). `Per Model Default` (Light of
Christmas) so each snowflake blinks its own bands. It reads on anything, because it is the whole
prop blinking; it is wasted on a matrix, where Twinkle or sparkles do more. On the Halloween
layout: the stakes `Per Model Default`, the cats, the roofline for a two-beat white hit; not
the hero matrix as a bed.

### Timing

Two lengths and nothing else: 2 beats (50%, median under a second) and 5 beats (50%, 2–4 s).
Fades .3 / .75 on the five-beat glitter, none on the two-beat hit. The house rule from
`xlo-sequencing`: Shimmer ≤ 2 bars. Light of Christmas spaces its glitters a phrase apart
(2:38, 2:43, 2:46, 2:49): never every beat.

### Exemplars

| Where | Stack top → bottom | Why it works |
|---|---|---|
| **Light of Christmas.xsq** 2:38–2:40, 2:43–2:48 (×2), 2:49–2:51, bridge 3 → pre-chorus, Snowflakes (also Mini Tree Stars All, Star 1 / 2) | Shimmer PRE_2017_7, Use All Colors, Duty 21, Cycles 600.0, `Per Model Default`, Blur 8, fades .3 / .75, black + gold, 5 beats, alone | the snowflakes glitter gold for five beats while the matrix tells the story in Pictures, then go dark again; the black bands keep it a glitter, not a flood |
| **XATW Shut Up and Dance Bill Jenkins.xsq** 1:59–2:00, Icicles (also Horizontals, Verticals, Horiz 4) | Shimmer Use All Colors, Duty 50, Cycles 4, white ×4, 2 beats, alone | four white blinks in two beats on the icicles: a hit on a line prop without a Shockwave |

### Anti-patterns

- **Shimmer as a bed.** The longest placement is five beats; past two bars it is a fault.
- **Shimmer every beat.** Light of Christmas drops it a phrase apart.
- **A one-colour palette with Use All Colors.** The prop blinks solid; add black to thin it.
- **Cycles 600 with PRE_2017_7 off.** Six hundred blinks in two beats is a strobe. Keep the pair
  as the look freezes them.
- **Shimmer on the matrix.** Nothing to see but a blinking rectangle; Twinkle there.
- **Our own pipeline: the Cycles override.** `effect_meta` writes `E_TEXTCTRL_Shimmer_Cycles`
  4–12 as the speed knob; on `Shimmer#0` (PRE_2017_7 and Cycles 600.0 frozen) that would be a
  different render's number; check the preview before trusting it on `#0`.

### What code can realize today

- `look_id`: `Shimmer#0` (the gold glitter, every key frozen) and `#1` (the two-beat blink,
  frozen); neither has knobs, so Duty or Cycles off the look go in `settings` as
  `E_SLIDER_Shimmer_Duty_Factor` / `E_TEXTCTRL_Shimmer_Cycles`, and the palette in `palette`.
- `effect_meta`: energy band 2–4, `duration_class="phrase"`, speed knob
  `E_TEXTCTRL_Shimmer_Cycles` 4–12; no direction. Nothing synthesizes the phrase-spaced
  glitter: write a `stack` layer with `role: "accent"`, `look_id: "Shimmer#0"`,
  `render_style: "Per Model Default"`, `palette: ["#000000", "<accent>"]`, and short `groups`
  (the stakes, the cats) so it sits in the gap, not on the whole house.
