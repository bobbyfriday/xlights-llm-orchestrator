# rebalance-hit-vocabulary — design

> Executor note: exact anchors as of commit `1cd742d` (2026-07-07); re-locate by symbol if drifted.
> Corpus numbers cited are from the 2026-07-07 measurement (17 community .xsq = 27,099 effects;
> ours = 3 instruction caches = 3,852): flat-flash types (On/Strobe/Shimmer/Twinkle/Lightning)
> ≈ 42% of our fabric vs ≈ 7.5% community; Shockwave 12.6% community vs 3.6% ours; community
> Strobe = 3 placements total; community Shockwave median duration 600 ms, top targets = mini
> trees, stars, snowflakes, spinners, whole-house groups.

## Context

`place_beat_accents` (`packages/xlights-orchestrator/src/xlights_orchestrator/pipeline/beats.py`,
~line 355) builds five rhythm sublayers — meter backbone (ring walk), backbeat (2&4 answer),
sparkle (top drum hits on accent props), hero (melodic onsets on the focal), bass (ground band) —
but every one of them uses the SAME effect: `eff, look = _accent_look(section.accent_effect)`
(~line 374), where `_accent_look` falls back to `On`. The `_mk(target, t, end, ...)` closure
(~line 385) stamps that one `eff`/`look` on every accent. This single choice is why `On` is 21.7%
of our fabric.

`pipeline/triggers.py` (~line 35) already holds `SHOCKWAVE_SETTINGS` — hand-authored radiating-
Shockwave settings ("a modest ring expanding from center", built to read on accent props like
snowflakes/spinners). Import direction constraint: **triggers.py imports from beats.py** (line 19),
so beats.py must not import from triggers.py — the dict has to move to a common module.

Strobe/Shimmer inflation: the generator occasionally chooses Strobe/Shimmer for a section;
`normalize_durations` (beats.py, the hit/pulse expansion around line 549–585) legitimately chops a
section-spanning hit effect into per-bar pulses — turning one bad choice into dozens of placements
(290 Strobes across 3 runs). `clamp_hard_caps` (`qa/rules.py` ~line 161) already enforces the
duration caps (Strobe ≤ 1 s, Shimmer ≤ 2 bars) but nothing constrains *count* or *placement
context*.

The QA advisory pattern to copy: the motion-share advisory in `qa/rules.py::evaluate` (~lines
135–157) — per-section, energetic-only (`intensity ≥ MOTION_SHARE_INTENSITY`), treatment-exempt
(`_QUIET_TREATMENTS`), `severity="warn"`, `objective=False`.

## Goals / Non-Goals

**Goals:**
- Shaped radial hits (Shockwave) in the sparkle + backbeat accent roles, per community practice.
- Strobe restricted to peak sections; Shimmer count-capped.
- A QA advisory that keeps flat-flash share inside the corpus band going forward.

**Non-Goals:**
- Changing the meter backbone / bass / hero effects (On for backbone+bass matches community's own
  use of On; the hero already follows the melodic stem via `STEM_EFFECT`).
- Touching the curated trigger cookbook placements (their Shockwave usage is already correct).
- Reducing accent *count* (`SPARKLE_TOP_N`, `MAX_ACCENTS_PER_SECTION` unchanged — this change is
  about which effect, not how many).
- Prop-fit policy generally (separate roadmap item, `effect-variety-audit` memory).

## Decisions

**D1 — Move `SHOCKWAVE_SETTINGS` to `pipeline/effect_meta.py`** (rename in place, keep the dict
identical, keep the provenance comment). `triggers.py` re-imports it from there (public name
unchanged so its own callers don't churn); `beats.py` imports it too. Rationale: effect_meta is
the per-effect metadata module with no orchestration imports — cycle-free by construction.

**D2 — Role-differentiated accents in `place_beat_accents`.** Extend `_mk` with an optional
`eff_override: tuple[str, str] | None = None` (effect_type, look_id) and an
`extra_override: dict | None = None`:

- *Sparkle block* (~line 436) and *backbeat block* (~line 420): use
  `("Shockwave", candidate_look_ids("Shockwave")[0])` with `SHOCKWAVE_SETTINGS` merged into the
  extra settings, and duration `SHOCKWAVE_ACCENT_MS` (new tuning dial = **600**, the community
  median) instead of `ACCENT_MS` (250) — still clipped by `_end_at`'s next-beat/section caps.
- *Backbone, bass*: unchanged (`accent_effect` → On fallback).
- *Hero*: unchanged.
- Respect an explicit Director choice: if `section.accent_effect` is a placeable non-On effect,
  the backbone keeps it (today's behavior) — the sparkle/backbeat override still applies (those
  roles are code-owned, same split as treatments).
- Legato phrasing: keep the existing legato behavior (soft edges + sparser); Shockwave accents in
  legato sections get the same soft-edge settings the `_mk` closure already applies.

**D3 — Strobe demotion + Shimmer cap, next to the existing hard caps.** New function in
`qa/rules.py` (beside `clamp_hard_caps`):

```python
def demote_offpeak_hits(instructions, *, is_peak: bool) -> int:
    """Corpus rule: Strobe is a climax effect (community: 3 placements in 27k). Outside a peak
    section, every Strobe instruction becomes a Shockwave (look remapped); Shimmer instances beyond
    SHIMMER_MAX_PER_SECTION (tuning, =2) are dropped, keeping the earliest. Returns count changed."""
```

(Implementation note: substitute `effect_type` and `look_id = candidate_look_ids("Shockwave")[0]`,
merge `SHOCKWAVE_SETTINGS`; drop Strobe-specific extra keys is unnecessary — unknown keys are
harmless in xLights settings strings, but strip keys starting `E_` from the old effect if present
in `extra_settings` for cleanliness.) Call it in `realize_section`
(`pipeline/generate.py`, next to the existing `clamp_hard_caps(kept, ...)` call, which already has
`si in _peaks` in scope). Why substitution (not drop): the generator placed a hit *moment* there —
keep the moment, fix the vocabulary; dropping would leave rhythmic holes.

**D4 — Flat-flash QA advisory.** In `qa/rules.py`: `FLAT_FLASH = frozenset({"On", "Twinkle",
"Strobe", "Shimmer", "Lightning"})`; threshold `FLAT_FLASH_SHARE_MAX = 0.30` in
`pipeline/tuning.py` (cite the corpus: ours 42% / community 7.5% — 0.30 is deliberately loose to
avoid spamming the Judge). Add a per-section advisory block inside `evaluate` mirroring the
motion-share block exactly (energetic-only, `_QUIET_TREATMENTS` exempt, `severity="warn"`,
`objective=False`), with a detail message citing this change's doc.

**D5 — One-line prompt grounding.** In `agents/prompts/director.md` and
`agents/prompts/generator.md`, add a single sentence to the effect-choice guidance:
"Community shows punctuate with SHAPED hits (Shockwave ~13% of all placements, on trees/stars/
snowflakes/spinners) and almost never Strobe (3 placements in 27,000) — prefer Shockwave for hits;
Strobe only at the single climax." (Exact wording at executor's discretion; keep it one sentence
per file; the corpus numbers make it concrete for the LLM.)

## Risks / Trade-offs

- [Shockwave on tiny low-pixel props reads as a blob, not a ring] Community places Shockwave on
  these same prop classes (snowflakes 163+97, spinners 108+108+91 placements) and the
  `SHOCKWAVE_SETTINGS` dict was hand-tuned on this layout's snowflakes/spinners specifically —
  low risk, and the FEATURE-props-pop rule (bright On on small props) still governs *feature*
  moments, which this change does not touch.
- [Accent density × longer duration = more overlap] `SHOCKWAVE_ACCENT_MS` 600 is still clipped to
  the next beat by `_end_at` for the backbeat; sparkle hits are `SPARKLE_TOP_N`-capped (8/section).
  Overlap pressure is bounded.
- [Rule #4 (one feature at a time) counts Shockwave as a FEATURE] Check `qa/rules.py::FEATURES` —
  Shockwave is in it. Many small accent Shockwaves could trip rule #4's overlap detector against a
  generator-placed Shockwave. Mitigation: the rule already merges same-type overlapping spans into
  one event; different-type overlaps remain possible → after implementing, run QA over a real
  cache (e.g. `data/analyses/orchestrator/e1a6805bc78a0643/instructions.json`) and if accent
  Shockwaves trip rule #4, exclude accent-sourced instructions (`source == "accents"`) from the
  FEATURES sweep — they are punctuation, not features (matches the module's own family comment).
- [Golden churn] Accent effect types + durations change in every rhythmic section. → One golden
  regen commit, expected diff = sparkle/backbeat rows only.

## Migration Plan

Single PR (branch `feat/rebalance-hit-vocabulary`). Order: D1 (move dict) → D2 → D3 → D4 → D5 →
golden regen last. Rollback = revert.

## Open Questions

- Should the *backbone* also rotate effect by section identity (an `ACCENT_ROTATION` mirroring
  `CARRIER_ROTATION`)? Deliberately deferred — measure the effect of D2/D3 first; the backbone's
  every-beat On is community-consistent.
