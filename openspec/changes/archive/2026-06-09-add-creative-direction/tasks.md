> **Build result (verified live on Gemini):** enriched `ShowPlan`/`SectionPlan` (additive/back-compat) with `experience` (plain-language audience vision) + `concept`/`palette`/`group_motifs`/`key_moments` and per-section `look`/`palette`/`effect_types`/`motion`/`transition`; deepened + GROUNDED Director prompt (instrumental signal + 'cite the description, no fabrication, title isn't evidence'); `render_creative_brief` (pure render, leads with the plain `experience`); hard design checkpoint (`_design_review`, attended; --auto bypass); design cache busted (show_plan→creative_brief); Generator `render_input` takes optional `concept`/`motifs` threaded at both call sites (back-compat). **127 hermetic tests pass** (5 new). LIVE: Director on the rich brief produced a grounded `creative_brief.md` — a non-musical campfire→celebration experience, palette tied to the real harmony (G-major warmth / E-minor melancholy / C7 tension), per-group roles, piano-led intro (6-stem) given a distinct candlelight treatment, NO hallucination. Note: two attended checkpoints now (interpret + design) — use --auto for unattended.

## 1. Schema: enrich ShowPlan into a creative brief (additive)

- [x] 1.1 `show_plan.py`: add `ShowPalette {name, colors: list[str], mapping: str}`, `GroupMotif {role, style, color}`, `KeyMoment {at_ms, kind, treatment}`
- [x] 1.2 `ShowPlan`: add `experience: str` (plain-language audience vision), `concept: str`, `palette: ShowPalette | None`, `group_motifs: dict[str, GroupMotif]`, `key_moments: list[KeyMoment]` (all defaulted/back-compat)
- [x] 1.3 `SectionPlan`: add `look: str` (plain-language "what you see"), `palette: list[str]`, `effect_types: list[str]`, `motion: str`, `transition: str` (keep `effect_family`/`intensity`/`rationale`; all defaulted)

## 2. Director: deepen + ground

- [x] 2.1 `director.render_input`: pass the FULL Stage-1 SongDescription (per-section intensity/stem_shares/musical_description/accents + dynamic_arc/harmony/journey/featured_lyric_moments) + the instrumental/no-lyrics grounding signal
- [x] 2.2 Deepen the Director prompt: a plain-language `experience` (what the audience sees/feels, NO music theory) + per-section `look`; AND the grounded direction — concept; palette mapped to dynamics+harmony; a role/motif per group; per-section direction that CITES the section's intensity/stem_shares/accents; key-moment choreography (accents/climax/featured lyrics); transitions from transition_cues. HARD RULE: no invented narrative/genre; the title is not evidence

## 3. Render + hard checkpoint + cache bust

- [x] 3.1 `render_creative_brief(plan) -> str`: pure Markdown — **lead with the plain-language `experience`**, then concept, palette + language, group motifs, per-section direction (time/label/**plain `look`**/intensity/palette/groups/effect-types+motion/grounded rationale/transition), key moments; write to `data/.../<key>/creative_brief.md` (top readable without musical knowledge)
- [x] 3.2 `pipeline/run.py`: a `_design_review` interpret-style gate + `design_checkpoint=` param — after the plan, render the brief and gate (attended → approve/abort; `--auto` → write + continue); CLI passes it when not `--auto`
- [x] 3.3 **Bust the design cache:** rename the stage key `show_plan` → `creative_brief` so old thin plans don't shadow

## 4. Generator follows the brief

- [x] 4.1 `generator.render_input(section, revision=None, *, concept="", motifs=None)` — back-compat optional params (section fields flow via `section.model_dump_json()` already); include `concept` + the section's `group_motifs` in the prompt. Pass from `st.show_plan` at BOTH call sites (`run.py:111` refine regen, `run.py:282` initial generate), filtering motifs to the section's `target_groups`

## 5. Tests & verification

- [x] 5.1 Schema: enriched `ShowPlan`/`SectionPlan` is additive — an old-shape plan (only the original fields) still validates; new fields default
- [x] 5.2 `render_creative_brief`: renders all layers (**plain-language `experience` first**, then concept/palette/group motifs/per-section direction incl. the `look` line/key moments) from a structured plan (TestModel-stubbed prose); deterministic
- [x] 5.3 Design checkpoint gates: attended stub stops for review; `--auto` writes + continues; generation proceeds on approve
- [x] 5.4 `generator.render_input` includes the section palette + its group motifs + effect_types/motion + concept (assert present in the built prompt); back-compat — old call `render_input(section)` / `render_input(section, revision=…)` still works
- [x] 5.4a Director input carries the **grounding signal** (instrumental flag + the hard "cite the description / no fabrication" rule is in the prompt; the no-hallucination behavior itself is verified live in 5.6)
- [x] 5.5 Cache-bust: an old `show_plan.json` doesn't shadow the new `creative_brief` stage; refine/visual-critique unaffected
- [x] 5.6 Live (gated): re-design mad russian → a grounded `creative_brief.md` (palette tied to the cinematic-rock dynamics; piano-led intro a distinct treatment; choruses escalate) with NO fabricated narrative; the checkpoint pauses; a generated section's prompt reflects the brief
