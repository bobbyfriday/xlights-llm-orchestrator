# Strobe

Random pixel flashes — and the corpus's only three are black, under five layers, invisible — so the craft is xLights behaviour plus our house rule: peak payoff only, once, ≤ 1 bar.

---

## Corpus facts

> Generated 2026-11-03 from the deduped corpus: **22 community sequences, 14 distinct songs** (xLights 2020.45–2025.08; 0 byte-identical files dropped). 1 sequences / 1 songs use Strobe: **3 placements, 15 overlapping pairs.** Every share carries its breadth (sequences / songs); a habit in one sequence is one sequencer's habit, however many placements it has.
>
> Sources by placements: Light Of Christmas (main) 3.

### Where it is placed

| Prop class | Share | Breadth | Example model names |
|---|---|---|---|
| matrix | 100% | 1 seq / 1 song | Matrix1, Matrix2, P10 |

### Dials observed

Share · breadth per value; `curved` = that key has an active value curve instead of a static value.

| Key | Values |
|---|---|
| `Music` (checkbox) | 0: 100% · 1 seq / 1 song |
| `Number_Strobes` (slider) | 3: 100% · 1 seq / 1 song |
| `Duration` (slider) | 10: 100% · 1 seq / 1 song |
| `Type` (slider) | 1: 100% · 1 seq / 1 song |
| `T_TEXTCTRL_Fadein` | 0.50: 100% · 1 seq / 1 song |
| `T_TEXTCTRL_Fadeout` | 0.25: 100% · 1 seq / 1 song |

### Value curves

| Parameter | Share · breadth | Shapes |
|---|---|---|
| any curve | 0% · 0 seq / 0 songs | |

Most-used exact strings (copy verbatim; `Min`/`Max` are the parameter range, `P*` the real values):

```
```

### Palette habits

Colors per placement: 1: 100%.
Black as a color: 100% · 1 seq / 1 song. Sparkles on: 0% · 0 seq / 0 songs.
Top palettes: #000000 3.

### Duration

Median 3.88 s. 2–4 s 100%.
In beats (3 placements with a beat track): 8 beats 100%.

### Stacking

**100% of placements share the model with at least one concurrent effect (1 seq / 1 song); 100% with three or more (1 seq / 1 song).**

Partner types (pairs · sequences): Pinwheel 6 · 1 · SingleStrand 6 · 1 · Warp 3 · 1.

Above Strobe (partner type, the partner's blend): Pinwheel 6 Normal · SingleStrand 6 Normal · Warp 3 Normal.

Beneath Strobe (partner type, Strobe's own blend over it): .

Recurring full stacks (top → bottom, `*` = the mined effect): Pinwheel > Pinwheel > Warp > SingleStrand > SingleStrand > *Strobe (3).

---

## Craft

### Identity and role

Random pixels flashing on and off, each for a few frames: a spark field, harsher than Twinkle,
not the whole prop blinking (that is Shimmer) and not a flood flash (that is a one-beat white
On). From the corpus, one sequencer's one setting: **Number_Strobes** 3, **Duration** 10,
**Type** 1, **Music** off, fades 0.50 / 0.25. Not from the corpus, xLights' behaviour: Number of
Strobes is how many new flashes start per frame, Strobe Duration how many frames each stays
lit, Strobe Type the shape of each flash (1 a single pixel; the higher types larger), Music ties
the number of flashes to the audio level, and each flash takes a random colour from the
palette.

The corpus has, in effect, **no Strobe**: the three placements are one Light of Christmas verse
(Matrix1 / Matrix2 / P10, 0:11–0:15, 8 beats) with a palette of black only, at the bottom of a
six-layer stack under two Pinwheels, a Warp and two SingleStrands. A black strobe renders
nothing; it is a leftover. So everything below is xLights behaviour plus our house rule, and
labelled so.

Role: **accent**, and the most budgeted one. `xlo-sequencing`: "Strobe is peak-payoff only — the
climax, never a verse hit"; hit effects are ≤ 1 bar; prefer Shockwave for hit-class accents.
`effect_meta` classes it energy 4–5, `duration_class="hit"`. Never a bed, never a carrier.

### Thematic fit

The hard flash. A strobe says *alarm*, *lightning without the bolt*, *the drop*, *the monster is
here*. Halloween: a white strobe on the hero and the stakes for the two beats of the scream, an
orange strobe through the final chorus's last bar, purple + white on the cats as the spell
breaks. Christmas: the last bar of the final chorus, white, on the snowflakes. Against the
alternatives: a one-beat white On is the flood flash the community actually uses; Shockwave is
the community's default hit; Lightning is the storm; Shimmer the glitter. Strobe is for the one
moment that must hurt, and the house rule says once per show, at the peak.

### Anchors (starting points, not a menu)

| Anchor | Settings | Catalog look | Where | Dials to move |
|---|---|---|---|---|
| **The corpus strobe** | Number of Strobes 3, Duration 10, Type 1, Music off, fades 0.50 / 0.25, 8 beats — with a BLACK palette, so invisible | `Strobe#0` (frozen) | Light of Christmas verse 1, Matrix1 / Matrix2 / P10, 0:11–0:15, under Pinwheel ×2, Warp, SingleStrand ×2 | the palette (white); the length (≤ 1 bar) |
| **Peak strobe** | the same dials with a white palette, 1–2 beats, on top of the stack | `Strobe#0` + `palette: ["#FFFFFF"]` | not from the corpus: the house rule's one allowed use | Number of Strobes up for density; Music on so the flashes follow the level |
| **Coloured spark field** | Number of Strobes 3, Duration 10, Type 1, two or three palette colours, ≤ 1 bar | `Strobe#0` + palette | not from the corpus: each flash takes a random palette colour | |

**Dials** — pick from the observed values, then move one:

| Dial | Sane range | Moving it | Corpus picks |
|---|---|---|---|
| Number_Strobes | 3 (slider up for density) | new flashes per frame | 3 (one seq) |
| Duration | 10 | frames each flash stays lit | 10 (one seq) |
| Type | 1 (1–4 exist) | the flash shape: 1 a pixel | 1 (one seq) |
| Music | off / on | flashes follow the audio level | off (one seq) |
| Palette | white · 2–3 colours · never black alone | random per flash | black (one seq — invisible) |
| Fades | 0.50 / 0.25 | the catch and the cut | one seq |

**How to permute.** Barely: the dial that matters is *when*. One strobe per show at the peak,
white, ≤ 1 bar, on the hero or the whole house. If a second is wanted, change the colour to the
section's accent and halve the length; a third is a fault.

### Layering recipes

The corpus stack is a black strobe beneath five layers, which shows nothing. The rest is not
from the corpus, built from the blend semantics in SKILL.md:

| Name | Stack (top → bottom) | Blend | Use |
|---|---|---|---|
| **Strobe over the peak stack** | Strobe (white) · the chorus stack | Normal | the black between flashes is transparent, so the chorus shows and the sparks punch through |
| **Strobe as a brightness gate** | Strobe `Brightness` · a flood On or Color Wash | Brightness | the fill flashes only where the sparks land: a flickering flood |
| **Strobe with the bolt** | Strobe · Lightning · bed | Normal | the storm's flash field with the bolt, two beats at most |
| **Strobe over black** | Strobe · Off | Normal | a dark house with white sparks for the breakdown before the drop |

### Value curves

None observed (0 of 3), and none advised; Music on is the only envelope a strobe needs.

### Prop fit and render style

The corpus: matrices only (one sequence, and invisible). Not from the corpus: it reads on
anything dense (a matrix, the tree, the stakes `Per Model Default`) and is lost on a sparse line.
On the Halloween layout: the hero matrix and the stakes for the scream; `SEM_ALL` for the drop.
Not the video panel.

### Timing

The corpus holds its black strobe 8 beats, which is not a model. The house rule: ≤ 1 bar; one or
two beats is the right length for a flash that hurts. Fades 0.50 / 0.25 in the corpus; none for
a peak hit. Space it so the viewer sees it once.

### Exemplars

| Where | Stack top → bottom | Why it works |
|---|---|---|
| Light of Christmas.xsq 0:11–0:15, verse 1, Matrix1 (also Matrix2, P10) | Pinwheel · Pinwheel · Warp · SingleStrand · SingleStrand · Strobe Number of Strobes 3, Duration 10, Type 1, fades 0.50 / 0.25, black, 8 beats | it does not: a black strobe under five layers renders nothing. It is the only Strobe in 22 sequences, which is itself the lesson |

### Anti-patterns

- **Strobe every beat.** Our pipeline can do this: a brief whose `accent_effect` is Strobe, or
  the hit-class rotation landing on it, fires it on every accent beat. Name Shockwave as the
  accent and put Strobe in a `stack` layer at the peak only.
- **Strobe in a verse.** The house rule.
- **Strobe as a bed or a carrier.** Eight beats of sparks is a fault on the street; the corpus's
  8-beat one is invisible.
- **A black palette.** The corpus's; it renders nothing. White, or the section's colours.
- **Strobe plus Shockwave plus Lightning on the same hit.** One high-attention feature per
  moment.
- **Strobe on a sparse line.** Three flashes a frame on a 50-pixel arch is a glitch.

### What code can realize today

- `look_id`: `Strobe#0` only (every key frozen, no knobs; the picker has nothing else).
  The palette goes in the layer's `palette` (`["#FFFFFF"]`); a denser field or Music on goes in
  `settings` as `E_SLIDER_Number_Strobes`, `E_SLIDER_Strobe_Duration`,
  `E_SLIDER_Strobe_Type`, `E_CHECKBOX_Strobe_Music`.
- `effect_meta`: energy band 4–5, `duration_class="hit"` (in `DURATION_HIT`); no speed, no
  direction. Nothing enforces the once-per-show budget in code; it is the reviewer's rule.
  Write it as the top `stack` layer with `role: "accent"`, `look_id: "Strobe#0"`,
  `cell_beats: 0`, on a section cut to the peak's last bar, and nowhere else.
