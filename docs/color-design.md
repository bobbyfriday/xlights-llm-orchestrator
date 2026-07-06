# Color & Palette Design

How this orchestrator should choose colors for a holiday light show — the principles, the
LED constraints, the holiday/occasion palettes, and the open question of **per-section vs.
per-song** palettes. Written to match the project split: **the LLM owns color judgment**
(which palette, which mood), **code owns realization** (palette → settings string) and a
**narrow contrast floor on the rhythm layer only** (see §1.3 for the real scope).

> Scope: this is a design/technique doc. §1 describes current behavior with code references;
> §2–§4 are principles and recommendations; §5 + the appendix are an unbuilt backlog. Sections
> that describe things we *don't have yet* are banner-marked **PROPOSED**.

---

## TL;DR

- **LEDs render hue *contrast* well and subtle tints terribly.** Every palette must span
  hues. "Gold + amber + warm white" is one color on a real display.
- **Today the contrast floor only protects the beats, not the wash.** `ensure_contrast`
  (the 60° rule) runs *only* inside `contrast_anchors`, which feeds the beat/weave/trigger
  alternation pair. The section **wash and effect palettes have no floor at all** — a
  near-monochrome warm section renders as a warm smear. The fix is to floor the section
  palette itself, not just the rhythm layer.
- **Holiday music should wear holiday colors** — but today that's a single prompt nudge for
  *Christmas only*, with no detection and no library for other occasions. We should ship a
  small, LED-safe **occasion palette library** and select from it.
- **Color varies on three axes — song, section, and prop-group — and the fix for clashing is
  to constrain all three to one harmonized show palette with explicit roles** (a dominant +
  its *designated* accent per section), not free per-section choice. Today the song-level
  palette exists in the data model but is **never realized**, and each section picks colors
  quasi-independently — which is exactly why neighbors clash.

---

## 1. How color works today

### 1.1 The data model — nested scopes

`packages/xlights-orchestrator/src/.../show_plan.py`:

| Scope | Field | Status today |
| --- | --- | --- |
| **Song** | `ShowPlan.palette: ShowPalette` (`name`, `colors`, `mapping`) | **Informational only** — shown in the human-readable brief; *never applied to effects* |
| **Prop group** | `GroupMotif.color` (in `ShowPlan.group_motifs`) | Passed to the Generator as *context* (`generate.py:153`, `run.py:143`) and printed in the brief; **not code-realized** |
| **Section** | `SectionPlan.palette: list[str]` | **The operative lever** — what actually gets realized |
| **Cell / layer** | `CellRecipe.palette`, `CompositeLayer.palette` | Default to the section palette when empty |
| **Effect** | `EffectInstruction.palette_colors` | Code copies the section palette here (expanded); a Generator-pinned value wins (feature props) |

So despite song-level *and* per-group palette fields existing, **the section palette is where
all the realized decisions live**, and there is no enforced relationship between a section's
palette and the show palette, the group motifs, or the neighbouring sections.

### 1.2 Who decides — the Director, in one shot

`agents/director.py` → `render_input()` is the entire color brain. In a single call per song
the Director LLM authors the `ShowPalette`, the `group_motifs` colors, *and* every
`SectionPlan.palette`. The current prompt guidance (director.py lines 53–72) already says the
right things:

- *"per-section palette: 3-5 colors INCLUDING a contrast/accent color (not one warm family)"*
- *"LED COLOR REALITY: pixels render hue CONTRAST well and subtle tints terribly — gold +
  amber + warm white reads as ONE color on a real display. Every section palette MUST span
  hues (≥1 cool vs warm anchor)."*
- *"HOLIDAY BIAS: if the song is a Christmas/holiday piece, prefer the traditional RED +
  GREEN + WHITE primary palette with 1–2 accent colors (gold, cool white, ice blue)…"*
- *"FEATURE PROPS POP: … make THOSE props the BRIGHT, high-contrast focal element in a light
  color (white/ice) over a DIFFERENT-hued background bed (e.g. white snowflakes on a blue
  house)."*

Color names must come from a fixed vocabulary (`NAMED_COLORS` in `xlights-core`). Note this is
all *prompt* guidance — the Director is asked to span hues, but nothing downstream checks that
it did (see §1.5).

### 1.3 Realization, and the (narrow) contrast floor — `xlights-core/.../knowledge/colors.py`

How a section's color names become xLights settings, and where contrast is (and isn't)
enforced:

- **Section → effect colors:** `effect_palette(section.palette, effect_type, j)`
  (`pipeline/beats.py:74`) runs `expand_palette` to grow the 3–5 names to up to
  `PALETTE_DEPTH = 5` hexes (light/dark/hue-shift variants so Plasma/Spirals/Bars have enough
  to render), then **rotates** by the effect index `j` so concurrent effects aren't identical.
  Simple effects (On/Off/Strobe/Lightning/Fill) get the first 2 colors; others get the full set.
- **→ settings string:** at placement, `palette_from_colors()` (`editing.py:57`) emits the
  `C_BUTTON_Palette1..8` + `C_CHECKBOX_PaletteN=1` string; if it can't realize, it falls back
  to a mined `palette_id`.
- **The contrast floor is rhythm-only.** `MIN_HUE_SPREAD = 60.0` and `ensure_contrast()`
  (inject the complement of the dominant hue when chromatic colors cluster within 60°) are
  used in exactly one place: inside **`contrast_anchors()`**, which returns the two most
  hue-distant colors. That pair drives the **beat** alternation (`beats.py:316`), the **weave**
  carrier (`weave.py:412`), and **anchor-alternate triggers** (`triggers.py:306`).
  **`effect_palette` / the section wash do NOT call it** — the wash renders whatever the
  Director picked, expanded, with no floor.
- Achromatic colors (saturation < 0.25, e.g. whites/grays) **don't count** toward hue spread —
  correctly, two whites don't contrast. (Consequence: see the degenerate hole in §1.5.)
- **Trigger colors are richer than "the anchor pair."** `triggers.py:326–331`: a trigger's
  `spec.color` may be `lyric` (use the lyric's own color word), `fixed:<color>`, or
  `anchor_alternate` (only this one uses `contrast_anchors`).

Plus `feature_prop_contrast()` (`pipeline/beats.py`): a featured snow/sparkle group is recolored
to the section's **lightest** color at `FEATURE_PROP_BRIGHTNESS = 150` so it pops over the bed.

> `split_palette()` (a base/accent split) exists in `colors.py` but currently has **no call
> sites** — it is not part of the live path. Don't rely on it as if it shapes the show.

### 1.4 The mined palette corpus — `presets/palettes.json`

~hundreds of real palettes mined from `.xsq` files, tagged only **`warm`** / **`cool`** plus
a `count:N`. Used as a *fallback* `palette_id` when the brief's named colors can't be
realized. Many are de-facto Christmas (red/green/white/gold), but **nothing is tagged by
occasion**, so we can't select "a Halloween palette" or "a patriotic palette" from the corpus.

### 1.5 What's missing today

1. **No contrast floor on the wash.** The 60° floor protects only the beat/weave alternation
   pair; the section wash and the multi-color effect palettes use the Director's raw colors. A
   model that picks an all-warm section palette gets an all-warm wash — the floor can't save it.
2. **A degenerate hole even on the beats.** `contrast_anchors` only guarantees contrast when
   the palette has ≥1 *chromatic* color. An all-achromatic section palette (only whites/grays/
   black) has no hue to complement, so it falls back to `(first color, white)` — e.g.
   `(warm white, white)`, which barely contrasts. Rare (the prompt asks for a chromatic
   anchor), but unguarded.
3. **Holiday awareness is Christmas-only and prompt-only.** No detection, no other occasions
   (Halloween, July 4th, Valentine's, Hanukkah, New Year's…), no code enforcement, and the
   "title is not evidence" rule means even an obvious filename is ignored.
4. **The song-level palette and group motifs are never realized.** `ShowPalette` and
   `GroupMotif.color` are decoration / LLM context. There is no "use the show palette as the
   default for sections that don't set one," and no per-group color consistency in code.
5. **No cross-section coherence.** Nothing checks that adjacent sections' palettes relate, or
   that a section's palette is drawn from the show's spine. This is the clashing.
6. **Corpus palettes have no occasion tags**, so the fallback can't be occasion-aware.

---

## 2. Principle: design for the LED, not the screen

> Sourcing: the LED-rendering claims in this section are from common pixel-show practice and
> the project's own `ensure_contrast` rationale — taste/heuristic, **not render-verified here**.
> Treat them like `docs/community-technique.md`'s Tier-2 (forum/taste) claims; the visual
> critic and a render check remain the arbiters.

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
"earth tone." These belong indoors. Several are in `NAMED_COLORS` because the corpus uses
them; the actionable fix is to **prune or tag them "depth-only" in the vocabulary** (§5 #7)
so the Director can't reach for them as a section's load-bearing color in the first place.

### 2.3 Contrast rules of thumb

- **3–4 active hues per section, max.** Beyond that it's visual noise. `PALETTE_DEPTH = 5` is
  the expanded realization size, not a target hue count.
- **Always pair a warm anchor with a cool anchor** (or a color with its complement). The
  60° floor (where it runs) catches the worst cases; *design* for ≥90–120° between your two
  dominant hues.
- **One white is a pop, two whites is a wash.** Use white/ice to make a feature jump, not as
  half the palette.
- **Adjacent hues are the trap, not the goal:** red+orange, blue+teal, blue+purple,
  pink+red+magenta all look like "one slightly-changing color" at distance. They're fine as
  *depth within one role*, never as the contrast pair.

### 2.4 Value and darkness are color tools too

Color isn't only hue. On LEDs, **brightness contrast and unlit space carry as much of the
look as the palette does** — and the project already treats darkness as deliberate (see the
archived `add-intentional-darkness` change and the `WASH_MIN_B/MAX_B` brightness dials).

- **Black is negative space, not a palette color.** Unlit props *frame* the lit ones; a
  section where everything is on at once has no figure/ground. In the appendix, "bed = black"
  means *leave it dark*, not "add black to the palette."
- **Value contrast reads when hue contrast can't.** A bright feature over a dimmed bed of the
  *same* hue still pops (this is exactly what `feature_prop_contrast` exploits) — useful for
  identity palettes (Hanukkah blues, a blue "winter" Christmas) where you don't want a
  competing hue.
- **White-dominant is a legitimate whole-show aesthetic.** Elegant "warm-white with occasional
  color accents" shows are a real style; "every section must span hues" is the default for
  *energetic, colorful* shows, not a universal law. Let the occasion/mood pick.

---

## 3. Principle: holiday music wears holiday colors

> **PROPOSED.** The occasion library below does not exist yet — today only a Christmas prompt
> nudge does (§1.2). This section is the design for §5 #2.

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
| **Halloween** | orange · purple *(+ lime green; leave the bed dark)* | orange↔purple is a great contrast pair; lime = "toxic" accent |
| **Valentine's Day** | red · hot pink · white *(+ magenta/purple)* | ⚠ red/pink/magenta are near-hue — lean on white pops + a purple accent for separation |
| **Independence Day** | red · white · blue | red↔blue hue-distant, white pop — reads great as-is |
| **St. Patrick's Day** | green · gold · white | green↔gold is workable contrast |
| **Thanksgiving / Autumn** | amber · orange · red *(+ deep blue or purple dusk anchor)* | ⚠ the textbook low-contrast palette — **must** add a cool anchor or it's one orange smear |
| **New Year's** | gold · white · silver *(+ a bold pop: blue or magenta)* | ⚠ gold/white/silver are all near-achromatic/warm — the countdown pop needs a real hue |
| **Easter / Spring** | the *saturated* versions of pink, mint→green, lavender→violet, yellow | ⚠ pastels are LED-hostile — use the most saturated form and complement pairs (pink↔green, violet↔yellow); lean on motion + white, not tint |

**The recurring trap:** the "cozy" classic palettes (Victorian Christmas, Thanksgiving,
Valentine's, New Year's, Hanukkah) are exactly the low-contrast ones. The library bakes in the
fix — each ships with a built-in contrast/accent anchor *or* leans on value contrast (§2.4)
for identity palettes — so the occasion look survives the trip to the yard. This is the same
reason the prompt already pushes red+green for Christmas: the tradition happens to be
LED-friendly, and where it isn't, we correct it.

---

## 4. Per-section vs. per-song — the recommendation

Color actually varies on **three axes**, and the data model already has all three (§1.1):

- **Song** — `ShowPalette` (never realized today)
- **Prop group** — `GroupMotif.color` (LLM context only today)
- **Section** — `SectionPlan.palette` (the only one realized)

**Recommendation: one harmonized show palette is the spine; each section selects from it by
*role* (a dominant + a designated accent), not by free subset; prop groups keep a consistent
color identity across the show; a small budget of sections may make a deliberate, flagged
departure.**

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

### Why "draw from the spine" is not enough on its own
A naive version of the fix — "pick 4–6 hue-distant colors as the spine, let each section grab
a subset" — **does not prevent clashing**, because 4–6 *mutually* hue-distant colors by
definition contain clashing pairs. A section that happens to grab gold + magenta from the
spine clashes just as badly. So the spine needs *structure*, not just membership:

1. **Harmonize the spine, don't just spread it.** Build it as a small, designed set: 1–2
   **dominants** + 1 **accent/complement** + neutral **pops** (white/ice). Occasion-seeded
   per §3, or mood-derived for non-holiday songs. This is the appendix's
   primary/accent/pop shape — a designed palette, not "6 maximally-different colors."
2. **Assign roles per section, not free choice.** Each section picks a **dominant** from the
   spine and pairs it with the spine's **designated accent** for that dominant (red→green,
   blue→amber), plus the shared white pop. Variety comes from *which dominant leads* and from
   brightness/motion/effect — not from inventing new hue combinations per section. Adjacent
   sections that share a spine and obey accent-pairing **cannot** produce a clash.
3. **Prop groups hold a color identity.** Realize `GroupMotif.color` so the megatree, arches,
   etc. keep a recognizable treatment across sections — another force toward coherence (and a
   reason a section doesn't need to re-decide everything).
4. **Spend a departure budget deliberately.** ≤1–2 flagged sections may leave the scheme for
   an earned moment: a bridge mood shift, a lyric color word ("the snow turned *red*"), the
   climax white-out.

### The honest trade-off
This *reduces* the per-section surprise on purpose. Some shows want a hard palette flip between
songs or at the drop for "wow," and a strict spine fights that — which is what the departure
budget (and the per-song occasion reseed) is for. The default should be coherence; the
flips should be *chosen*, not the accidental by-product of independent per-section authoring.

This is also a cheap change to the architecture: `ShowPalette` and `GroupMotif.color` already
exist; we mostly have to *realize* them as constraints/defaults instead of decoration.

---

## 5. Proposed changes

Prioritized; each maps to existing code. (Backlog — argue/spec these as OpenSpec changes.)

1. **Floor the section palette, not just the beats.** Run an `ensure_contrast`-style pass on
   `SectionPlan.palette` (or inside `effect_palette`) so the **wash** is hue-spanned too, and
   close the achromatic-fallback hole in `contrast_anchors` (§1.5 #1–2). This is the
   highest-leverage fix — it makes the doc's "every section spans hues" actually true at render.

2. **Realize the show palette + group motifs as defaults + soft constraint.**
   - In `pipeline/run.py`/`generate.py`, where the section palette is copied to instructions:
     if `section.palette` is empty, fall back to `plan.palette.colors`.
   - Snap each section palette toward the show palette (keep colors in/near it by hue; treat
     anything else as the section's one allowed accent), and apply `GroupMotif.color` per
     group so prop identity is consistent. Reuse the hue helpers in `colors.py`.

3. **Ship the occasion palette library** (`xlights-core/.../knowledge/`), each entry a
   harmonized, LED-safe spine with explicit dominant/accent/pop **roles** (the §3 / appendix
   shape — not just a flat color list). The Director selects an occasion and gets the spine as
   a strong default; corpus palettes (`palettes.json`) gain an `occasion:` tag so the
   `palette_id` fallback is occasion-aware too.

4. **Occasion signal — let the user say it, don't guess from the title.** The "title is not
   evidence" rule is right for *lyrics/story*, but the occasion is a legitimate top-level
   input. Add an explicit `--occasion christmas|halloween|patriotic|…|auto` flag (and a brief
   field) that seeds the show palette. `auto` keeps today's behavior (Director infers from
   mood). This avoids silently theming a non-holiday song.

5. **Cross-section coherence QA advisory** (`qa/rules.py`): flag adjacent sections whose
   *dominant* hues clash (large jump with no shared anchor) or whose palette isn't drawn from
   the show palette. Advisory-only at first (like the motion-share check) so the Judge sees it
   without hard-gating; promote to a regen trigger once tuned.

6. **Tighten the authoring prompt** (`director.py`): replace "Christmas bias" with
   "occasion-seeded show palette + per-section dominant/accent **roles**," state the §2.2
   muddy-color blacklist explicitly, and instruct the Director to express section variety
   through emphasis/brightness/motion rather than swapping hue families.

7. **Prune/tag the color vocabulary** (`NAMED_COLORS`): drop or mark the §2.2 muddy colors as
   "depth-only" so they can't be a section's load-bearing color. The vocabulary is the cheapest
   place to enforce the LED-safe set, since the Director may only name colors from it.

8. **Raise contrast as an advisory target (not just the legibility floor).** 60° guarantees
   *legibility*; design wants ≥90–120° between the two dominant hues. Add a second, higher
   threshold the Judge nudges toward, distinct from the hard floor added in #1.

---

## Appendix: occasion palette reference

> **PROPOSED — not yet implemented.** This is the design target for the occasion library
> (§5 #3), not a description of current behavior. Today there is no primary/accent/pop
> structure in code — a section is a flat list of 3–5 names (§1.1).

Harmonized spines using the existing `NAMED_COLORS` vocabulary. **Dominant** colors lead the
look; **accent/pop** is the contrast anchor that keeps it legible; **bed** is how the
background reads (where it says *black* / *dark*, that means leave it unlit — black is not a
palette color, see §2.4).

| Occasion | Dominant 1 | Dominant 2 | Accent / pop | Bed | Watch out |
| --- | --- | --- | --- | --- | --- |
| Christmas — classic | red | green | gold + white | dark | none — this is the reference high-contrast palette |
| Christmas — cool/winter | deep blue | ice blue | cool white | dark | keep one *light* pop or it goes navy-mush |
| Christmas — warm/Victorian | gold | red | green (anchor) + warm white | dark | **without the green anchor it's monochrome warm** |
| Hanukkah | deep blue | ice blue | cool white + silver/gold | dark | blue+white = low contrast; carry it on the 2nd blue *value* + metallic pop |
| Halloween | orange | purple | lime green + white | dark (essential) | great contrast pair; the dark bed is the look |
| Valentine's Day | red | hot pink | white + purple | dark | red/pink near-hue — separate with white + a purple accent |
| Independence Day | red | blue | white | dark | reads great unmodified |
| St. Patrick's Day | green | gold | white (+ lime for a brighter accent) | dark | fine as-is |
| Thanksgiving / Autumn | amber | orange/red | **deep blue or purple** dusk anchor | dark | **must** keep the cool anchor or it's one smear |
| New Year's | gold | white/silver | **blue or magenta** pop | dark | metallics are near-achromatic — the countdown pop needs real hue |
| Easter / Spring | hot pink | green (saturated) | violet + yellow | warm white | use saturated forms; pair complements; lean on motion |
| Generic / mood-driven | mood hue A | mood hue B (≥90° from A) | white pop | dark | no occasion — derive from song mood; enforce the §2.3 hue spread |

> Underneath, the §5 #1 section-palette floor (once built) and `feature_prop_contrast` are the
> safety net; this library raises the *starting* quality so the floor rarely has to intervene.
