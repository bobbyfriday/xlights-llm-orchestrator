---
name: xlo-scenes
description: The scene cookbook and the trigger cookbook for an xLights show brief — when to cast a named cookbook scene (SC-NN) on a section versus designing it freeform, how scene_id + scene_adaptation map the cookbook's archetype rows (G2-HERO, G2-RHYTHM, G0-ALL-LESS-HERO…) onto the layout's real SEM_ groups, and how the brief steers the code-curated beat/trigger layer through pulse_groups, follow_stem, accent_effect and pulse_on. Load during /xlo:design and /xlo:review whenever you fill a section's scene or rhythmic-intent fields.
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

## Casting archetypes onto real groups (`scene_adaptation`)

Cookbook stack tables name display **archetypes**, not groups. In `scene_adaptation` write the
cast as `ARCHETYPE→GROUP[+GROUP]; …` and note any row this layout cannot cast. Every group you
cast must also appear in `target_groups`.

| Cookbook archetype | Usual SEM_ group(s) (`xlo-layout` has the full vocabulary) |
|---|---|
| G0-ALL | `SEM_ALL` |
| G0-ALL-LESS-HERO | `SEM_ALL_LESS_FOCAL` |
| G0-ALL-LESS-HERO-RHYTHM | `SEM_ALL_LESS_FOCAL_RHYTHM` |
| G1-LEFT / G1-RIGHT | `SEM_SIDE_LEFT` / `SEM_SIDE_RIGHT` |
| G2-HERO | `SEM_FOCAL` |
| G2-RHYTHM | `SEM_ARCHES` + `SEM_CANES` + `SEM_MINITREES` (whichever exist) |
| G2-FRAME | `SEM_OUTLINE` (or `SEM_HOUSE` = outline + windows + icicles) |
| G2-ACCENT | `SEM_SNOWFLAKES` + `SEM_SPINNERS` (not `SEM_ACCENTS`, which also holds the rhythm props) |
| G2-CANVAS | the layout's matrix group, by its own name (e.g. `Matrixes`) — only if one exists |
| G9-STROBE-OVERLAY | not a group here; code's climax flashes and `on_top` triggers play that role |

Example: `"scene_id": "SC-01", "scene_adaptation": "G2-HERO→SEM_FOCAL; G2-RHYTHM→SEM_ARCHES+SEM_CANES; G0-ALL-LESS-HERO→SEM_ALL_LESS_FOCAL; (no canvas in this layout)"`.

Only names in `vocab.json` `groups` are targetable; a cast to a group that does not exist is a
validation error on `target_groups`.

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
  exists. Name 2–4 groups to override; prefer `SEM_ARCHES` or the `SEM_SIDE_*` spatial chase.
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
peak's downbeat if you gave none, and an `entrance` moment per detected instrument entrance.
