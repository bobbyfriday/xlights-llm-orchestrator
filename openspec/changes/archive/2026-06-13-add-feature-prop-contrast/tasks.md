## 1. Implementation

- [x] 1.1 Director prompt (`agents/director.py`): add the "feature props pop" rule — featured accent/sparkle prop groups are the bright, high-contrast focal element in a light color over a different-hued bed, kept bright even in calm sections.
- [x] 1.2 Generator prompt (`agents/generator.py`): same realization guidance + the particle-effect caveat (named particle effects need a large canvas; on small props light them directly) + pin the feature color via explicit `palette_colors`.
- [x] 1.3 `pipeline/run.py` (generate + regen color passes): fill `palette_colors` only when the instruction left it empty, so an LLM-pinned color survives the section-palette override.

## 2. Tests (hermetic)

- [x] 2.1 Assert the director prompt contains the feature-props-pop guidance.
- [x] 2.2 Assert the generator prompt contains the feature-props-pop guidance + particle caveat + pin-the-color note.
- [x] 2.3 An explicit `palette_colors` survives the run.py color pass; an empty one takes the section family.
- [x] 2.4 Full suite passes.

## 3. Verify + land

- [x] 3.1 Live: regenerate Christmas Canon's snow section(s) and confirm the flakes read (white-ish props on a contrasting bed, visible at normal exposure).
- [x] 3.2 Archive, commit, push branch, open PR (user merges).

## 4. Deterministic floor (added after steering proved unreliable)

- [x] 4.1 `pipeline/beats.py`: `feature_prop_contrast(instructions, section)` — featured accent prop groups' base lighting takes the section's lightest color at a bright level.
- [x] 4.2 `pipeline/run.py`: apply the floor per section in the generate + regen paths.
- [x] 4.3 Tests: floor recolors snow to the lightest color + brightens; no-op without an accent group.
