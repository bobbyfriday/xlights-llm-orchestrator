# Color & Palette Design

How this orchestrator should choose colors for a holiday light show — the principles, the
LED constraints, the holiday/occasion palettes, and the open question of **per-section vs.
per-song** palettes. Written to match the project split: **the LLM owns color judgment**
(which palette, which mood), **code owns realization and the safety floor** (hue-contrast,
feature-prop pop, palette → settings string).

> Scope: this is a design/technique doc. It describes the current behavior accurately and
> then makes recommendations. Items under [Proposed changes](#5-proposed-changes) are not yet
> built — they're the backlog this doc argues for.

---

## TL;DR

- **LEDs render hue *contrast* well and subtle tints terribly.** Every palette must span
  hues. "Gold + amber + warm white" is one color on a real display. This floor already
  exists in code (`ensure_contrast`, 60° minimum spread) — we should lean on it harder and
  stop letting the LLM author near-monochrome warm palettes in the first place.
- **Holiday music should wear holiday colors** — but today that's a single prompt nudge for
  *Christmas only*, with no detection and no library for other occasions. We should ship a
  small, LED-safe **occasion palette library** and select from it.
- **Color should be per-song *and* per-section — as theme-and-variation, not free choice
  per section.** Pick one coherent **show palette** (the spine), then let each section draw a
  *subset/emphasis* from it, with a small budget of deliberate departures for special
  moments. This is the fix for clashing: sections can't clash if they share a pre-harmonized
  vocabulary. Today the song-level palette exists in the data model but is **never realized** —
  each section picks colors quasi-independently, which is exactly why neighbors clash.

---

## 1. How color works today

### 1.1 The data model — three nested scopes

`packages/xlights-orchestrator/src/.../show_plan.py`:

| Scope | Field | Status today |
| --- | --- | --- |
| **Song** | `ShowPlan.palette: ShowPalette` (`name`, `colors`, `mapping`) | **Informational only** — shown in the human-readable brief; *never applied to effects* |
| **Section** | `SectionPlan.palette: list[str]` | **The operative lever** — what actually gets realized |
| **Cell / layer** | `CellRecipe.palette`, `CompositeLayer.palette` | Default to the section palette when empty |
| **Effect** | `EffectInstruction.palette_colors` | Code copies the section palette here (expanded); a Generator-pinned value wins (feature props) |

So despite a song-level palette field existing, **the section palette is where all the real
decisions live**, and there is no enforced relationship between a section's palette and the
show palette — or between one section and the next.

### 1.2 Who decides — the Director, in one shot

`agents/director.py` → `render_input()` is the entire color brain. In a single call per song
the Director LLM authors the `ShowPalette` *and* every `SectionPlan.palette`. The current
prompt guidance (director.py lines 53–72) already says the right things:

- *"per-section palette: 3-5 colors INCLUDING a contrast/accent color (not one warm family)"*
- *"LED COLOR REALITY: pixels render hue CONTRAST well and subtle tints terribly — gold +
  amber + warm white reads as ONE color on a real display. Every section palette MUST span
  hues (≥1 cool vs warm anchor)."*
- *"HOLIDAY BIAS: if the song is a Christmas/holiday piece, prefer the traditional RED +
  GREEN + WHITE primary palette with 1–2 accent colors (gold, cool white, ice blue)…"*
- *"FEATURE PROPS POP: … make THOSE props the BRIGHT, high-contrast focal element in a light
  color (white/ice) over a DIFFERENT-hued background bed (e.g. white snowflakes on a blue
  house)."*

Color names must come from a fixed vocabulary (`NAMED_COLORS` in `xlights-core`).

### 1.3 The code safety floor — `xlights-core/.../knowledge/colors.py`

This is the strong part of the system. Code enforces an LED-legibility floor regardless of
what the LLM picks:

- **`MIN_HUE_SPREAD = 60.0`** — a palette whose chromatic colors sit within 60° of hue
  *reads as one color* on pixels.
- **`ensure_contrast(colors)`** — if the palette's hue spread is under the floor, inject the
  **complement** of the dominant hue so there's always a real contrast anchor.
- **`contrast_anchors(colors)`** — the two most hue-distant colors, used as the beat-to-beat
  alternation pair so rhythm reads.
- **`split_palette` / `expand_palette`** — base-vs-accent split for beats; grow a thin
  2-color brief to `PALETTE_DEPTH = 5` with light/dark/hue-shift variants so multi-color
  effects (Plasma, Spirals, Bars) render as intended.
- Achromatic colors (saturation < 0.25, e.g. whites/grays) **don't count** toward hue
  spread — correctly, two whites don't contrast.

Plus `feature_prop_contrast()` (pipeline/beats.py): a featured snow/sparkle group is recolored
to the section's **lightest** color at `FEATURE_PROP_BRIGHTNESS = 150` so it pops over the bed.

### 1.4 The mined palette corpus — `presets/palettes.json`

~hundreds of real palettes mined from `.xsq` files, tagged only **`warm`** / **`cool`** plus
a `count:N`. Used as a *fallback* `palette_id` when the brief's named colors can't be
realized. Many are de-facto Christmas (red/green/white/gold), but **nothing is tagged by
occasion**, so we can't select "a Halloween palette" or "a patriotic palette" from the corpus.

### 1.5 What's missing today

1. **Holiday awareness is Christmas-only and prompt-only.** No detection, no other occasions
   (Halloween, July 4th, Valentine's, Hanukkah, New Year's…), no code enforcement, and the
   "title is not evidence" rule means even an obvious filename is ignored.
2. **The song-level palette is never realized.** `ShowPalette` is decoration. There is no
   "use the show palette as the default for sections that don't set one."
3. **No cross-section coherence.** Nothing checks that adjacent sections' palettes relate, or
   that a section's palette is drawn from the show's spine. This is the clashing.
4. **Corpus palettes have no occasion tags**, so the fallback can't be occasion-aware.

---

## 2. Principle: design for the LED, not the screen

A pixel string is not a monitor. Two facts drive everything:

1. **Saturated, hue-distant colors read; tints and muddy colors don't.** On a screen, "antique
   gold vs. champagne vs. warm white" is three colors. On a 12mm node 60 ft away at night
   it's one warm smear. The viewer reads **hue jumps** (red→green, blue→amber) far more than
   lightness or saturation nuance.
2. **Color mixing on RGB nodes is additive and crude.** Browns, olives, dusty mauves, and
   most pastels either wash to white-ish or read as a dim dirty version of a primary. They are
   "screen colors," not "yard colors."

### 2.1 The LED-safe color set (prefer these)

From the existing `NAMED_COLORS` vocabulary, the reliably-readable ones:

- **Reds:** red, crimson, candy red (avoid dark red as a *primary* — fine as depth)
- **Oranges/Golds:** orange, amber, gold, sunburst orange
- **Yellows:** yellow (use sparingly — blooms/halates on dense props)
- **Greens:** green, emerald, forest green, lime green (lime = strong "toxic" accent)
- **Cyans/Teals:** cyan, turquoise, teal
- **Blues:** blue, deep blue, royal blue, ice blue (ice blue = winter signature)
- **Purples:** purple, violet, royal purple, indigo
- **Magenta/Pink:** magenta, hot pink (pink reads, but as a *light magenta*)
- **Whites:** white, warm white, cool white — as **accents/pops**, never as a "color"

### 2.2 The muddy-color blacklist (avoid as primaries)

bronze, copper, champagne, peach, lavender (as a primary), mint, silver/gray as a *hue*,
burgundy/dark-red as a *primary*, and anything the eye would call "pastel," "dusty," or
"earth tone." These belong indoors. (Several are in `NAMED_COLORS` because the corpus uses
them — keep them available, but the Director should not reach for them as a section's load-
bearing color.)

### 2.3 Contrast rules of thumb

- **3–4 active hues per section, max.** Beyond that the contrast logic floors out and it's
  visual noise. `PALETTE_DEPTH = 5` is the expanded realization size, not a target hue count.
- **Always pair a warm anchor with a cool anchor** (or a color with its complement). The
  60° floor catches the worst cases; *design* for ≥90–120° between your two dominant hues.
- **One white is a pop, two whites is a wash.** Use white/ice to make a feature jump, not as
  half the palette.
- **Adjacent hues are the trap, not the goal:** red+orange, blue+teal, blue+purple,
  pink+red+magenta all look like "one slightly-changing color" at distance. They're fine as
  *depth within one role*, never as the contrast pair.

---

## 3. Principle: holiday music wears holiday colors

This is a holiday-show tool; the occasion is the strongest prior we have on color, and it's
almost free contrast because the traditional holiday palettes are *already* hue-distant
(red↔green, orange↔purple, red↔blue).

The recommendation: a small **occasion palette library** (LED-safe, pre-harmonized), selected
by occasion, with the Director still free to depart when a song's mood clearly overrides
(a melancholy Christmas ballad isn't bright red/green). See the
[reference table](#appendix-occasion-palette-reference) for the full set; the headlines:

| Occasion | Spine (LED-safe) | Notes |
| --- | --- | --- |
| **Christmas — classic** | red · green · white *(+ gold)* | red↔green is the canonical high-contrast pair |
| **Christmas — winter/cool** | deep blue · ice blue · cool white *(+ white pop)* | "icy" look; overlaps Hanukkah |
| **Christmas — warm/Victorian** | warm white · gold · red *(+ a green anchor)* | ⚠ all-warm without the green = the monochrome trap |
| **Hanukkah** | deep blue · ice blue · cool white *(+ silver/gold pop)* | ⚠ blue+white alone is low-contrast (white is achromatic) — needs the second blue *value* + a metallic pop |
| **Halloween** | orange · purple *(+ lime green, black bed)* | orange↔purple is a great contrast pair; lime = "toxic" accent |
| **Valentine's Day** | red · hot pink · white *(+ magenta/purple)* | ⚠ red/pink/magenta are near-hue — lean on white pops + a purple accent for separation |
| **Independence Day** | red · white · blue | red↔blue hue-distant, white pop — reads great as-is |
| **St. Patrick's Day** | green · gold · white | green↔gold is workable contrast |
| **Thanksgiving / Autumn** | amber · orange · red *(+ deep blue or purple dusk anchor)* | ⚠ the textbook low-contrast palette — **must** add a cool anchor or it's one orange smear |
| **New Year's** | gold · white · silver *(+ a bold pop: blue or magenta)* | ⚠ gold/white/silver are all near-achromatic/warm — the countdown pop needs a real hue |
| **Easter / Spring** | the *saturated* versions of pink, mint→green, lavender→violet, yellow | ⚠ pastels are LED-hostile — use the most saturated form and complement pairs (pink↔green, violet↔yellow); lean on motion + white, not tint |

**The recurring trap:** the "cozy" classic palettes (Victorian Christmas, Thanksgiving,
Valentine's, New Year's, Hanukkah) are exactly the low-contrast ones. The library bakes in the
fix — each ships with a built-in contrast/accent anchor — so the occasion look survives the
trip to the yard. This is the same reason the prompt already pushes red+green for Christmas:
the tradition happens to be LED-friendly, and where it isn't, we correct it.

---

## 4. Per-section vs. per-song — the recommendation

**Recommendation: both, structured as theme-and-variation. One song-level *show palette* is
the spine; each section draws a subset/emphasis from it; a small budget of sections may make a
deliberate, flagged departure.**

### Why not per-song only
The whole reason sections exist is dynamics and variety. A single fixed palette for the whole
song goes flat — verse and chorus and bridge should *feel* different, and color is a primary
lever for that.

### Why not per-section-only (today's behavior)
Each `SectionPlan.palette` is authored quasi-independently. Even with a shared `concept`
string, nothing constrains section 3's colors to relate to section 2's or to a global anchor.
Result: neighbors clash (a warm gold verse slamming into a magenta/cyan chorus), and the show
reads as a sequence of unrelated looks rather than one designed piece. **This is the clashing
the request is about.**

### Why theme-and-variation
Pick **one coherent show palette of ~4–6 LED-safe, hue-distant colors that are designed to
work together** (occasion-seeded per §3, or mood-derived for non-holiday songs). Then each
section expresses *that* palette differently:

- **different dominant + accent** drawn from the spine (chorus leads on red w/ green accent;
  verse leads on deep blue w/ ice-white feature),
- **different brightness, motion, and effect** — which is where most of the per-section
  *contrast* should come from anyway,
- **a small departure budget** (e.g. ≤1–2 sections) for an earned moment: the bridge mood
  shift, a lyric color word ("the snow turned *red*"), the climax white-out.

Because every section pulls from a pre-harmonized set, **adjacent sections cannot clash** —
they're variations on one chord, not different songs. Variety is preserved through emphasis +
motion + brightness, which read better on LEDs than raw hue-swaps anyway.

This is also the cheapest change to the existing architecture: the `ShowPalette` field already
exists; we just have to *realize* it as the constraint/default instead of decoration.

---

## 5. Proposed changes

Prioritized; each maps to existing code. (Backlog — argue/spec these as OpenSpec changes.)

1. **Realize the show palette as the section default + soft constraint.**
   - In `pipeline/run.py`, where the section palette is copied to instructions: if
     `section.palette` is empty, fall back to `plan.palette.colors` instead of nothing.
   - Add a code pass that *snaps* each section palette toward the show palette: keep colors
     that are in (or near, by `_hue_dist`) the show palette; treat anything else as the
     section's one allowed accent. This makes "draw from the spine" enforceable, not just
     hoped-for. Reuse the hue helpers in `colors.py`.

2. **Ship the occasion palette library** (`xlights-core/.../knowledge/`), each entry a
   pre-harmonized, LED-safe spine + accent (the §3 / appendix table). The Director selects an
   occasion and gets the spine as a strong default; corpus palettes (`palettes.json`) gain an
   `occasion:` tag so the `palette_id` fallback is occasion-aware too.

3. **Occasion signal — let the user say it, don't guess from the title.** The "title is not
   evidence" rule is right for *lyrics/story*, but the occasion is a legitimate top-level
   input. Add an explicit `--occasion christmas|halloween|patriotic|…|auto` flag (and a brief
   field) that seeds the show palette. `auto` keeps today's behavior (Director infers from
   mood). This avoids silently theming a non-holiday song.

4. **Cross-section coherence QA advisory** (`qa/rules.py`): flag adjacent sections whose
   *dominant* hues clash (large jump with no shared anchor) or whose palette isn't drawn from
   the show palette. Advisory-only at first (like the motion-share check) so the Judge sees it
   without hard-gating; promote to a regen trigger once tuned.

5. **Tighten the authoring prompt** (`director.py`): replace "Christmas bias" with
   "occasion-seeded show palette + per-section emphasis," state the §2.2 muddy-color blacklist
   explicitly, and instruct the Director to express section variety through
   emphasis/brightness/motion rather than swapping hue families.

6. **(Optional) Raise the contrast floor for primaries.** 60° guarantees *legibility*; design
   targets ≥90–120° between the two dominant hues. Consider a second, higher threshold that's
   an advisory (not the hard floor) so the Judge nudges toward bolder separation.

---

## Appendix: occasion palette reference

LED-safe spines using the existing `NAMED_COLORS` vocabulary. "Accent/pop" is the
contrast anchor that keeps the look legible in the yard; "bed" is the recommended background.

| Occasion | Primary 1 | Primary 2 | Primary 3 | Accent / pop | Bed | Watch out |
| --- | --- | --- | --- | --- | --- | --- |
| Christmas — classic | red | green | white | gold | black | none — this is the reference high-contrast palette |
| Christmas — cool/winter | deep blue | ice blue | cool white | white | black | keep one *light* pop or it goes navy-mush |
| Christmas — warm/Victorian | warm white | gold | red | green | black | **without the green anchor it's monochrome warm** |
| Hanukkah | deep blue | ice blue | cool white | silver/gold | black | blue+white = low contrast; the 2nd blue value + metallic pop carry it |
| Halloween | orange | purple | lime green | white | black | great contrast pair; black bed is essential |
| Valentine's Day | red | hot pink | white | purple | black | red/pink near-hue — separate with white + purple |
| Independence Day | red | white | blue | white | black | reads great unmodified |
| St. Patrick's Day | green | gold | white | white | black | fine; add lime for a brighter accent |
| Thanksgiving / Autumn | amber | orange | red | deep blue *or* purple | black | **must** keep the cool anchor or it's one smear |
| New Year's | gold | white | silver | blue *or* magenta | black | metallics are near-achromatic — the pop needs real hue |
| Easter / Spring | hot pink | green (sat.) | violet | yellow | warm white | use saturated forms; pair complements; lean on motion |
| Generic / mood-driven | — | — | — | — | — | derive from song mood; enforce ≥90° between the two dominants |

> All entries assume the code floor (`ensure_contrast`, feature-prop pop) still runs underneath
> — the library raises the *starting* quality; the floor is the safety net.
