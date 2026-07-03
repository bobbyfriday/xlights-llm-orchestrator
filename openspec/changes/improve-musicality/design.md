## Context

All per-section realization now flows through one function, `generate.realize_section` (shared by
first-pass generation, the refine loop, and `xlo regen` since the consolidation in PR #44), and all
whole-list passes through `generate.finalize_effects`. That gives this change exactly two seams to
work in — treatments/identity/dynamics inside `realize_section`, transitions/color script as
list-level passes before `finalize_effects` — with no duplication risk.

Available signals, already computed and cached: `MusicBrief.repetition_map` (label → recurring
section indices), `transition_cues_ms`, per-section intensity, the full `energy_arc`,
beats/downbeats (`section_rhythm`), stems, and key moments. Nothing below requires new analysis.

## Goals / Non-Goals

**Goals:**
- Repeated music visually rhymes; escalation is structural (layers/coverage/density), not just gain.
- Quiet sections can be genuinely sparse or dark without QA punishing them.
- Section boundaries are composed (risers/blackouts/handoffs), not butt joints.
- All new QA metrics are **advisory** (`objective=False`) — they inform the Judge, never gate the
  objective score, so the refine loop's convergence properties are untouched.
- Deterministic and code-owned wherever possible; the LLM chooses *intent* (treatment, palette
  direction), code realizes it.

**Non-Goals:**
- No new audio analysis or analyzer schema changes.
- No change to the emitter, layer budget, or occlusion rules — transitions and treatments compose
  with `finalize_effects` as-is.
- No lyric-word-level effects (a later change; needs alignment confidence work).
- Phase 3's color script does not add new Director round-trips — it is a deterministic post-pass.

## Decisions

**1. Identity keying: label hash, index fallback.**
Add `section_identity(si, repetition_map) -> str | None` (the label whose indices contain `si`, if
that label recurs). `section_carrier` and the peak-composite pick key their rotation on
`hash(label) % len(rotation)` when an identity exists, else on the index as today. Palette rotation
offset (`effect_palette`'s `index` interplay stays per-effect; the *expanded palette* order is keyed
per label). Rationale: zero schema change, one function, and one-off sections keep today's variety.

**2. Escalation spends structurally.**
`escalation_level` (0..1 across occurrences) already exists. Use it beyond intensity: occurrence
ordinal raises `coverage_cap` by +1 group per step, tightens accent stride one step, and the final
occurrence adds one extra layer (the sparkle/feature contrast layer if the layout has accent props).
Bounded by existing hard caps (`clamp_hard_caps`, `clamp_layer_budget`) so it cannot blow the budget.

**3. Treatments are a realization contract, not a prompt suggestion.**
`SectionPlan.treatment: Literal["full","feature","pulse","gesture","rest"] | "" = ""` (defaulted —
old cached plans validate). Director prompt gains a short doctrine block; the deterministic fallback
when empty: intensity ≥ peak-band → `full`; ≥ 0.5 → `pulse`; ≥ 0.25 → `feature` if the layout has a
focal prop else `pulse`; < 0.25 → `gesture`; an explicit near-zero (< 0.1) → `rest`.
`realize_section` includes layers per treatment:

| treatment | bed | weave | accents | composites/VU | feature |
|-----------|-----|-------|---------|---------------|---------|
| full      | ✓   | ✓     | ✓       | ✓             | ✓       |
| pulse     | ✓   | —     | ✓       | —             | ✓       |
| feature   | dim | —     | sparse  | —             | ✓ (hero)|
| gesture   | —   | one carrier recipe on ≤2 groups | — | — | — |
| rest      | dim, ≤2 groups | — | — | — | — |

**4. Coverage QA keys expectations to energy + treatment.**
`qa/coverage.py` scales its expected-lit threshold by section intensity (roughly the same curve as
`coverage_cap`), and `gesture`/`rest` sections are exempt from the darkness error entirely (they get
an advisory note instead). This is the single QA change with objective-score impact; it *loosens*
only, so existing passing shows keep passing.

**5. Transitions are an instruction-list pass, tagged to the outgoing section.**
New `pipeline/transitions.py`: `place_transitions(st, instrs) -> list[EffectInstruction]`, run in
`generate_instructions` and after refine-loop splices, **before** `finalize_effects`. Detection is
pure signal math: boundary energy delta ≥ riser threshold → a 2-bar brightness-ramp chase on a broad
group ending at the boundary; delta ≥ drop threshold with a downbeat landing → gate all instructions
in the final beat before the boundary (blackout-before-hit); otherwise lateral → optional sweep
handoff. Transition instructions carry the **outgoing** section's `section_index` (they occupy its
time range), so regenerating the incoming section never orphans them; idempotence via a
`extra_settings` marker key so re-running the pass after a splice replaces rather than stacks.

**6. Color script is a deterministic plan post-pass.**
`apply_color_script(plan, repetition_map)`: anchor = the most frequent resolvable color across
section palettes (injected into any section missing it); the chorus label's sections get a shared
signature pair (their two most hue-distant colors, reused verbatim across occurrences); the
lowest-recurrence mid-song section (bridge heuristic) gets `ensure_contrast`'s complement pushed to
front. Runs right after the Director produces the plan and after any section redesign. No LLM call.

**7. Phrase dynamics ride existing value-curve helpers.**
In `realize_section`, beds/washes spanning ≥ 2 bars get a brightness curve shaped by the section's
energy-arc slice: rising slice → `brightness_ramp(lo, hi)`, falling → reversed, flat → none (today's
behavior). 8-bar phrase starts (downbeat grid) get a one-beat swell on the bed via the accent layer's
existing boost mechanism. Only beds/washes — features and accents keep crisp levels.

**8. Advisory metrics live in a new `qa/musicality.py`.**
- *repetition-rhyme*: for each recurring label, Jaccard similarity of `(target, effect_type)` sets
  between occurrences, plus carrier equality; score = mean over labels.
- *dynamic-range*: normalized spread between the min and max section of mean(brightness ×
  lit-group-fraction); low spread → "wall-to-wall brightness" finding.
- *focus-budget*: per section, peak count of concurrent distinct moving-effect systems
  (`MOTION_EFFECTS` targets grouped by effect_type); flag when it exceeds an energy-keyed budget
  (quiet: 1, mid: 2, peak: 3+bed).
All emit `objective=False` findings routed through the existing `source_of` metric naming
(`musicality:rhyme` etc.) so the revision log distinguishes them.

## Risks / Trade-offs

- [Golden test churn each phase] → Regenerate deliberately per phase with `XLO_REGEN_GOLDEN=1` and
  review the diff; the golden exists to catch *accidents*, and these are intentional.
- [Treatment withholding could produce a near-black show if the Director over-uses `rest`] → The
  deterministic fallback only assigns `rest` below 0.1 intensity; QA's dynamic-range metric flags a
  show that is *all* quiet exactly like one that is all loud; hard floor: at most 2 consecutive
  non-`full`/`pulse` sections get a bed injected.
- [Blackout-before-drop gating could fight the occlusion guard's ordering] → The pass runs before
  `finalize_effects`, and gating only trims end times (never reorders), so occlusion logic sees
  final geometry.
- [Label hashing gives an unlucky carrier for a whole show] → The Director's explicit weave carrier
  (when the LLM picked a distinctive one) still wins, exactly as today (`diversify_carrier` only
  swaps defaults).
- [More advisory findings → noisier Judge input] → Each metric emits at most one finding per
  label/section with a hard cap, mirroring `qa/variety`'s style.

## Open Questions

- Should the bridge heuristic come from the LLM (a `bridge` flag on SectionPlan) instead of
  "lowest-recurrence mid-song section"? Defaulting to the heuristic; revisit if it misfires.
- Whether `treatment` should eventually gate the *generator prompt* per treatment (smaller prompts
  for `gesture`/`rest`) — a cost lever, out of scope here.
