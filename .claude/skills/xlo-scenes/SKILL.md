---
name: xlo-scenes
description: The scene cookbook and the trigger cookbook for an xLights show brief — when to cast a named cookbook scene (SC-NN) on a section versus designing it freeform, how scene_id + scene_cast (+ scene_adaptation prose) map the cookbook's archetype rows (G2-HERO, G2-RHYTHM, G0-ALL-LESS-HERO…) onto the layout's real SEM_ groups and what code realizes from the cast stack, the default casting by role, and how the brief steers the code-curated beat/trigger layer through pulse_groups, follow_stem, accent_effect and pulse_on. Load during /xlo:design and /xlo:review whenever you fill a section's scene or rhythmic-intent fields.
---

# xlo-scenes

Two hand-editable cookbooks at the repo root. Open them; do not recite them.

| Decision | Read |
|---|---|
| Which named scene fits a section (musical slot, energy band 1–5, stack table, escalation, failure modes) | `xlights-scene-cookbook.md` §3–§7 (SC-01…SC-19), §7b composite stacks |
| The archetype group vocabulary the scenes are written against | `xlights-scene-cookbook.md` §2 |
| What accents code places automatically, and on what | `xlights-trigger-cookbook.md` (each `## ` block is one trigger) |

## Scene or freeform?

- Cast a scene when its **musical slot** and **energy band** match the section. SC-01 (the
  Standard Stack) is the default for ordinary verses and choruses; about 60% of a song lives there.
- Spend showpieces only where they are earned: SC-04 Drop Formula ≤ 2 per song, SC-06 Persistent
  Trail Finale on the finale, SC-05 Shaped Reveal on a title-lyric moment with a matrix.
- Repeated choruses follow SC-14 (Escalating Chorus Series): chorus 1 reduced, final chorus
  maximal. Give the recurring sections the same `label` so code escalates them.
- Quiet moments: SC-09 Snowfall Hush, SC-19 Ripple Reflections, SC-18 Ember Glow.
- Builds: SC-07 Additive Build, SC-16 Radiant Fan Bloom. Grooves: SC-08 Brightness Envelope.
- Set `scene_id` to `""` (freeform) only when no scene fits; then the section's `effect_family`,
  `effect_types` and fabric carry the look alone.
- `scene_id` must be one of `vocab.json` `scene_ids` (the validator checks it).

## Casting archetypes onto real groups (`scene_cast` + `scene_adaptation`)

Cookbook stack tables name display **archetypes**, not groups. Two section fields carry the cast:

- `scene_cast` — the machine cast, `{"ARCHETYPE": "GROUP", …}`: one real group per archetype
  row id, exactly as the scene's stack table spells it (`G2-HERO`, `G2-RHYTHM`,
  `G0-ALL-LESS-HERO`, …). This is what code realizes. Values must be `vocab.json` `groups`
  (validation error, with the allowed list); a key that is not one of the scene's rows is a
  warning and is ignored; a `scene_cast` with no `scene_id` is ignored (warning).
- `scene_adaptation` — prose for the reader: the same cast in words plus what this layout cannot
  cast (`"G2-HERO→SEM_FOCAL; G2-RHYTHM→SEM_ARCHES; (no canvas in this layout)"`). Code never
  parses it.

Screens under a hero scene: most scenes have no G2-CANVAS row, so the matrixes (`SEM_CANVAS`) get
nothing from the cast. Name `SEM_CANVAS` in `target_groups` and code gives it ONE layer of the
hero's feature effect, drawn per matrix (`scenes._canvas_echo`) — a calmer echo, not the hero's
whole stack. Leave it out and the screens only take the beds.

Every group you cast should also appear in `target_groups` (the coverage and rhythm layers read
`target_groups`; the scene rows themselves are placed from `scene_cast`).

| Cookbook archetype | Default cast (when `scene_cast` is `{}`), first that exists | Alternatives you may cast |
|---|---|---|
| G0-ALL | `SEM_ALL` | |
| G0-ALL-LESS-HERO | `SEM_ALL_LESS_FOCAL`, else `SEM_BAND_GROUND`, else `SEM_ALL` | any broad group |
| G0-ALL-LESS-HERO-RHYTHM | `SEM_ALL_LESS_FOCAL_RHYTHM`, else as G0-ALL-LESS-HERO | |
| G1-LEFT / G1-RIGHT | `SEM_SIDE_LEFT` / `SEM_SIDE_RIGHT` | |
| G2-HERO | `SEM_FOCAL` | |
| G2-RHYTHM | the section's rhythm pool, first group (`pulse_groups`, else the rhythm props among `target_groups`), else `SEM_ARCHES` → `SEM_CANES` → `SEM_MINITREES` → `SEM_STAKES` → `SEM_SIDE_*` | one of `SEM_ARCHES`, `SEM_CANES`, `SEM_MINITREES` |
| G2-FRAME | `SEM_OUTLINE`, else `SEM_HOUSE` (outline + windows + icicles) | |
| G2-ACCENT | `SEM_SNOWFLAKES`, else `SEM_SPINNERS`, else `SEM_CHARACTERS` (not `SEM_ACCENTS`, which also holds the rhythm props) | |
| G2-CANVAS | `SEM_CANVAS`, else the group whose name contains "matrix" (e.g. `Matrixes`), else uncast | |
| G9-STROBE-OVERLAY | never cast: code's climax flashes and `on_top` triggers play that role | |

A row casts to **one** group. To spread G2-RHYTHM over arches + canes, cast it to one and name
the other in `pulse_groups` — the beat layer and the fabric walk the pool. An archetype the
layout cannot cast (no matrix for G2-CANVAS) simply drops its rows.

Example: `"scene_id": "SC-01", "scene_cast": {"G2-HERO": "SEM_FOCAL", "G2-RHYTHM": "SEM_ARCHES", "G0-ALL-LESS-HERO": "SEM_ALL_LESS_FOCAL"}, "scene_adaptation": "hero on the mega tree, arches drum, the rest of the yard glows under it; no canvas in this layout"`.

### What code realizes from a cast scene (`pipeline/scenes.py`)

The scene's stack table **replaces** the generic one-row-per-group base layer for that section;
everything downstream (bed, fabric, phrase gesture, accents, composites, flashes) still runs over
it. Per stack row, one section-spanning effect on the cast group:

- `Layer` `L1…Ln` → instruction layer `n−1` (cookbook L1 is the top, layer 0); a blank Layer is
  a single layer. A blank Row cell carries the archetype of the row above (the hero's 3-layer
  stack).
- `Blend` → the xLights layer method (`Max`, `Average`, `1 is Mask`, `Subtractive`, …); `Normal`
  is left unset.
- A brightness in the Effect cell (`Color Wash 30–40%` → 35 %, `25%`) → a constant brightness;
  the phrase-dynamics curve (rising swells, falling decays) shapes around that level instead of
  the energy wash level.
- `Render style` (`Default (canvas)`, `Per Model`) → the buffer style; blank → the per-effect
  fallback.
- `*Feature effect*` (and "Any …") placeholders take the section's `effect_family` — that is
  where your choice of hero effect goes. Other rows use the first effect the cell names
  (`Fast Spirals or Pinwheel` → Spirals); a row naming no catalog-backed effect (Text, Shape
  with no looks) is skipped.
- Colors: the section `palette`, rotated per row; recurring labels keep the same order.
- Cast rows are exempt from the energy coverage gate (the scene is the coverage decision);
  gesture/rest still cut to ≤ 2 groups. The code's own ensemble bed stands down when the scene
  beds the same group. Long cellable rows (`Single Strand chase on beat`) are still chopped into
  2-bar cells by the duration pass, and the occlusion guard still sinks a plain Normal wash under
  the features it shares a group with.
- Timeline scenes (SC-04's `Phase` table) cast only the final phase (the release body); an `Off`
  row is never cast section-spanning — the blackout and flash are code's transitions and climax
  flash. Prose-only scenes (SC-09, SC-10, SC-11, SC-12, SC-13, SC-14, SC-18, SC-19) have no
  table to cast; they realize as freeform from `effect_family` / `effect_types` / `fabric`, so
  write those fields to match the scene's prose.

Composite stacks (§7b: kaleidoscope, swirl, ember, bloom) are **not** brief fields: code drops one
curated stack on the hero at the peak. Don't try to request one.

## Triggers are curated by code; the brief only steers them

`xlights-trigger-cookbook.md` declares each trigger's detector, effect, render, eligibility,
rarity and color; `pipeline/triggers.py` finds the events in the analysis and places them. You
never list triggers in the brief. To change what fires, edit the cookbook (a `- field: value`
line), not the brief.

What the brief's rhythmic-intent fields do (`pipeline/beats.py`):

- `pulse_groups` — the groups that walk the **metric ring** (one prop family per beat of the bar).
  Default ring: `SEM_ARCHES` → `SEM_CANES` → `SEM_MINITREES` → `SEM_SNOWFLAKES`, filtered to what
  exists; the layout manifest ranks in other families it has (e.g. `SEM_STAKES`). Name 2–4 groups to override; prefer `SEM_ARCHES` or the `SEM_SIDE_*` spatial chase.
  Naming any `pulse_groups` also makes a quiet section rhythmic (it opts into the beat layer and
  the fabric), so leave it empty for a still section.
- `follow_stem` — whose onsets the **hero** (`SEM_FOCAL`) follows. Default: the section's
  most-onset melodic stem (guitar / piano / vocals). Must be one of `vocab.json` `stems`.
- `accent_effect` — the beat-accent effect on the ring. Default `On`; any placeable type works,
  non-placeable falls back to `On`. Hit-class punctuation on downbeats already uses Shockwave on
  the sparkle props; don't put Strobe here.
- `pulse_on` — `"beat"` or `"onset"`. Validated today; the beat layer currently always grids the
  ring to beats and the hero/sparkle to real onsets, so treat this as advisory intent.

Also from the brief, not the cookbook: `key_moments` of kind `climax` / `accent` / `drop` / `hit`
become a short white flash on `SEM_ALL` (at most 8). Code adds its own `climax` moment at the
peak's downbeat if you gave none, and an `entrance` moment per detected instrument entrance. A
`key_moment` of kind `lyric` with a `text` puts that lyric line on the matrix (see `xlo-brief`,
Key moments) — SC-05's "Text (the lyric)" row is realized this way, not from the scene table.
