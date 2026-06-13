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
> - **detector** — what finds the events: `guitar_solo` | `drum_onsets` | `lyric_color` | `instrument_entrance`
>   (a "big moment" is just `drum_onsets` with `magnitude: top:<low pct>` + `render: whole_house`)
> - **effect** — the xLights effect to place (e.g. `Lightning`, `Shockwave`)
> - **render** — `per_model` (each prop, scaled to it) | `whole_house` (one gesture across the layout)
> - **sections** — eligibility: `any` | `drum_prominent` | `has_guitar_solo` | `peak`
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

## Drum Onset Pops
# A per-prop POP/flash on each drum hit (opaque, top layer → punches through the lit fabric).
# Not a radiating shockwave — just a drum-reactive pop in an alternating contrast color, on a
# rotated subset of drum-heavy sections so it's an effect you catch periodically, not constantly.
- detector: drum_onsets
- effect: On
- render: per_model
- sections: drum_prominent
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
