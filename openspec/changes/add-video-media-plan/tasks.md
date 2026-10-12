## 1. Config and ledger (no LLM)

- [x] 1.1 `models/config.yaml`: `video:` block — `veo: {model, per_second_usd (TODO), clip_s: 8, max_stretch: 1.2, daily_clips: 10, quota_reset_tz: America/Los_Angeles}`, `still: {model, per_image_usd (TODO)}`; `registry.video_config()` accessor + `video_cost(seconds) -> float | None` (unpriced ⇒ None, never 0).
- [x] 1.2 `veo_ledger.py`: `LedgerEntry{ts, day, clip_id, song_key, asset, seconds, model}`, `ledger_path()` at `cache_root()`, `read()`, `append()`, `day_for(ts, tz)`, `remaining_today(limit, tz)`; tolerant line-by-line parse (a bad line is skipped and logged).
- [x] 1.3 Tests: remaining counts across songs; yesterday ignored; missing file ⇒ full quota and no file created; append then read round-trips; tz boundary (23:30 vs 00:30 in the configured zone).

## 2. The media planner (pure functions)

- [x] 2.1 `media_plan.py`: `MediaBudget{campaign_clips, clip_s, max_stretch, pinned: list[int]}`, `SectionMedia{index, medium, asset, value, clips}`, `Asset{id, label, sections, clips, promote_rank}`, `MediaPlan{budget, ledger_remaining, sections, assets, veo_seconds, est_usd}`.
- [x] 2.2 `value_scores(energies, climax, featured_hits, n)` with weights as module constants; `asset_groups(labels)`; `clips_for(duration_ms, clip_s, max_stretch)`.
- [x] 2.3 `plan(sections, labels, energies, featured_hits, budget, ledger_remaining) -> MediaPlan`: pinned first, then by value, group-at-a-time, never over budget; promote ranks by asset value; budget 0 ⇒ all procedural.
- [x] 2.4 `featured_hits(featured_lines, lyric_lines, sections)`: which sections carry a featured line (text match on aligned lines).
- [x] 2.5 Tests per spec: determinism; climax first with a one-group budget; budget never exceeded; zero budget; pinned sections; chorus ×4 shares one asset counted once; 20.8 s @ 8 s × 1.2 ⇒ 3 clips; exhausted ledger leaves filmed sections unchanged.

## 3. Storyboard written for the medium

- [x] 3.1 `video_script.py`: `Beat.procedural_stand_in: str = ""`; `Shot.medium`, `Shot.asset`, `Shot.clips`, `Shot.promote_rank` (defaulted, so old JSON loads); `split_long_shots` takes `media` and splits filmed shots only at `clip_s × max_stretch` (or the user maximum); `assign_lyrics` unchanged.
- [x] 3.2 `agents/videographer.py`: `render_input` adds per-section `· FILMED (asset A, 3 clips)` / `· PROCEDURAL` and an asset-group line; `PERSON_TERMS` list + `lint_media(out, plan)` returning `(beat_index, term)` hits over procedural beats' imagery/action and every stand-in; registered as a PydanticAI output validator raising `ModelRetry` (one retry) and requiring a non-empty stand-in on filmed beats.
- [x] 3.3 `agents/prompts/videographer.md`: procedural vocabulary (do / forbidden), motif rule (character only in filmed beats, proxy object carries it), stand-in instruction, asset-group instruction ("write the group as one shot that returns").
- [x] 3.4 Tests: input shows medium per section and asset groups; person in a procedural beat ⇒ one retry (TestModel sequence); second hit ⇒ no file; hands in a filmed beat pass; missing stand-in on filmed beat fails; prompt text contains the vocabulary and rule.

## 4. Hand-off, persistence, CLI

- [x] 4.1 `media_plan.py`: `veo_prompt(shot, constraints)` (imagery + action + camera + lighting + contract notes, no text) and `procedural_brief(shot, palette, constraints)` (stand-in for filmed shots, beat for procedural; span + frame count from the resolved shot). Write `media_plan.json` with per-shot hand-off.
- [x] 4.2 `pipeline/video.py`: build the plan before `render_input`; pass media into `resolve_beats`/`split_long_shots`; write `media_plan.json` beside `video_script.json`; refusals still write nothing; a validation failure writes neither file.
- [x] 4.3 `render_markdown`: per-shot medium / asset / clips / promote rank; a **Media** summary under the contract (filmed sections, assets, clips, Veo seconds, est. spend or "unpriced", renderable today from the ledger).
- [x] 4.4 `cli.py`: `--veo-clips N` (campaign budget; default = `daily_clips`), `--no-veo` (⇒ 0), `--filmed-sections 3,6` (pinned); `--max-shot-s` documented as the filmed clip-length override.
- [x] 4.5 Tests: end-to-end writes script + plan; `--no-veo` ⇒ all procedural, 57 s shot unsplit; priced vs unpriced estimate; hand-off spans come from the resolved shot; existing `video_script.json` without the new fields still loads.

## 5. Prove it

- [x] 5.1 ruff, mypy, pytest green with CI's fresh-resolve invocations.
- [x] 5.2 Archive `add-matrix-video-script` so the `video-script` delta applies to a base spec.
- [x] 5.3 Regenerate the four cached storyboards at the default budget (10 clips) and read them: are the filmed sections the right ones, do procedural beats avoid people, do motifs carry across the media? Paste Christmas Canon's media summary and one procedural beat in the PR.
- [x] 5.4 `docs/usage.md`: media plan section (budget vs quota, ledger location, flags, what the renderers will consume); PR to `main` from `feat/video-media-plan`.
