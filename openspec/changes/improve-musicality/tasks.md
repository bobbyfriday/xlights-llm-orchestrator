## 1. Phase 1 — repetition identity

- [x] 1.1 Add `section_identity(si, repetition_map) -> str | None` (beats.py, near
  `escalation_level`; a label counts only when it recurs). Unit tests: recurring label found,
  one-off → None, empty map → None.
- [x] 1.2 Key `section_carrier` on the identity label when present (`hash(label) % len(CARRIER_ROTATION)`),
  index otherwise; thread the label from `realize_section`. Test: two sections sharing a label get
  the SAME carrier; adjacent one-offs still differ. (Used a STABLE md5-derived label hash, not
  builtin `hash`, so the choice is process-independent and never churns the golden.)
- [x] 1.3 Key the peak-composite pick (`_PEAK_COMPOSITES`) and the expanded-palette rotation offset
  on the same label. Test: repeated choruses share composite + palette order.
- [x] 1.4 Spend escalation structurally in `realize_section`: occurrence ordinal raises
  `coverage_cap` (+1 group/step), tightens accent stride one step, final occurrence adds the
  sparkle-contrast layer when accent props exist. Existing hard caps bound it. Tests: occurrence 1
  vs final differ in coverage/density/layer count; caps never exceeded.
- [x] 1.5 New `qa/musicality.py` with the **repetition-rhyme** advisory metric (Jaccard of
  `(target, effect_type)` per label + carrier equality); wire into `qa/__init__.evaluate` as
  advisory. Tests: rhyming show scores high; index-rotated (pre-change) fixture scores low; no
  recurring labels → neutral.
- [x] 1.6 Regenerate the golden (`XLO_REGEN_GOLDEN=1`), review the diff (carriers now stable per
  label), full suite green. NOTE: the golden fixture is a ONE-OFF show (no recurring labels), so
  Phase 1's re-keying is a deliberate no-op for it and the snapshot stays byte-identical (verified
  `git diff --stat`) — exactly the intended behavior (one-offs keep index-keyed variety). The
  recurring-label re-keying is proven by `tests/test_realize_identity.py`.

## 2. Phase 2 — section treatments

- [x] 2.1 Add `SectionPlan.treatment` (defaulted `""` for old cached plans); expose in
  `brief_editor.py`'s field list; document values in the schema docstring.
- [x] 2.2 Deterministic fallback `resolve_treatment(section, peaks)` per design table; Director
  prompt gains the treatment doctrine block (choose per section; withhold, don't just dim).
- [x] 2.3 Branch `realize_section` on treatment per the design matrix (layers withheld, not dimmed);
  `rest`/`gesture` respect the 2-consecutive-sections bed floor. Tests: each treatment's layer
  inventory; fallback mapping; floor injection.
- [x] 2.4 Key `qa/coverage.py` expectations to intensity + treatment (`gesture`/`rest` exempt from
  the darkness objective error, advisory note instead). Tests: dark rest section no longer errors;
  dark high-energy section still does.
- [x] 2.5 Add **dynamic-range** and **focus-budget** advisory metrics to `qa/musicality.py`.
  Tests: wall-to-wall bright show flagged; quiet section running 4 moving systems flagged;
  well-shaped show clean.
- [x] 2.6 Regenerate golden, review (verses now visibly sparser), full suite green. Reviewed diff:
  section 0 (intensity 0.45 → `feature`) drops 37→20 effects (weave carrier + Twinkle texture +
  composite + VU withheld, dim bed added); the `full` peak (section 1) is byte-identical; global
  effects unchanged. Exactly the intended "verses now visibly sparser".

## 3. Phase 3 — transitions, color script, phrase dynamics

- [x] 3.1 New `pipeline/transitions.py::place_transitions(st, instrs)` — riser (2-bar ramp chase
  ending at a rising boundary), blackout-before-drop (gate the final beat before a detected drop
  landing on a downbeat), sweep handoff (lateral). Pure signal math from energy arc + downbeats +
  `transition_cues_ms`; instructions tagged with the OUTGOING section index; idempotent via a
  marker key. Unit tests per transition kind + idempotence. (Riser vs drop are separated by the
  APPROACH slope — a build climbs in; a drop steps out of a flat/low approach.)
- [x] 3.2 Run the pass in `generate_instructions` and after refine-loop/`xlo regen` splices, before
  `finalize_effects`. Test: regenerating the incoming section preserves the boundary riser.
  (Wired as the FIRST step of `finalize_effects`, the one seam all three paths already share.)
- [x] 3.3 `apply_color_script(plan, repetition_map)` post-pass (anchor injection, chorus signature
  pair, bridge contrast) after Director planning and after section redesigns. Tests: anchor present
  in every section; chorus occurrences share the pair; bridge leads with the complement.
- [x] 3.4 Phrase dynamics in `realize_section`: energy-arc-shaped brightness curves on ≥2-bar
  beds/washes (rising/falling/flat). Tests: rising slice → ramp, flat → constant; features/accents
  untouched. (The 8-bar accent-boost swell is deferred — see note; the per-instruction energy-shaped
  bed curve covers the spec scenario "a building bed swells".)
- [x] 3.5 Regenerate golden, full suite green. Reviewed diff: +1 riser (SingleStrand on SEM_ALL,
  8000→12000, tagged to outgoing section 0) into the rising boundary; +2 energy-shaped brightness
  value curves (section 0's rising bed swells; the flat peak keeps constant levels).

## 4. Land

- [ ] 4.1 Each phase is its own PR (branch per phase); do not commit to `main` directly. DEFERRED
  to the orchestration harness: per instruction, all three phases land in order on the single branch
  `change/improve-musicality` as one commit per phase; the harness opens the PR after verification.
- [ ] 4.2 Render a before/after visual-critique bundle on a reference song per phase. DEFERRED:
  requires a live/GUI render (non-hermetic); the golden diffs + unit tests stand in for the
  automated check, and the deterministic diffs were reviewed (risers, sparser verses, phrase swells).
- [x] 4.3 Document the treatment vocabulary and new advisory metrics where QA/refine behavior is
  documented; note the golden-regeneration policy. (Docstrings in `show_plan.SectionPlan.treatment`,
  `pipeline/generate._TREATMENT_LAYERS`, `qa/musicality.py`, `qa/coverage.py`, `pipeline/transitions.py`,
  `pipeline/color_script.py`; the golden-regeneration policy is captured in the tasks + commit msgs.)
