## ADDED Requirements

### Requirement: Each stage is a file-in, file-out command over the song's cache dir
The `xlo` CLI SHALL expose the stages `analyze`, `groups`, `validate-brief`, `realize`, `apply`, `qa`, `stills`, `finalize`, `video-plan`, and `init-layout`. Each SHALL take `--song <mp3>` (or `--cache <dir>`), read its inputs from and write its outputs to the song's cache dir (`<song-slug>--<hash>/`), print a short summary to stdout, and exit non-zero with a message naming the missing input when a prerequisite file is absent. No stage SHALL call a model API.

#### Scenario: Missing prerequisite
- **WHEN** `xlo realize` runs before `creative_brief.json` exists
- **THEN** it exits non-zero naming `creative_brief.json` and writes nothing

#### Scenario: Resume by files
- **WHEN** `xlo analyze` has already produced its outputs for a song
- **THEN** re-running it reuses the cached analysis (unless `--no-cache`) and regenerates only the digest

### Requirement: Analyze writes a bounded, human-readable analysis digest
`xlo analyze` SHALL write `analysis_digest.md` alongside the cached analysis containing: duration, tempo, meter; the sections (downbeat-snapped, from lyric markers or audio segmentation) with per-section normalized energy, dominant stems, and chord density; the timed lyric lines and repeated lines; detected instrument entrances; key and mood descriptors. The digest SHALL stay under 20 KB for a typical song and SHALL be fully deterministic from the analysis.

#### Scenario: Digest content
- **WHEN** analysis completes for a vocal song with stems
- **THEN** the digest lists each section with its time range, energy, dominant stem, and the lyric lines it contains

#### Scenario: Determinism
- **WHEN** the digest is regenerated from the same cached analysis
- **THEN** the file is byte-identical

### Requirement: Groups writes the brief vocabulary and schema
`xlo groups` SHALL probe (or reuse the layout-fingerprinted cache of) the targetable groups, and write `vocab.json` (targetable groups, placeable effect types, cellable carrier types, cookbook scene ids, the song's stems, the named colors) and `creative_brief.schema.json` with those values as enums, before any brief exists.

#### Scenario: Schema precedes the brief
- **WHEN** `xlo groups` runs on a fresh song dir
- **THEN** `vocab.json` and `creative_brief.schema.json` exist and the schema's group and scene enums match `vocab.json`

### Requirement: Validate-brief reports structured, actionable errors
`xlo validate-brief` SHALL load `creative_brief.json` as a `ShowPlan` and check: sections are ordered, non-overlapping, and cover the song within tolerance; every group field names a targetable group; every effect field names a placeable type; `scene_id`, `follow_stem`, `pulse_on`, and palette names are in the vocabulary; `fabric.carrier` is cellable; `intensity` is within 0–1. It SHALL write `validation.json` as `{ok, errors:[{path, message, allowed}], warnings:[...]}` and exit non-zero when `errors` is non-empty. Section boundaries that are not on a downbeat SHALL be warnings, not errors.

#### Scenario: Unknown group
- **WHEN** a section's `target_groups` contains a name not in the vocabulary
- **THEN** `validation.json` has an error at `sections[i].target_groups[j]` with the allowed group names, and the command exits non-zero

#### Scenario: Gap between sections
- **WHEN** two consecutive sections leave more than the tolerance uncovered
- **THEN** an error names both sections and the gap

#### Scenario: Off-downbeat boundary
- **WHEN** a section starts between downbeats
- **THEN** `validation.json` carries a warning for that section and `ok` remains true if there are no errors

### Requirement: The brief directs the fabric through optional per-section fields
`SectionPlan` SHALL accept an optional `fabric` object with `carrier` (a cellable effect type), `alternation` (`chase|pingpong|all|sparse`), `cell_beats` (1–8), and `blend` (a layer-method name). Each field SHALL be optional; realization SHALL use the field when present and the deterministic default when absent.

#### Scenario: Directed carrier and alternation
- **WHEN** a section's fabric names `SingleStrand` with `pingpong` at 2 beats
- **THEN** the realized weave's carrier cells are SingleStrand, alternate ping-pong across the rhythm pool, and span two beats each

#### Scenario: Absent fabric
- **WHEN** a section has no `fabric` block
- **THEN** the section is realized exactly as today's fallback weave would (carrier on the rhythm pool, sparse texture from `effect_types`)

### Requirement: Realize is deterministic and LLM-free
`xlo realize` SHALL turn `creative_brief.json` into `instructions.json` using only the brief, the analysis, the vocabulary, and the preset library: per-section weave from the fabric fields with the deterministic fallback; look ids from the catalog's candidate rotation; render styles from the per-effect fallback; then the unchanged layers (energy bed and peak fill, beat accents, curated triggers, climax flashes, phrase curves, curated composites, counter-rotation, treatment gating, feature-prop contrast, singing faces, matrix text, layer budget, wash-occlusion guard). The same brief and analysis SHALL yield byte-identical instructions.

#### Scenario: Reproducible
- **WHEN** `xlo realize` runs twice on the same inputs
- **THEN** `instructions.json` is byte-identical

#### Scenario: Scene stack realized
- **WHEN** a section names a cookbook scene with an archetype casting
- **THEN** the instructions carry that scene's layered stack on the cast groups with the cookbook's blend modes

### Requirement: Apply re-emits the whole show and records placements
`xlo apply` SHALL create a clean-slate animation sequence in the running xLights (replacing an already-open one only when permitted by the existing clean-slate rules), additively place every instruction, and write `applied.json` recording each instruction's placement outcome (placed, or skipped with reason). It SHALL NOT remove or mutate individual effects. `--render` SHALL additionally trigger a full render and wait for it.

#### Scenario: Re-apply after a brief edit
- **WHEN** the brief is edited, realized, and `xlo apply` runs again
- **THEN** the sequence is rebuilt from the full instruction list and `applied.json` reflects the new placements

#### Scenario: Target-missing skips are reported
- **WHEN** an instruction targets a group xLights rejects
- **THEN** `applied.json` marks it skipped with the reason and the command's summary counts it

### Requirement: QA writes findings for the human and Claude to act on
`xlo qa` SHALL evaluate `instructions.json` (and the rendered `.fseq` series when present) with the deterministic checks — sync, placement, rules, variety, musicality, coverage — plus a **dark mid-energy** finding (an energetic section whose rendered coverage stays below the floor) and a **static section** finding (an energetic section whose coverage barely varies), and write `qa.json` with per-finding `section_index`, severity, metric, and a plain-language fix. Nothing in `qa.json` SHALL gate any other stage.

#### Scenario: Dark mid-energy
- **WHEN** a section with normalized energy ≥ 0.6 renders below the lit-coverage floor for most of its span
- **THEN** `qa.json` contains a `visual:dark` finding for that section with a suggested brief change

#### Scenario: Advisory only
- **WHEN** `qa.json` contains errors
- **THEN** `xlo apply` and `xlo finalize` still run normally

### Requirement: Stills writes a preview image per section
`xlo stills` SHALL render, from the compiled `.fseq` and the layout geometry and without contacting xLights, one PNG per brief section (at the section's energy peak, or its midpoint when no series is available) into `stills/`, named by section index and label, and SHALL skip with a message when no `.fseq` is available.

#### Scenario: Stills per section
- **WHEN** a rendered `.fseq` exists for the sequence
- **THEN** `stills/` contains one PNG per section, and the command's summary lists them with their timestamps

#### Scenario: No render available
- **WHEN** no `.fseq` exists
- **THEN** the command prints how to produce one (`xlo apply --render`) and exits zero without writing

### Requirement: Finalize saves and patches offline
`xlo finalize --name <sequence>` SHALL save the open sequence, close it, and patch the `.xsq` offline with the song audio, the canonical render order, and the reference timing tracks (built from the analysis and the brief's sections), as today's finalize does.

#### Scenario: Timing tracks from the brief
- **WHEN** finalize runs with timing tracks enabled
- **THEN** the section track's labels come from the brief's sections

### Requirement: Video-plan times and media-plans a written story
`xlo video-plan` SHALL read `video_story.json`, validate it (one beat per brief section, no time fields), resolve beats to the brief's section cuts, split long shots on downbeats, assign lyrics, compute the media plan and per-shot prompts, and write `video_script.json` and `video_script.md`, replacing prior ones. A story that fails validation SHALL produce no script file.

#### Scenario: Story planned
- **WHEN** a valid story exists for a song with a validated brief
- **THEN** both script forms are written and the summary reports the filmed/procedural split

#### Scenario: Invalid story
- **WHEN** the story omits a beat for a section
- **THEN** the command exits non-zero naming the section and writes no script

### Requirement: Init-layout writes a review file and honors overrides
`xlo init-layout --dry-run` SHALL write `layout_review.json` listing each unresolved prop with the features the classifier observed and the candidate roles; a subsequent run SHALL read the show folder's `layout_overrides.json` and treat its assignments as resolved. The LLM fallback SHALL be removed.

#### Scenario: Review file
- **WHEN** the deterministic pass leaves props unresolved
- **THEN** `layout_review.json` lists them with observed features and candidate roles

#### Scenario: Overrides applied
- **WHEN** `layout_overrides.json` assigns roles to every unresolved prop
- **THEN** the next run reports zero to review and proceeds to the membership diff

### Requirement: The cache layout is flat and provider-independent
Stage artifacts SHALL live directly in the song's cache dir with no model-routing namespace. Analysis and targetable-group caches from before this change SHALL be reused; briefs and instructions under a former routing namespace SHALL be ignored.

#### Scenario: Old cache reused
- **WHEN** a song analyzed before this change is analyzed again
- **THEN** the cached analysis is reused and only the digest is new
