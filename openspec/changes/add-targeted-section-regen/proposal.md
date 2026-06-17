## Why

Every pipeline stage is already cached by song content hash (`song_analysis`, `music_brief`,
`creative_brief`/`ShowPlan`, `instructions`), and the refine loop already regenerates **one section at
a time** — `_refine_loop._regen` realizes a single section and `replace_section` swaps its slice while
leaving every other section's instructions byte-identical. But that power is only reachable through the
full automatic `--refine` loop (test → judge → revise → rebuild → QA). There is no way to say "section 4
is too busy — just redo *that* one and leave the rest alone." For targeted fixes the user must re-run the
whole loop and hope the judge flags the section they care about. We want a direct, human-driven
single-section regenerate.

## What Changes

- **Extract** the per-section realization currently nested inside `_refine_loop._regen` into a reusable
  module-level `regenerate_section(st, rev)` so the refine loop and a new CLI command share one code
  path (no behavior change to refine).
- **New `xlo regen` CLI command** that reloads the cached artifacts for a song and regenerates a single
  section in place:
  - `xlo regen --song <path> --list` prints each section's index, time range, and label.
  - `xlo regen --song <path> --section <i> [--note "..."]` regenerates section `i`, optionally steered by
    a free-text fix note (e.g. *"too busy, calm it down"*), then re-emits and re-saves the sequence.
- **Section timing and structure stay pinned** (`start_ms`, `end_ms`, `target_groups`), exactly as the
  refine loop pins them; only section `i`'s instructions change. All other sections render identically.
- **A fix note becomes a `RevisionBrief`** (`section_index` + `issue`/`suggested_fix`), reusing the
  existing generator `revision=` path the refine loop already uses.
- Requires a prior `xlo run` (so the cache exists) and an LLM key (the generator agent runs).

## Capabilities

### New Capabilities
<!-- none — this exposes existing per-section regeneration through a new entry point -->

### Modified Capabilities
- `show-refinement`: per-section regeneration becomes directly invokable for a single, user-chosen
  section (outside the automatic loop), reloading cached artifacts, steerable by a free-text note, with
  section structure pinned and all other sections left intact.

## Impact

- `packages/xlights-orchestrator/src/xlights_orchestrator/pipeline/run.py`: lift `_regen`'s body to a
  module-level `regenerate_section(st, rev, *, gen_agent)`; have `_refine_loop._regen` call it.
- `packages/xlights-orchestrator/src/xlights_orchestrator/cli.py`: add the `regen` subcommand (`--song`,
  `--section`, `--list`, `--note`, `--name`).
- A thin `regen_section` pipeline entry that loads cached `song_analysis` / `music_brief` / `show_plan` /
  `instructions` into a `State`, runs `regenerate_section`, `replace_section`, `clamp_layer_budget`,
  re-emits via the emitter, and re-finalizes (audio/render-order/timing-track patch) the saved sequence.
- Tests: hermetic coverage that one section's slice changes and all others are byte-identical; a section
  listing test. No schema changes; back-compatible with existing caches.
