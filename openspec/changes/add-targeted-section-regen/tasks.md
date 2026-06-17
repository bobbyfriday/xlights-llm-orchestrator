## 1. Extract per-section realization into a reusable function

- [x] 1.1 In `pipeline/run.py`, lift the body of `_refine_loop._regen` into a module-level
  `async def regenerate_section(st, rev, *, gen_agent) -> list[EffectInstruction]` (same imports/helpers:
  `effective_intensity`, `section_rhythm`, `trim_coverage`, `normalize_durations`, palette/brightness/
  speed, `ensemble_bed`/`peak_fill`, `section_carrier`/`fallback_weave`/`diversify_carrier`/`expand_weave`,
  `clamp_hard_caps`, `place_beat_accents`, `feature_prop_contrast`). Pin section structure as today.
- [x] 1.2 Make `_refine_loop._regen` a thin wrapper: if an injected `regenerate` hook is set use it, else
  call `regenerate_section(st, rev, gen_agent=gen_agent)`. Confirm no behavior change (refine tests pass).

## 2. Pipeline entry: rehydrate State from cache and regen one section

- [x] 2.1 Add `async def regen_section(song, *, client, section_index, note, save_as, use_cache=True)` in
  a pipeline module. Load cached `song_analysis` (`SongAnalysis` deserialize), `music_brief`,
  `show_plan` (`creative_brief`), and `instructions` into a `State`; recompute `available_groups` /
  `placeable_types` from the live client as a normal run does.
- [x] 2.2 Guard: if the `instructions` cache is missing, raise a clear "run `xlo run` for this song first"
  error; if `section_index` is out of range or absent from the instruction tags, fail loudly.
- [x] 2.3 Build `RevisionBrief(section_index=i, groups=section.target_groups, issue=note or "manual
  regenerate", suggested_fix=note or "")`; call `regenerate_section`; `replace_section`;
  `clamp_layer_budget`.
- [x] 2.4 Re-emit via `apply_instructions` (clean rebuild from the spliced list), persist the updated
  `instructions` cache, and when `save_as` is set re-finalize (`finalize_sequence`: audio + render order +
  timing tracks) so the saved sequence reflects the change. `--no-save` leaves it open/unsaved.
- [x] 2.5 Add a `list_sections(song)` helper returning `(index, label, start_ms, end_ms)` per section from
  the cached `show_plan`.

## 3. CLI: the `regen` subcommand

- [x] 3.1 In `cli.py`, add `regen` subparser: `--song` (required), `--section` (int), `--list` (flag),
  `--note` (str), `--name` (str), `--no-save` (flag), `--no-cache` (flag).
- [x] 3.2 `--list` (or `--section` omitted) prints `i  label  m:ss–m:ss` per section via `list_sections`
  and exits.
- [x] 3.3 `--section i` runs `regen_section` inside an `XLightsClient` context (mirror `_run`), requires
  an LLM key (reuse the `has_llm_key()` guard), and prints a short before/after summary (which section,
  effect count delta).

## 4. Hermetic tests

- [x] 4.1 Test `regenerate_section` parity: refine-loop regen and the extracted function produce identical
  instructions for the same `State`/`RevisionBrief` (inject a fake generator so no API key is needed).
- [x] 4.2 Test `regen_section` end-to-end with a fake generator + fake emitter: only section `i`'s slice
  changes; assert every other section's instructions are byte-identical (`model_dump` equality) and
  section `i`'s `start_ms`/`end_ms`/`target_groups` are preserved.
- [x] 4.3 Test the guards: missing instructions cache → clear error; out-of-range index → error, no
  mutation.
- [x] 4.4 Test note plumbing: a note populates the `RevisionBrief.issue`/`suggested_fix` reaching the
  generator (assert via the fake generator's captured input).
- [x] 4.5 Test `list_sections` formatting/content against a cached show plan fixture.
- [x] 4.6 Run the full hermetic suite (`pytest`) — confirm refine and golden-pipeline tests still pass.

## 5. Live verification

- [ ] 5.1 `xlo run --song "mp3/christmas canon.mp3"` to seed the cache, then `xlo regen --song "mp3/
  christmas canon.mp3" --list` and confirm the section table.
- [ ] 5.2 `xlo regen --song "mp3/christmas canon.mp3" --section <i> --note "too busy, calm it down"` and
  confirm in xLights that only that section changed and the rest is identical.

## 6. Land

- [x] 6.1 Document the `regen` command (README / CLI help) — when to use it vs `--refine`.
- [ ] 6.2 Open a PR per the project workflow; do not commit to `main` directly.
