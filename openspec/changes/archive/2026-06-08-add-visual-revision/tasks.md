> **Build result (verified live on Gemini):** the visual critique is now MUSIC-AWARE — `render_input` feeds each section's intensity/label/neighbors; the critic judges darkness/staticness/energy *in context* and marks `severity=error` only for contextual defects. The Judge prompt elevates visual findings to first-class revision inputs; `refine.Finding` gained `section_index` (robust targeting, no scope parsing); `floor_visual_revisions` is a narrow backstop for critic-confirmed errors the Judge ignored; the loop extends its revision set with it. **90 hermetic tests pass** (4 new). LIVE: on our show the critic flagged the dark CHORUS (0.9 intensity) as error citing the intensity, while leaving the dark low-energy INTRO unflagged, and called the outro's build-vs-fade a sync warn — exactly the in-context judgment intended. Visual stays advisory to the objective gate. Roadmap: ⑩ revision log (decision/outcome flight-recorder for prompt tuning).

## 1. Music-aware critique (headline)

- [x] 1.1 `agents/visual_critic.py::render_input`: per section, include the **musical context** from `brief.sections[i]` — `intensity`, `label`, and neighbor labels (so "before a transition" is visible). Zip `media` with `brief.sections[:len(media)]` (aligned by sampler order); guard the cap edge (missing next-neighbor)
- [x] 1.2 Update the critic prompt: judge visuals **against the music here** (is darkness/staticness/energy appropriate or a defect *for this moment*?); assess **dynamics/variety** (dynamic, unique, not repetitive, not random) and **music-sync** (effects fit the energy/structure); mark `severity=error` only for *contextual* defects (dark mid-energy, repetitive, random, energy-mismatched), not darkness per se

## 2. Judge decides + Generator gets the visual issue

- [x] 2.1 `agents/judge.py`: prompt treats the (music-aware) `visual:*` findings as first-class judgment inputs → scoped `RevisionBrief`s for genuine problems, carrying a concrete visual fix. No deterministic visual-property→revision mapping; no contract change
- [x] 2.2 Ensure a visual-driven `RevisionBrief`'s `issue`/`suggested_fix` carries the critic's visual detail verbatim → `generator_mod.render_input(section, revision)` already surfaces it (verify the visual text reaches the regenerated section's prompt)

## 3. Section identity + narrow backstop (critic-confirmed defects only)

- [x] 3.0 Add `section_index: int | None = None` to `refine.Finding`; `visual_critic.to_findings` sets it from `VisualFinding.section_index` (QA findings leave it `None`). Additive/back-compat
- [x] 3.1 `refine.py` `floor_visual_revisions(findings, existing_revisions) -> list[RevisionBrief]`: for each finding with `metric` startswith `visual:`, `severity=="error"`, and non-`None` `section_index` not already covered by `existing_revisions`, synthesize a `RevisionBrief(section_index, issue=<visual detail>, suggested_fix="visual defect for this musical moment — regenerate to fit the music here")` — reads `finding.section_index` directly (no scope parsing). Pure + unit-testable
- [x] 3.2 `pipeline/run.py` loop: after the Judge/checkpoint decision and before regenerating, extend the revision set with `floor_visual_revisions(report.findings, revisions)`; record synthesized briefs in the anti-oscillation ledger
- [x] 3.3 Confirm the loop's existing per-iteration `visual_critique(st)` re-renders after a visual revision rebuild (⑧) — the next decision reflects the updated section (verify, no new mechanism)

## 4. Tests & verification

- [x] 4.1 `render_input` music context: per section it includes the section's `intensity`/`label`/neighbor labels aligned to `media` index (assert present in the built prompt). (The contextual *judgment* — intentional-dark-not-flagged — is verified LIVE in 4.6, not hermetically.)
- [x] 4.2 **Section-index threading:** `to_findings` sets `Finding.section_index` from `VisualFinding`; `floor_visual_revisions` reads it (no scope parsing) to target the right section
- [x] 4.3 Pure `floor_visual_revisions`: a `visual:*`/`severity=error` finding on section 2 not in `existing` → a `RevisionBrief(section_index=2)` carrying the visual detail; already-covered → no duplicate; **`warn`/`info` (e.g. an intentional dark lull) → NO floor**
- [x] 4.4 Hermetic loop: stub critic returns a `severity=error` section-2 finding + a Judge that returns NO revision → loop still regenerates section 2 (backstop) with the visual issue in its revision; ledger records it
- [x] 4.5 Hermetic loop: Judge DOES return a visual-driven revision → passed through (no duplicate backstop); a `warn` visual finding → no forced revision (Judge's call)
- [x] 4.6 Hermetic: **objective_score excludes visual** — acting on visual findings doesn't change `_obj`/the revert-stall decision; `refine=False` unchanged
- [x] 4.7 Live (gated, Gemini + xLights): `xlo run --refine --auto` on the dark-chorus show → the music-aware critic flags the chorus (dark at a high-energy moment) as error, the chorus gets a visual-driven revision and regenerates, and a later review-bundle frame for that section is lit (or the loop terminates within the cap having attempted the fix) — while an intentional quiet/dark moment is not flagged
