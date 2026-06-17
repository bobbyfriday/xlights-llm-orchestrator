## Context

The pipeline (`pipeline/run.py`) runs sequential stages, each cached by song content hash under
`cache_root()/<song_key>/`: `song_analysis`, `music_brief`, `creative_brief` (the `ShowPlan`), and
`instructions` (the realized `EffectInstruction[]`). Effects carry a `section_index` tag, and
`refine.replace_section` swaps one section's tagged slice while leaving the rest intact. The per-section
regeneration logic — intensity escalation, coverage trim, duration normalization, palette/brightness/
speed realization, ensemble/peak bed, carrier-rotated weave, beat accents, feature-prop contrast — lives
inside the closure `_refine_loop._regen` (`run.py:148-201`). It already pins section timing and operates
on exactly one section. There is no entry point to it outside the automatic refine loop.

## Goals / Non-Goals

**Goals:**
- One command to regenerate a single, user-named section in place, steerable by a free-text note.
- Byte-identical output for every other section (only the chosen section's slice changes).
- Reuse the existing realization — no second, drifting copy of `_regen`.
- Re-emit and re-save so the on-disk sequence reflects the change.

**Non-Goals:**
- No re-running of the judge/QA loop (this is the *manual* counterpart, not automatic refinement).
- No re-running of global, cross-section post-processing (key-moment synthesis, triggers) that could
  perturb other sections — targeted regen matches the refine loop's per-section scope exactly.
- No new section model fields, no Director re-plan (structure/`ShowPlan` stays as cached; the note steers
  the *generator*, not a redesign).

## Decisions

**1. Extract `_regen` to a module-level `regenerate_section(st, rev, *, gen_agent)`.**
Move the body of `_refine_loop._regen` verbatim to a module-level function taking the `State`, a
`RevisionBrief`, and the generator agent. `_refine_loop._regen` becomes a thin wrapper that supplies
`gen_agent` and (when injected) the test `regenerate` hook. This guarantees the CLI path and the refine
path realize a section identically.

*Alternative considered:* duplicate the logic in the CLI. Rejected — `_regen` is ~50 lines of subtle
realization that would silently drift from the loop.

**2. New `regen_section(...)` pipeline entry that rehydrates a `State` from cache.**
It loads `song_analysis`, `music_brief`, `show_plan`, and `instructions` from the cached artifacts (the
same `model_validate`/`SongAnalysis` deserialization the run path uses), plus `available_groups` /
`placeable_types` (recomputed from the live client, as in a normal run). It validates the section index,
builds a `RevisionBrief(section_index=i, issue=note or "manual regenerate", suggested_fix=note)`, calls
`regenerate_section`, then `replace_section`, `clamp_layer_budget`, re-emits via the emitter, persists the
updated `instructions` cache, and re-finalizes the saved sequence (audio + render-order + timing-track
patch) so the output matches a normal save.

*Alternative considered:* mutate the live xLights sequence's section region only. Rejected — `apply_
instructions` rebuilds a clean sequence from the full instruction list; feeding it the spliced list is
simpler and already deterministic, and other sections' unchanged instructions render identically.

**3. Targeting is by index, listed for the user.**
`--list` prints `i  label  start–end` per section so the user can choose. `--section i` selects it;
out-of-range fails loudly. A future `--at mm:ss` could map a timestamp to its section, but index is the
contract now (matches `RevisionBrief.section_index`).

**4. The note is optional and purely a generator steer.**
With a note → it populates the `RevisionBrief` issue/fix (the generator's existing `revision=` path,
already exercised by refine). Without a note → a fresh reroll of that section (no guidance), still pinned
to the cached structure.

## Risks / Trade-offs

- [Stale cache: instructions newer than show_plan, or hand-edited] → Reload all four artifacts together;
  if `instructions` is missing, fail with "run `xlo run` first". The regen only rewrites the chosen
  section's slice, so a stale-but-valid cache still yields a coherent splice.
- [Section count changed since the cache was written] → Validate `0 <= i < len(show_plan.sections)` and
  that the instruction set actually has that `section_index`; error clearly otherwise.
- [Global post-processing not re-applied (e.g. a key-moment flash that targeted the old section)] →
  Acceptable and consistent with the refine loop, which also regenerates per-section without re-running
  global synthesis; document it. Re-running `xlo run --refine` remains the path for whole-show coherence.
- [Determinism of the LLM reroll] → A reroll changes that section by design; everything else is byte-
  identical, which is the guarantee we test.

## Open Questions

- Should `regen` without `--save`/`--name` re-finalize the existing saved sequence by default? Decision:
  yes — default to the song's derived name (like `run`), with `--name` to override and `--no-save` to
  leave it open/unsaved for inspection.
