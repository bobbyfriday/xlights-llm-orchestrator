## Why

Generated shows are technically correct but read as **samey and scattered** next to a hand-sequenced
show. The causes are structural, not tuning:

- **One recipe everywhere.** `realize_section` applies the same stack (bed + weave fabric + beat
  accents + sparkle contrast) to every section; only brightness and coverage scale with intensity. A
  quiet verse is "the chorus, but dimmer" — nothing is ever truly absent, so the peak has no contrast
  to land against. Coverage QA reinforces this by treating darkness as an objective error regardless
  of section energy.
- **Variety is keyed to position, not musical identity.** `section_carrier(section_index)` rotates the
  weave carrier by index, so chorus 1 and chorus 2 — which `repetition_map` *knows* are the same music
  — get different carriers (and different peak composites via `_PEAK_COMPOSITES[si % n]`). The
  pipeline injects difference exactly where a sequencer would enforce sameness; repeated music never
  visually rhymes, so the show reads as arbitrary. `repetition_map` is currently used only to bump
  intensity.
- **Section boundaries are butt joints.** The harmony analyst emits `transition_cues_ms` and the
  Director writes a `transition` field, but nothing downstream consumes either. Hand shows live on
  risers into choruses, a one-beat blackout before the drop, and sweep handoffs.
- **No show-level color story and no phrase-level dynamics.** Palettes are chosen per section with no
  cross-section constraint, and brightness value curves only fire on >15s washes at intensity ≥ 0.7,
  so nothing swells or decays with the music's 2/4/8-bar phrasing.
- **The refine loop can't protect any of this** because no metric measures it — what isn't measured
  gets optimized away.

## What Changes

Phased; each phase lands independently and is valuable alone.

**Phase 1 — repetition identity (theme & development):**
- Key the weave carrier, peak-composite choice, and palette rotation to the section's
  `repetition_map` **label** (chorus/verse/...) instead of the section index; one-off sections keep
  index-keyed rotation.
- Spend escalation across occurrences structurally, not just as brightness: later occurrences of a
  label gain coverage and accent density; the final occurrence gains a layer.
- New advisory QA metric **repetition-rhyme**: instruction-similarity between sections sharing a
  label, so the Judge sees when a repeat doesn't rhyme.

**Phase 2 — section treatments (texture contrast):**
- A `treatment` field on `SectionPlan` (`full` | `feature` | `pulse` | `gesture` | `rest`) chosen by
  the Director, with a deterministic energy-based fallback. `realize_section` **withholds** layers per
  treatment instead of only dimming them.
- Coverage QA expectations keyed to section energy/treatment so deliberate darkness stops being an
  objective error.
- New advisory QA metrics **dynamic-range** (contrast between the quietest and loudest sections) and
  **focus budget** (concurrent moving systems vs. energy).

**Phase 3 — connective tissue (transitions, color script, phrase dynamics):**
- A `transitions` pass that consumes section boundaries + energy arc + the brief's transition cues:
  riser into a rising boundary, one-beat blackout before a detected drop, sweep handoff on lateral
  moves.
- A deterministic show-level color script: a persistent anchor color across all sections, a signature
  pair owned by the chorus label, deliberate contrast at the bridge.
- Phrase-level brightness value curves on beds/washes shaped by the in-section energy arc and 8-bar
  phrase boundaries.

## Capabilities

### New Capabilities
<!-- none — all changes deepen existing generation/refinement behavior -->

### Modified Capabilities
- `show-orchestration`: per-section realization gains repetition-identity keying, treatment
  archetypes, a boundary-transition pass, a show-level color script, and phrase-shaped dynamics.
- `show-refinement`: QA gains advisory musicality metrics (repetition-rhyme, dynamic-range, focus
  budget) and energy-aware coverage expectations.

## Impact

- `pipeline/weave.py` (`section_carrier`, carrier rotation), `pipeline/generate.py`
  (`realize_section`, `_PEAK_COMPOSITES` keying, treatment branching, phrase curves),
  `pipeline/beats.py` (escalation spending, accent density), new `pipeline/transitions.py`,
  new `pipeline/color_script.py` (or a pass in `show_plan` realization).
- `show_plan.py` (`SectionPlan.treatment`), `agents/director.py` (treatment + transition guidance),
  `brief_editor.py` (expose the new field).
- `qa/coverage.py` (energy-keyed expectations), new `qa/musicality.py` (advisory metrics), `qa/__init__.py`.
- Tests: hermetic coverage per phase; the golden pipeline test will need regeneration once per phase
  (`XLO_REGEN_GOLDEN=1`) since generation output changes deliberately.
- Risk profile: Phase 1 changes which effects appear where (visual change, no schema change); Phase 2
  adds a schema field (defaulted, backward compatible); Phase 3 is additive passes.
