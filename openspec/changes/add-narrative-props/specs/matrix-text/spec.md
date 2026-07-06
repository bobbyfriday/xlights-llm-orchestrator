## ADDED Requirements

### Requirement: Narrative Text is placed on the matrix model from lyric and identity events
The pipeline SHALL place stock xLights Text effects on the matrix model, derived deterministically from existing brief fields (the song identity and the curated featured lyric moments), with no new Director round-trip.
A deterministic pass runs inside `generate_instructions` after the per-section loop; content and times come from the brief (`identity.title`/`.artist`, `featured_lyric_moments`), so only strings already present in the brief can ever appear. If a `KeyMoment` of kind `"lyric"` later gains a `text` field, the pass SHALL prefer it over its own selection.

#### Scenario: Title card and featured phrases on a vocal song
- **WHEN** a vocal reference song with aligned lyrics is generated and the layout has a matrix
- **THEN** the show contains a title card in the intro section and at most four featured lyric phrases as Text effects on the matrix model

#### Scenario: Content is grounded in the brief
- **WHEN** the selection pass considers candidate text
- **THEN** only strings present verbatim in `featured_lyric_moments` or `identity` appear, and section labels ("CHORUS"), invented captions, and full lyric captioning never appear

### Requirement: Text targets the matrix model, never a group
The pass SHALL target the matrix model resolved by name (a model whose name contains "matrix", case-insensitive) and SHALL never place Text on a group canvas such as `SEM_FOCAL`.
Model names are fetched best-effort beside the existing group probe; `find_matrix` returns `None` when no matrix exists, causing the whole pass to no-op.

#### Scenario: No matrix in the layout
- **WHEN** the layout contains no model whose name matches "matrix"
- **THEN** the pass no-ops with a logged degradation reason and places no Text effects

#### Scenario: Every Text instruction targets the model
- **WHEN** Text effects are emitted
- **THEN** each targets the matrix model directly (never a group), and none is placed on `SEM_FOCAL`

### Requirement: Text appears as sparse punctuation, bounded and peak-excluded
The pass SHALL treat text as punctuation, not captioning: at most `MAX_TEXT_MOMENTS` (4) featured lyric phrases per show, at least `TEXT_SPACING_MS` (20 000 ms) apart, at most one per section, and none inside the peak section.
Each featured moment's span is cross-checked against the aligned lyric lines and snapped to the matched line's start/end; a moment that matches no aligned line is dropped rather than shown at a guessed time. The title card ends at least one bar before the first downbeat-anchored section boundary and is skipped if the intro is shorter than 8 s or the title is empty. An optional config-gated outro sign-off appears only when a lyric-kind key moment lands in the final section.

#### Scenario: Caps and spacing enforced
- **WHEN** the brief offers six candidate featured lyric moments
- **THEN** at most four are placed, each at least 20 s apart, at most one per section, and none in the peak section

#### Scenario: Unaligned moment is dropped
- **WHEN** a featured lyric moment fuzzy-matches no aligned lyric line
- **THEN** it is dropped and no Text is placed at its brief-supplied time

#### Scenario: Instrumental song shows only a title card
- **WHEN** the song has no featured lyric moments and no aligned lines
- **THEN** at most the title card appears, and if the title is empty or the intro under 8 s, no text appears

### Requirement: Text is legible over the matrix's focal choreography
The pass SHALL emit Text with `on_top=True`, a `Max` layer-blend method, and the section palette's lightest color, and SHALL dim only concurrent matrix-targeted non-text instructions during each text span.
Scrolling phrases traverse exactly once within their aligned span (speed sized so one full traverse ≈ the phrase duration); static text is used when it fits the probed matrix width. Glyph height is at least 10–12 px and at most the matrix height minus two; if the matrix resolution is under ~50 px the pass refuses and logs a degradation. Non-matrix props are never dimmed.

#### Scenario: Text rides on top of a busy background
- **WHEN** a Text moment coexists with hero onsets or washes on the matrix
- **THEN** the Text is placed on top with a Max blend over the section's lightest palette color, and concurrent matrix-targeted non-text instructions are dimmed to about 40% while non-matrix props are untouched

#### Scenario: Scroll-once timing
- **WHEN** a phrase is too wide to fit the matrix at the chosen size
- **THEN** it scrolls left and completes exactly one traverse within its aligned span; a phrase that fits is placed static

### Requirement: Text placement round-trips the settings parser and survives regen
Each Text instruction SHALL carry `direct_settings` that round-trip `parse_settings`/`serialize_settings` with `E_TEXTCTRL_Text` equal to the sanitized source string, and SHALL be tagged with its owning `section_index` and an idempotence marker so refine-loop and `xlo regen` splices reproduce exactly one copy.
The pass re-runs after section splices and replaces its own prior output rather than stacking, using a marker key (`X_MatrixText=1`) in `extra_settings`. Comma/equals or non-ASCII text is sanitized by the F-B builder; phrases that fail sanitization are dropped, not mangled.

#### Scenario: Regenerating a section reproduces one text moment
- **WHEN** a section that owns a text moment is regenerated via a refine splice or `xlo regen`
- **THEN** exactly one copy of that text moment is present afterward (no duplication, no orphan)

#### Scenario: Settings round-trip
- **WHEN** a Text instruction is emitted
- **THEN** its `direct_settings` round-trip the parser and `E_TEXTCTRL_Text` equals the sanitized source string

### Requirement: Excess text moments surface as an advisory
The QA layer SHALL surface an advisory finding when placed text moments exceed the configured cap, visible to reviewers but never gating the objective score.
Text is outside `rules.FEATURES` and `ENERGY_BAND`, so this advisory is the belt-and-braces guard against over-captioning by future authors.

#### Scenario: Cap exceeded
- **WHEN** more text moments are placed than `MAX_TEXT_MOMENTS` permits
- **THEN** an advisory QA finding is emitted without changing the objective score
