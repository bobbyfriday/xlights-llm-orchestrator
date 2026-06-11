> **Build result (verified live):** `pipeline/beats.py` — `section_rhythm` (in-window beats + per-stem onsets + prominent stem = most non-'other' onsets, derived from audio not a brief field) + `place_beat_accents` (beat-chase across rhythm groups, default `On`/`beat`, cap 24/section + downsample, section palette, `_accent_look` validates placeable+look→On fallback since Pulse isn't placeable); SectionPlan rhythm fields (additive); a code pass adds the beat layer over the washes at BOTH generate sites; Director surfaces/requests rhythmic intent (defaults fill it). **147 hermetic tests pass** (7 new). LIVE: re-generated mad russian → 363 placed / 0 skipped = 27 washes + 336 beat accents (24/section cap respected exactly), accents on `04_BEAT_1-4` chasing, MEDIAN 0ms off the nearest beat (dead-on), in the section palette (Warm White intro). The show pulses with the music.

## 1. Per-section rhythm helper

- [x] 1.1 `section_rhythm(sa, section) -> {beats_ms, prominent_stem, stem_onsets_ms, tempo}`: filter `sa.beats` + the prominent stem's `StemFeatures.onsets` to `[start_ms,end_ms)`; prominent stem = top `stem_shares` excluding `"other"` (→ `drums` if present else None when shares absent); graceful when stems absent (beats only)

## 2. Rhythmic intent + the beat-accent placement pass

- [x] 2.1 `SectionPlan`: add `pulse_groups: list[str]`, `follow_stem: str`, `accent_effect: str`, `pulse_on: str` (all defaulted/back-compat)
- [x] 2.2 `place_beat_accents(section, rhythm, available_groups) -> list[EffectInstruction]`: pick times (default `beat` for the regular chase; `onset` per `pulse_on`); **cap to `MAX_ACCENTS_PER_SECTION` (**24**) with even downsample**; **chase** across `pulse_groups` (`groups[i % len]`); short duration (`min(next, t+ACCENT_MS≈250)`); build `EffectInstruction(effect_type=accent_effect, look_id=candidate_look_ids(accent_effect)[0], palette_colors=section.palette, …, section_index)`
- [x] 2.3 Defaults: empty `pulse_groups` → `04_BEAT_*` ∩ `available_groups` (else `target_groups`); empty `follow_stem` → prominent stem; empty `accent_effect` → `On` (placeable; `Pulse` is NOT); `pulse_on` default → `beat` (regular chase); `onset` only when explicitly riding a stem

## 3. Wiring + Director surface

- [x] 3.1 `run.py`: after the section's washes, `rhythm = section_rhythm(sa, section)`; fill intent defaults; `instrs += place_beat_accents(...)`; tag `section_index`. Apply at BOTH generate sites (initial + refine `_regen`)
- [x] 3.2 Director `render_input`: surface the per-section rhythm (compact: beat count, prominent stem, onset count) + request `pulse_groups/follow_stem/accent_effect/pulse_on`; placement stays deterministic regardless of model output

## 4. Tests & verification

- [x] 4.1 `section_rhythm`: synthetic `SongAnalysis` (beats + per-stem onsets) → in-window beats + prominent stem (excludes `other`) + its onsets; stems absent → beats only, prominent None
- [x] 4.2 `place_beat_accents`: produces beat/onset-aligned `EffectInstruction`s on `pulse_groups`, **chasing** (rotating groups), in `section.palette`, tagged `section_index`; a dense section is **capped/downsampled** to ≤24; short durations clamped in-window; `accent_effect` always resolves to a placeable type with a valid look (no index error); total count stays bounded
- [x] 4.3 Defaults: no brief intent → `04_BEAT_*` groups, prominent stem, a placeable accent effect, `pulse_on` chosen by onset availability
- [x] 4.4 Wiring: the beat layer is ADDED to the washes (wash instructions still present); `refine`/existing generation unaffected
- [x] 4.5 Live (gated): re-generate mad russian → beat-synced accents on `04_BEAT`/rhythm groups timed to the drums/prominent-stem onsets; Sync QA reports high beat alignment; offline preview shows pulsing; total effect count stays sane; no new skips
