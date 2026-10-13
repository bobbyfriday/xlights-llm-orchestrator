## Context

Today `xlo run` is a single async process: analyze → analyst panel + synthesizer (LLM) → Director (LLM) → per-section Generator (LLM ×~21) → deterministic realization → emit to xLights → optional refine loop (QA + visual critic (LLM) + Judge (LLM) + regen) → finalize. Every LLM call goes through `pydantic-ai` with a per-role model registry; LLM-stage caches are namespaced under a model fingerprint. The song's cache dir already holds the stage artifacts (`song_analysis`, `creative_brief.json` + schema, `instructions.json`), and `xlo regen` already proves that "reload cache → change one thing → re-realize → re-emit everything" is a workable cycle.

What the explore settled: Claude Code is the loop; the creative brief is the single judgment artifact; the per-section Generator goes and the deterministic fallback fabric becomes the main path; interpretation is a conversation, not a file; review is manual; apply stays on live xLights; unattended runs are out of scope; the skills and commands live in this repo's `.claude/`; the videographer and layout classifier move to skills in the same change so `pydantic-ai` can be removed entirely.

Constraints: `xlights-core` and `xlights-mcp` are untouched. The realization layers (beats/weave/triggers/timing/phrasing/faces/matrix text/color script/QA/finalize) are the project's real asset and must keep their behavior; the golden fixture and the fabric canary must still pass. Changes land via PR, never on `main`.

## Goals / Non-Goals

**Goals:**
- A show is made in a Claude Code session: read the digest, talk about the song, write the brief, realize, apply, watch, adjust, finalize.
- `xlights-orchestrator` has no LLM dependency and needs no API key (lyrics still need `GENIUS_ACCESS_TOKEN`).
- Every stage is an `xlo` command with a documented file contract under the song's cache dir, runnable by hand, resumable by virtue of the files existing.
- Claude can self-correct a brief from structured validator output without a human in the middle.
- The brief exposes the few fabric knobs the Generator used to set, with sensible code defaults.
- The fixture-driven hermetic tests cover realize/QA/timing exactly as before.

**Non-Goals:**
- Unattended or headless runs (possible later via `claude -p`; not designed for here).
- Writing effects into the `.xsq` offline (apply keeps using the live REST listener).
- A plugin that works outside this repo.
- Preserving the A/B harness, cost telemetry, or revision log in any form.
- Changing the preset library, the audio analyzer, or the MCP server.

## Decisions

### D1. Bash-invoked CLI for stages; MCP only for live xLights
Stage commands are plain `xlo <stage>` invocations that Claude runs through Bash. They print a short human summary to stdout and write their real output to files. **Why not MCP tools:** a CLI is runnable by the user without Claude, debuggable with the shell, and its outputs are files Claude reads with the same tools it uses for everything else. `xlights-mcp` stays as-is for live read/edit operations that the commands do not cover.

### D2. One judgment artifact: `creative_brief.json`, written by Claude
Claude writes the `ShowPlan` JSON directly (guided by the `xlo-brief` skill and the per-run `creative_brief.schema.json`), then runs `xlo validate-brief`. **Alternatives:** YAML (friendlier to write, but the schema tooling and the existing loader are JSON); a markdown brief parsed by code (loses the schema). The brief keeps `$schema` so VS Code still validates it when the user edits by hand.

### D3. The brief gains an optional per-section `fabric` block; realize is deterministic
```
"fabric": { "carrier": "SingleStrand", "alternation": "pingpong", "cell_beats": 2, "blend": "Max" }
```
All four fields are optional; empty means "code chooses". `realize` builds the section's `SectionWeave` from these fields over today's `fallback_weave` (carrier on the rhythm pool, sparse texture from `effect_types`), then runs the unchanged downstream layers (bed, peak fill, accents, triggers, flashes, phrase curves, curated composites, counter-rotation, treatment gating, layer clamp, occlusion guard). Render style per effect comes from `fallback_style(effect_type)`; look ids from `candidate_look_ids(type)[0]` with the existing label-seeded rotation. **Why these four:** they are the recipe fields with visible, nameable effect on the show (what moves, how it alternates, how fast, how it blends); `direction`, `motion_curve`, and `transition` already have code-chosen defaults (`counter_rotate_stacks`, `label_seed`, legato transitions). **Alternative rejected:** exposing the whole `CellRecipe` list in the brief, which re-creates the Generator's 21-schema problem in Claude's hands.

### D4. Interpretation is a conversation over a deterministic **analysis digest**
`xlo analyze` writes `analysis_digest.md` next to the cached analysis: duration, meter and tempo, sections (from lyric markers or audio segmentation, downbeat-snapped) with per-section normalized energy, dominant stems, chord density, timed lyric lines, repeated lines, detected instrument entrances, key and mood descriptors. This is the deterministic half of today's `song_description.py` plus the analyst slices from `panel.py`, rendered once in a bounded size (target < 20 KB). Claude reads it, discusses structure with the user, and encodes the agreed interpretation in the brief's `experience`, `concept`, section labels, and `key_moments`. `MusicBrief` is deleted; `build_timing_tracks` and `resolve_beats_per_bar` take the brief's sections (the `fallback_sections` path that already exists) and the analysis.

### D5. `xlo validate-brief` returns machine-readable, actionable errors
Checks: JSON parses as `ShowPlan`; sections ordered, non-overlapping, covering the song within tolerance; every `target_groups`/`pulse_groups` entry is targetable; every effect type is placeable; `scene_id` exists; `follow_stem` is one of the song's stems; palette names resolve; `fabric.carrier` is a cellable effect; intensity in range. Output: `validation.json` `{ok, errors:[{path, message, allowed?}], warnings:[...]}` and a one-line stdout summary. Exit code 1 on errors. **Why:** this is the loop that replaces structured-output enforcement; Claude fixes and re-validates until clean. The checks are lifted from `layout_validate.py`, `brief_schema.py`'s enum sources, and the Director prompt's rules.

### D6. Cache layout flattens; no model namespacing
```
data/analyses/orchestrator/<song-slug>--<hash>/
  song_analysis.json        (unchanged, shared)
  analysis_digest.md        (new)
  vocab.json                (targetable groups, placeable types, scene ids, stems, colors)
  creative_brief.json       (+ creative_brief.schema.json)
  validation.json
  instructions.json
  applied.json              (emit result: placed/skipped per instruction)
  qa.json
  stills/<section>.png
  video_story.json          (Claude-written) → video_script.json + .md (code)
  layout_review.json        (init-layout, show-dir scoped)
```
`cache_path(key, stage)` keeps its signature with `models=` removed; `models_fingerprint` and `FINGERPRINT_EXEMPT_ROLES` are deleted. Old `m-xxxxxxxx/` subdirs are simply never read.

### D7. Skills point at the root guide files; commands are thin prompts
Skills (`.claude/skills/xlo-*/SKILL.md`): `xlo-sequencing` (reads `xlights-sequencing-guide.md`, `xlights-effects-catalog.md`, `xlights-layering-rendering-guide.md`), `xlo-scenes` (scene + trigger cookbooks), `xlo-layout` (layout semantics spec, the manifest, SEM_ groups), `xlo-brief` (how to author and validate a brief: the field meanings, the fabric knobs, the treatment table, the validate loop), `xlo-video` (story rules from the videographer prompt). Each SKILL.md is short and tells Claude which root file to read when; the guides stay single-source and hand-editable. Commands (`.claude/commands/xlo/<name>.md`) say which skills to load, which `xlo` command to run, which files to read, and what to do with the result. **Alternative rejected:** copying the guides into the skills (two sources that drift).

### D8. The command flow
```
/xlo:analyze <mp3>   xlo analyze → xlo groups   → read digest + vocab; summarize; discuss structure
/xlo:design          load xlo-brief, xlo-sequencing, xlo-scenes, xlo-layout → write brief
                     → xlo validate-brief (loop until ok) → show the brief in plain language
/xlo:realize         xlo realize → xlo qa → read qa.json; report findings; propose brief edits
/xlo:apply           xlo apply → read applied.json; report skips
/xlo:review          xlo stills → read PNGs + qa.json; ask the user what they saw;
                     take feedback ("redo 1:05–1:30, calmer") → edit brief (split a section if the
                     range isn't a boundary) → validate → realize → apply
/xlo:finalize        xlo finalize --name <seq>
/xlo:video           load xlo-video → write video_story.json → xlo video-plan
/xlo:init-layout     xlo init-layout --dry-run → read layout_review.json → classify the tail into
                     layout_overrides.json → xlo init-layout
```
A `/xlo:show <mp3>` convenience command chains analyze → design → realize → apply with the conversation pausing after design and after apply.

### D9. Review is manual; QA keeps the cheap judgments as findings
No Judge, no critic, no loop. `xlo qa` keeps `qa.evaluate` (sync, placement, rules, variety, musicality, coverage from the `.fseq` series when present) and adds the two checks the critic contributed that are computable: **dark mid-energy** (a section with normalized energy ≥ 0.6 whose rendered lit-coverage stays below the floor, from `fseq_metrics`) and **static section** (coverage variance near zero over an energetic section). Findings carry `section_index` and a plain-language fix so Claude can propose a brief edit. Nothing gates; the human decides.

### D10. Re-apply is a full re-emit
`xlo apply` always creates a clean-slate sequence and emits every instruction, exactly as `regen` does today. Scoped re-emit would need per-effect deletion through the live API, which is both unsupported by the emitter's additive design and the crash-prone path. Cost is seconds to a minute per cycle, acceptable for a manual loop.

### D11. Video and layout onboarding split the same way
`video_script.py` keeps everything after the agent: `resolve_beats`, `split_long_shots`, `assign_lyrics`, `media_plan.plan`, `veo_prompt`, `render_markdown`. `VideographerOut` becomes the schema for `video_story.json` that Claude writes. `init_layout` drops the `classify_tail` call; the unresolved props are written to `layout_review.json` with the features the classifier saw; Claude writes `layout_overrides.json` entries (the file `_load_overrides` already reads) and re-runs.

### D12. Tests re-base on fixture briefs
`test_golden_pipeline.py` replaces its `TestModel` Director/Generator with a fixture `creative_brief.json` (including a `fabric` block on at least one section) and asserts the same instruction properties and the fabric canary. Tests for deleted modules are deleted. New hermetic tests: digest rendering from the fixture analysis, validate-brief error cases, fabric-field realization, qa's new findings, CLI stage commands with a fake client.

### D13. Removal order
Additive first, then subtractive, in three PRs: (1) digest + vocab + validate-brief + fabric fields + stage commands, with `xlo run` still present; (2) skills + commands + docs, used for at least one real song; (3) delete agents, registry, refine, live server, editor, telemetry, reporting, revision log, A/B, `pydantic-ai`, their tests, and the old CLI subcommands. PR 1 is independently mergeable and already useful (a hand-edited brief can be realized without an LLM).

## Risks / Trade-offs

- [Shows get worse without the per-section Generator] → the fallback weave and curated composites were always the floor; the fabric block gives the brief the knobs that mattered; the fabric canary and `measure_fabric.py` compare before/after on the golden fixture and one real song before PR 3 deletes the agent path.
- [Claude writing ~20 sections of JSON is slow or error-prone] → the schema enumerates the vocabulary, `validate-brief` gives path-level errors, and the `xlo-brief` skill shows a complete worked section; the digest keeps the input bounded.
- [Guides are ~100 KB; loading them all every design costs context] → skills are loaded per command and tell Claude which file to read for which decision; the catalog and cookbooks are read in full only during `/xlo:design`.
- [Time-range feedback that doesn't match a section boundary] → the brief's sections carry their own `start_ms`/`end_ms`; `validate-brief` accepts any non-overlapping cover, and the `/xlo:review` command splits a section at the requested times. Boundaries that aren't downbeats get a validation warning, not an error.
- [Losing `MusicBrief` breaks timing tracks and video] → both already accept the plan's sections as the fallback; the digest carries the labels; tests cover the no-MusicBrief path.
- [Pre-change caches go cold for briefs and instructions] → analysis and targetable-group caches are reused; one cold design per song is the migration cost, accepted.
- [No A/B harness or cost report] → accepted in the explore; quality comparison falls back to the fabric stats script and the user's eyes.
- [xLights crashes during apply still interrupt the loop] → unchanged from today; `apply` is idempotent and `instructions.json` persists, so the recovery is "restart xLights, `xlo apply` again".

## Migration Plan

1. PR 1 (additive): new stage commands and files alongside `xlo run`. Verify `xlo realize` on an existing cached brief reproduces the golden fixture modulo the Generator rows.
2. PR 2 (skills + commands + docs): make one real show end-to-end in a Claude Code session on this branch; fix the skill text from what went wrong.
3. PR 3 (removal): delete the agent harness and dependencies; update `.env.example`, README, usage, architecture; `uv lock` without `pydantic-ai`.
Rollback at any step is reverting that PR; PR 1 and 2 leave `xlo run` working.

## Open Questions

- Should `xlo apply` also trigger `renderAll` and wait, or leave rendering to `xlo stills`/`finalize` (today render happens inside the refine loop only)? Default: `apply --render` flag, off by default.
- Does `/xlo:design` write the brief in one pass or section-by-section with validation between? Default: one pass, validate, fix; revisit after the first real song.
- Keep `degradations.py` (the best-effort failure collector) as the stage commands' warning channel, or fold it into stdout summaries? Default: keep, print its summary at the end of each command.
