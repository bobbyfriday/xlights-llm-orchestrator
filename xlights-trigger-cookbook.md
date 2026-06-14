# xLights Trigger Cookbook

> **Hand-editable.** This file defines *curated trigger effects* — "when X happens in the music,
> do Y" accents the orchestrator places sparingly over the woven show. Edit freely: tune a
> threshold, change an effect or color, enable/disable a trigger, or add a new one that reuses an
> existing **detector**. A new detector (new way to *find* events) needs a small code addition in
> `pipeline/triggers.py`; everything else is just markdown here.
>
> Each trigger is a `## ` block of `- field: value` lines. Unknown detectors or bad fields are
> skipped (logged), never fatal. Fields:
>
> - **detector** — what finds the events: `guitar_solo` | `drum_onsets` | `stem_onsets` | `lyric_color` | `instrument_entrance`
>   (a "big moment" is just `drum_onsets` with `magnitude: top:<low pct>` + `render: whole_house`)
> - **effect** — the xLights effect to place (e.g. `Lightning`, `Shockwave`)
> - **render** — `per_model` (each prop, scaled to it) | `whole_house` (one gesture across the layout)
> - **sections** — eligibility: `any` | `drum_prominent` | `stem_prominent` (the trigger's `stem` is prominent) | `sparse_beat` (strong beat, low overall energy) | `has_guitar_solo` | `peak`
> - **groups** — per_model target pool: `rhythm` (arches/canes/mini-trees) | `accents` (snowflakes/spinners) | `focal`
> - **stem** — for `stem_onsets`/`stem_prominent`: which instrument drives it — `drums` (default) | `bass` | `piano` | `guitar` | `vocals` | `other`
> - **select** — `rotate` (only a rotated SUBSET of eligible sections — keeps it sparse) | `all`
> - **density** — max events per selected section (`per_onset` = every qualifying hit)
> - **magnitude** — event filter: `any` | `top:<pct>` (e.g. `top:5` = strongest 5%)
> - **color** — `anchor_alternate` (two contrast colors, alternating) | `lyric` | `section` | `fixed:<name>`
> - **direction** — `none` | `out` | `in` | `alternate` (out/in per successive event)
> - **enabled** — `true` | `false`

## Guitar Solo Lightning
- detector: guitar_solo
- effect: Lightning
- render: per_model
- sections: has_guitar_solo
- select: all
- density: per_onset
- magnitude: any
- color: section
- direction: none
- enabled: true

## Big Moment Shockwave
# DEFERRED: a whole-house shockwave layered over the lit fabric can't read (no contrast, and
# SEM_ALL renders under every other group). The real version is a "punch" — briefly clear the
# fabric and sweep the gesture through the cleared space. Disabled until that's built.
- detector: drum_onsets
- effect: Shockwave
- render: whole_house
- sections: any
- select: all
- density: 10
- magnitude: top:6
- color: fixed:white
- direction: out
- enabled: false

## Drum Shockwaves on Accents
# Radiating shockwaves on the ACCENT props (snowflakes/spinners) on each drum hit — but ONLY in
# 'sparse_beat' sections: a strong beat with little else going on (the quiet intro/verse), where
# a shockwave has empty space and a clear prop to read against. In a busy chorus it'd be lost.
# (Modeled on the user's hand-authored 0:30–0:44 edit.)
- detector: drum_onsets
- effect: Shockwave
- render: per_model
- groups: accents
- sections: sparse_beat
- select: all
- density: per_onset
- magnitude: any
- color: anchor_alternate
- direction: out
- enabled: true

## Piano Note Chase
# The piano melody walks the props: a bright pop rotates across the rhythm groups on each piano
# onset, but ONLY in piano-prominent sections (so it's a melodic accent, not a constant wash).
# Change `stem` to bass/guitar/vocals to chase a different instrument's line.
- detector: stem_onsets
- effect: On
- render: per_model
- groups: rhythm
- sections: stem_prominent
- stem: piano
- select: rotate
- density: per_onset
- magnitude: any
- color: anchor_alternate
- direction: none
- enabled: true

## Lyric Color Words
- detector: lyric_color
- effect: On
- render: per_model
- sections: any
- select: all
- density: per_onset
- magnitude: any
- color: lyric
- direction: none
- enabled: true

## Instrument Entrance Feature
- detector: instrument_entrance
- effect: stem_default
- render: per_model
- sections: any
- select: all
- density: 24
- magnitude: any
- color: section
- direction: none
- enabled: true
