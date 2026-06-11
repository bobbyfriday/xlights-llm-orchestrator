## Context

Stage 2 of "set the stage." Stage 1 made `MusicBrief` a rich `SongDescription`; Stage 2 makes the `ShowPlan` a rich, grounded **creative brief** the Generator follows. Today `SectionPlan` is `{start_ms, end_ms, target_groups, effect_family, intensity, rationale}` and the Director's prompt is thin (and once hallucinated a trap narrative). We enrich the schema additively, deepen + ground the Director prompt in the Stage-1 description, render a reviewable `creative_brief.md` behind a hard checkpoint, and feed the new direction to the Generator. Reuses the exact patterns from Stage 1 (grounding signal, pure-render doc, hard checkpoint, cache-key bump).

## Goals / Non-Goals

**Goals:** rich grounded creative brief (concept, palette, group motifs, deep per-section direction, key-moment choreography, transitions); hard review checkpoint; the Generator follows it; no fabrication. Hermetic tests.

**Non-Goals:** new effect types/presets; the refine/visual-critique loop (built); per-stem reactive channels; auto-apply.

## Decisions

### Two registers: plain-language experience + grounded direction
The brief serves two readers. (1) **The human** — a plain, NON-MUSICAL "what the audience sees and feels": `ShowPlan.experience: str` (the overall visual/emotional vision in everyday terms) and per-section `look: str` (one line: what a viewer sees there). No music theory. (2) **The Generator** — the grounded, musical/technical direction (palette mapping, group motifs, per-section rationale citing dynamics/stems/accents). The render leads with the experience so a non-musician can confirm the vibe at a glance, with the technical direction below.

### Enrich `ShowPlan`/`SectionPlan` (additive, back-compat)
- **Global on `ShowPlan`:** `experience: str` (plain-language audience vision), `concept: str` (the artistic concept), `palette: ShowPalette {name, colors: list[str], mapping: str}`, `group_motifs: dict[str, GroupMotif {role, style, color}]`.
- **Per `SectionPlan` (all defaulted):** `look: str` (plain-language "what you see"), `palette: list[str]` (section colors), `effect_types: list[str]` (richer than the single `effect_family`, which stays), `motion: str`, `transition: str`, and `rationale` is kept (now required to cite the analysis). Existing fields unchanged → existing readers/tests still validate.
- **Key moments:** a `key_moments: list[KeyMoment {at_ms, kind, treatment}]` on `ShowPlan` (from accents/climax/featured_lyric_moments).

### Director: deepen + GROUND the prompt (no fabrication)
`director.render_input` already gets the brief + available groups + placeable types. Pass the **full Stage-1 SongDescription** (per-section intensity/stem_shares/musical_description/accents + dynamic_arc/harmony/journey/featured_lyric_moments) and the **instrumental/no-lyrics grounding signal** (reuse Stage 1's). The prompt demands BOTH registers: (a) a plain-language `experience` (what the audience sees/feels, NO music theory) + a per-section `look` line; and (b) the grounded direction — a concept; a palette mapped to dynamics+harmony; a role/motif per group; per-section direction that **cites** the section's intensity/stem_shares/accents (e.g. "piano 44% intro → soft megatree wash"); key-moment choreography; transitions from `transition_cues`. HARD RULE: never invent narrative/genre unsupported by the description; the title is not evidence.

### `creative_brief.md` (pure render) + hard design checkpoint
`render_creative_brief(plan) -> str`: **lead with the plain-language `experience`** (the audience vision), then concept → palette + language → group motifs → per-section direction (time, label, the plain `look` line, then intensity, palette, groups, effect types + motion, grounded rationale, transition) → key moments. Written to `data/.../<key>/creative_brief.md`. The top of the doc is readable without any musical knowledge. A **design-stage hard checkpoint** presents it and gates (attended → review/approve/abort; `--auto` → write + continue) — same injectable pattern as Stage 1's interpret checkpoint (`_interpret_review` → add `_design_review`; `run_pipeline` gains `design_checkpoint=`).

### Bust the design cache
The plan is cached at `_cache_path(key,"show_plan")`; an old thin plan would shadow the rich one. **Rename the stage key** (`show_plan` → `creative_brief`) so it regenerates — same fix as Stage 1.

### Generator follows the brief (thread the globals; section fields flow for free)
`generator.render_input(section, …)` already does `section.model_dump_json()`, so the new **section** fields (`look`/`palette`/`effect_types`/`motion`/rationale) appear automatically. The **globals** (`concept`, `group_motifs`) live on `ShowPlan`, so add **optional** params: `render_input(section, revision=None, *, concept="", motifs=None)` — back-compat so injected/test callers are unaffected. Pass them from `st.show_plan` at **both** call sites (`run.py:111` refine regen, `run.py:282` initial generate), filtering `motifs` to the section's `target_groups`. The effect_family/preset mechanics are unchanged — we feed richer *intent*, not new placement code.

### Grounding the Director (the brief flowing in is not enough)
`director.render_input` already dumps the full rich brief, so the data is present — but Stage 1 showed the **prompt rule** is what stops fabrication, not the data. The Director prompt carries the explicit **instrumental/no-lyrics signal** (derive from the brief: no `featured_lyric_moments` and no `narrative_summary` ⇒ instrumental) and the HARD rule: cite the description, never invent narrative/genre, the title is not evidence. This applies especially to the new `experience`/`concept` prose where invention is tempting.

## Risks / Trade-offs

- **Prompt cost/verbosity** — deeper Director prompt on the planner tier; one design pass per song, cached. Worth it (the foundation).
- **Schema growth** — additive + defaulted, so the Generator/refine/visual code keeps working; the Generator opts into the new fields.
- **Grounding still depends on the model** — Stage 1 showed prompt grounding works once the instrumental/no-lyrics signal is explicit; reuse it. The hard checkpoint is the human backstop.
- **Palette → real effect palettes** — the brief's named colors are *intent*; mapping to concrete `palette_id`/`C_BUTTON_Palette` strings stays the preset library's job (the Generator already emits palettes). We pass color intent, not raw strings.
- **Checkpoint friction** — two hard checkpoints now (description + brief); intended for the dial-in phase, `--auto` bypasses both.

## Open Questions

- Whether group_motifs should be derived per show or seeded from a reusable library of prop-type roles — start per-show, library later.
- Palette specification depth (named colors vs hex vs preset palette ids) — start named colors + mapping prose; tighten to concrete palettes if the Generator needs it.
