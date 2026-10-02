# add-phrase-gestures — design

> Executor note: anchors as of commit `1cd742d` (2026-07-07); re-locate by symbol if drifted.
> Corpus numbers from `corpus-alignment-2026-07` memory (17 community .xsq = 27,099 effects vs 3
> recent caches = 3,852): Morph 6.2%→0.7%, Curtain 2.7%→0.0%, Ripple 3.1%→0.4%,
> VU Meter 6.2%→0.2%, Garlands 0.5%↔ours 1.9%, Marquee 0.3%↔ours 1.9%.

## Context

`realize_section` (`packages/xlights-orchestrator/src/xlights_orchestrator/pipeline/generate.py`,
~line 263) assembles a section from deterministic layers gated by the treatment table
`_TREATMENT_LAYERS` (~line 85): bed, weave (cell fabric), accents, extras (composites + VU),
feature. Phrase-class effects (Morph/Curtain/Fill/Fan — `duration_class="phrase"` in
`pipeline/effect_meta.py`) have NO deterministic layer: `expand_weave` only places cellable types,
and `normalize_durations` (`pipeline/beats.py` ~line 665) clamps a phrase effect to ≤8 bars but
nothing *places* one. The model for a new single-instruction deterministic layer is
`place_vu_meter` (`pipeline/beats.py` ~line 630): pure function → `EffectInstruction | None`,
called from `realize_section` with a seed, tagged with `section_index`/`source`.

Rotation/rhyme convention: `CARRIER_ROTATION` + `section_carrier(seed, label)` in
`pipeline/weave.py` (~line 167) — keyed to `label_seed(label)` when the section has a recurring
identity, else the section index, so repeated choruses pick the same member. The phrase gesture
copies this exactly.

`fallback_weave` (weave.py ~line 203): texture cell = first cellable type from the section's own
`effect_types`, else **no texture at all** — one reason Ripple never appears.

VU gating: `place_vu_meter` is called under `if _layers["extras"]:` in `realize_section` (~line
367), and `extras` is True only for the `full` treatment.

## Goals / Non-Goals

**Goals:**
- Every `full`/`pulse` section carries one bounded phrase gesture (Morph/Curtain/Fill), rhymed
  across recurring sections.
- Carrier rotation and fallback texture reflect community shares.
- VU Meter appears in ordinary energetic sections, not only the peak stack.

**Non-Goals:**
- Making the weave cell phrase effects (they're phrase-class by definition — the catalog's
  duration taxonomy stands).
- Shape/Faces/Text staples (Shape rides `add-blend-vocabulary`'s reveal composite; Text/Faces have
  their own narrative pipelines).
- Marquee reduction (it is not in any deterministic rotation — its 1.9% comes from LLM choices;
  the prompt grounding sentence added by `rebalance-hit-vocabulary` is the lever there; measure
  again after these changes).
- Any Director/Generator schema change.

## Decisions

**D1 — `place_phrase_gesture` in `pipeline/beats.py`** (place it right after `place_vu_meter`,
same shape):

```python
PHRASE_ROTATION = ("Morph", "Curtain", "Fill")   # community staples the weave cannot cell
                                                  # (6.2% / 2.7% / 1.1% of the community corpus)

def place_phrase_gesture(section, rhythm, intensity, available_groups,
                         *, seed: int = 0, label: str | None = None) -> EffectInstruction | None:
```

- Effect choice: start from `PHRASE_ROTATION[(label_seed(label) if label else seed) % 3]`
  (import `label_seed` from `.weave` — beats.py must not create an import cycle: check first;
  if weave imports beats (it does — `from .beats import …`), put `label_seed` usage on the
  CALLER side instead: compute the rotation index in `realize_section`, where `label_seed` is
  already imported, and pass `seed` in — simplest cycle-free shape). Then filter by energy band:
  if `ENERGY_BAND[effect]` is ≥2 bands away from the section band (same rule as QA rule #3),
  step to the next rotation member.
- Target: the hero group if available, else the first available of the vocab's `peak_broad`
  (pass `vocab` like `place_beat_accents` does). One instruction only.
- Span: 4 bars (`4 * _bar_ms(rhythm)`), starting at the section's second bar boundary (a gesture
  that enters after the section establishes, community-style), clipped to the section end; skip
  entirely if the section is shorter than 6 bars.
- Settings: `effect_speed_setting(effect, intensity)`, section palette via `effect_palette`,
  `render_style="Per Preview"` for Fill/Curtain (a sweep must travel the group buffer — same
  rationale as the chase-family sweep rule in `_cell`) and `"Per Model Default"` for Morph;
  `T_CHOICE_LayerMethod: "Max"` when the target already carries a base (mirror how accents do
  `setdefault("T_CHOICE_LayerMethod", "Max")` in `realize_section`).
- Returns None when: intensity < 0.4, no target, no looks for the chosen effect.

**D2 — Call site + gating (generate.py).** Add a `"phrase"` key to `_TREATMENT_LAYERS`:
`full: True, pulse: True, feature: False, gesture: False, rest: False`. In `realize_section`,
after the weave block and before extras:

```python
if _layers.get("phrase"):
    pg = place_phrase_gesture(section, rhythm, _si, st.available_groups,
                              seed=(label_seed(_label) if _label else si))
    if pg is not None:
        pg.section_index, pg.source = si, "phrase"
        kept.append(pg)
```

`source="phrase"` is a NEW provenance tag: add `"phrase"` to `SOURCE_TAGS` in
`scripts/measure_fabric.py` (~line 84) so attribution reports stay complete.

**D3 — Carrier rotation rebalance (weave.py ~line 167).**
`CARRIER_ROTATION = ("SingleStrand", "Bars", "SingleStrand", "Wave")` — Garlands out (4× its
community share from rotation alone), SingleStrand double-weighted (community's 28.5% workhorse).
Keep the tuple length 4 so label-keyed rhyming distribution stays uniform. Update the comment.
Garlands remains placeable (LLM can still choose it); only the deterministic rotation drops it.

**D4 — Fallback texture (weave.py `fallback_weave` ~line 216).** When the section's own
`effect_types` yield no cellable texture, use `"Ripple"` (community 3.1%, cellable, 55 mined
looks) on the existing `tex_groups` instead of omitting the texture recipe. Only when `tex_groups`
is non-empty — a section with no non-accent target groups still gets carrier-only.

**D5 — VU in pulse sections (generate.py).** Move the `place_vu_meter` call out from under
`_layers["extras"]` to its own gate: `if _layers["extras"] or _treatment == "pulse":`. Everything
else about VU (one per section, `VU_MIN_INTENSITY`, seeding) is unchanged. Rationale: community
uses VU as an ordinary reactive texture (6.2% pooled; one show runs it as its main bed), not a
peak-only garnish; `pulse` is the workhorse energetic treatment.

## Risks / Trade-offs

- [Layer pressure: +1 instruction per full/pulse section] The 4-layer budget (`clamp_layer_budget`)
  and the emitter's `MAX_LAYERS` still governs; the gesture is one span on one target. If the
  budget drops other rows at peaks, the drop counter will show it — check the emit report after
  golden regen (`skipped` reasons mentioning layer budget).
- [Morph "Per Model Default" on a group of small props reads as noise] Catalog places Morph on
  tree/arches/matrix; the target here is hero/broad. If the live watch disagrees, flip Morph to
  "Per Preview" — one string.
- [Rule #4 feature overlap] Morph/Curtain/Fill are not in `qa/rules.py::FEATURES` — no conflict.
- [Carrier tuple change reshuffles every show's carriers] Pure golden churn, by design; recurring
  labels still rhyme (same keying).
- [VU in pulse sections overlapping the weave] VU is `Per Preview` on a wide group and section-
  spanning — it will be blended-over or layered by `_free_layer`; the existing wash-occlusion
  guard doesn't treat VU as opaque (only On/Color Wash/Fill), which is correct (VU is sparse bars).

## Migration Plan

Single PR (branch `feat/phrase-gestures`). Independent of the other three changes in this series;
golden conflicts are regen-trivial (regen after rebase). Order: D3+D4 (small, weave) → D1+D2 →
D5 → golden regen. Rollback = revert.

## Open Questions

- Should the gesture also fire in `feature` sections (they keep a `feature` layer)? Deliberately
  no for now — `feature` sections spotlight ONE hero element; a second traveling gesture competes.
  Revisit with live-watch evidence.
