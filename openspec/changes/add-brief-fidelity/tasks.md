## 1. The gate

- [ ] 1.1 `beats.py`: `section_is_rhythmic(section)` (pulse_groups OR rhythm-pool ∩ target_groups OR intensity ≥ RHYTHM_FLOOR)
- [ ] 1.2 `weave.py`: `rhythm_pool` builds from pulse_groups / rhythm groups in target_groups; injects the default pool ONLY when rhythmic; `fallback_weave` returns empty cells when non-rhythmic
- [ ] 1.3 `run.py` (generate + regen): call `place_beat_accents` only when `section_is_rhythmic`; fallback weave already gated via rhythm_pool/fallback_weave

## 2. Tests & verification

- [ ] 2.1 Hermetic: `section_is_rhythmic` truth table (pulse_groups / rhythm-target / intensity floor / none); fallback_weave empty for a quiet no-rhythm section; rhythm_pool doesn't inject excluded groups; beat accents skipped when non-rhythmic; energetic section unchanged; LLM weave still expands when non-rhythmic
- [ ] 2.2 Live: re-run Christmas Canon → §0 renders as still glow + chosen Snowflakes, rhythm props dark (no injected chases/pops); a known energetic show (carol/DJ) shows no objective regression
- [ ] 2.3 PR (user merges)
