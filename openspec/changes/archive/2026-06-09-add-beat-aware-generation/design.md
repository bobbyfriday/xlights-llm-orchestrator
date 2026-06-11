## Context

Generation = `SectionPlan -> SectionEffects(EffectInstruction[])`, one section-spanning effect per group. The analysis carries `beats` (617, `Beat{time, bar_position}`; `bar_position` is None here → no bar lines, use the beat grid), `onsets`, and per-stem `StemFeatures.onsets` (drums 716, guitar 853, …). `LabeledSection.stem_shares` gives the prominent stem; `04_BEAT_1–4` are targetable rhythm groups. This change adds a deterministic **beat layer** of short accents timed to the beats/the prominent stem's onsets — following the project's "code owns timing, the brief owns the creative choice" pattern (like the palette/intensity passes).

## Goals / Non-Goals

**Goals:** beat/onset-synced accents within sections; directable rhythm intent + default; bounded density; additive to the washes; reuses palette realization. Hermetic tests.

**Non-Goals:** per-onset-of-every-stem; timing-track/BPM-speed sync; bar detection; melody-following; per-stem color; changing the wash generator.

## Decisions

### Per-section rhythm helper (deterministic)
`section_rhythm(sa, section) -> {beats_ms, prominent_stem, stem_onsets_ms, tempo}`: filter `sa.beats` and the prominent stem's `StemFeatures.onsets` to `[start_ms, end_ms)`. **Prominent stem** = the top stem from `section.stem_shares` excluding `"other"` (it's the orchestral catch-all and a poor rhythm lead); if shares absent → `"drums"` if present else None (fall back to beats). Surface a compact form to the Director (counts + the stem, not all 600 times) and the full times to the placement pass.

### Rhythmic intent on `SectionPlan` (additive, brief-directed)
`pulse_groups: list[str]`, `follow_stem: str`, `accent_effect: str`, `pulse_on: "beat"|"onset"` — all defaulted. The Director (given the surfaced rhythm) chooses them; a **deterministic fallback** fills any that are empty: `pulse_groups` → the `04_BEAT_*` groups present in `available_groups` (else the section's `target_groups`); `follow_stem` → the prominent stem; `accent_effect` → a placeable punctuation type (e.g. `On`/`Pulse` — validated against `placeable_effect_types()`); `pulse_on` → `onset` if the stem has onsets else `beat`.

### Deterministic beat-accent placement pass (the core)
After the section's wash instructions are generated, `place_beat_accents(section, rhythm, available_groups) -> list[EffectInstruction]`:
1. Choose the **times**: `pulse_on=="onset"` → the `follow_stem`'s onsets in-window; else (**default**) the beats in-window. **Default `beat`** — the beat grid gives the clean 1‑2‑3‑4 chase the `04_BEAT_*` groups are built for; onsets are irregular (use only when explicitly riding a stem's hits).
2. **Bound density:** cap to `MAX_ACCENTS_PER_SECTION` (**24** — ~24×14≈340 accents total keeps placement time + clutter in check; 48 was too high); if more times, **downsample** evenly (every k-th).
3. **Chase across `pulse_groups`:** for the i-th time, target `pulse_groups[i % len(pulse_groups)]` (one short effect per accent, rotating the group).
4. **Short duration:** each accent spans `t` → `min(next_time, t + ACCENT_MS)` (~250ms), clamped within the section.
5. Build `EffectInstruction(target, effect_type=accent_effect, look_id=_accent_look(accent_effect), palette_colors=section.palette, start_ms, end_ms, section_index)` — **timing code-owned, color via the palette pass, look from the catalog.** `_accent_look` validates `accent_effect` is placeable AND `candidate_look_ids` is non-empty, else falls back to `On`/`On#0` (`Pulse` is NOT a placeable type — the default accent is **`On`**). Layer is left to the emitter's `_free_layer` (accents land over the wash).

These accents are **appended** to the section's instruction list (the wash layer is untouched). Same pattern as the palette/intensity code passes — a post-generation deterministic step in `run.py`, applied at the initial generate and on refine regen.

### Where it plugs in
`run.py`: after the Generator returns a section's washes, compute `rhythm = section_rhythm(sa, section)`, fill the rhythmic-intent defaults, and `instrs += place_beat_accents(...)`. Tag `section_index`. The Director prompt is extended to surface the rhythm + request `pulse_groups/follow_stem/accent_effect/pulse_on` (so a human can steer), but the **placement is deterministic** regardless of what the model returns (it just uses the fields, defaulted).

## Risks / Trade-offs

- **Effect-count blow-up** — the density cap + chase (1 effect per accent, not per group) keeps it bounded (≤48/section × 14 ≈ ~670 accents worst case; downsample lower if placement is slow). The live test asserts the total stays sane and placement time is acceptable.
- **"other"-dominant songs** — for orchestral tracks the prominent non-"other" stem may be guitar/piano (fine) or weak; if no usable stem, fall back to the beat grid. Never blocks.
- **Visual clutter** — too many accents can look busy; the cap + short duration + chase (spreading across groups) mitigate. Tunable constants; the visual critic will flag "too busy."
- **Layer conflicts** — accents go on a free layer over the wash (the emitter already bumps layers on overlap), so they coexist.
- **Sync QA now bites** — beat-aligned accents should *raise* the Sync score; if the cap/quantization misaligns, the QA will show it (good feedback).

## Open Questions

- Best `MAX_ACCENTS_PER_SECTION` / `ACCENT_MS` and whether to chase vs flash-all-pulse-groups — start with chase + ~48 cap + 250ms; tune live against the preview/Sync QA.
- Whether high-energy sections get denser accents than quiet ones (scale the cap by intensity) — a natural later refinement; start uniform.
