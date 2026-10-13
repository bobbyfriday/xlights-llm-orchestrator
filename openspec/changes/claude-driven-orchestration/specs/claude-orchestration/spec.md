## ADDED Requirements

### Requirement: Skills carry the show's craft knowledge from a single source
The repository SHALL provide project-local Claude Code skills (`.claude/skills/xlo-*`) that give Claude the sequencing guide, effects catalog, layering/rendering guide, scene and trigger cookbooks, layout semantics, brief-authoring guidance, and video-story guidance. Each skill SHALL reference the hand-editable guide files at the repository root rather than copying their content, so the guides remain the single source.

#### Scenario: A guide edit reaches Claude
- **WHEN** the user edits `xlights-sequencing-guide.md` and later runs `/xlo:design`
- **THEN** the design conversation reflects the edited guidance without any skill file being changed

#### Scenario: Skills are discoverable by task
- **WHEN** a command needs craft knowledge (design, review, video)
- **THEN** it names the skills to load, and each skill states which root file to read for which decision

### Requirement: Commands drive each stage through the deterministic CLI
The repository SHALL provide project-local commands (`.claude/commands/xlo/*.md`) — `analyze`, `design`, `realize`, `apply`, `review`, `finalize`, `video`, `init-layout`, and a chaining `show` — each of which runs the corresponding `xlo` stage command(s) through Bash, reads the files they write, and performs any judgment in the conversation. Commands SHALL NOT invoke a model API themselves.

#### Scenario: Analyze then summarize
- **WHEN** the user runs `/xlo:analyze <mp3>`
- **THEN** Claude runs `xlo analyze` and `xlo groups`, reads the analysis digest and vocabulary, and summarizes the song's structure and the layout's available groups in the conversation

#### Scenario: Chained show
- **WHEN** the user runs `/xlo:show <mp3>`
- **THEN** the stages run analyze → design → realize → apply, pausing for the user after the brief is presented and after the show is applied

### Requirement: The creative brief is authored in conversation
Claude SHALL write `creative_brief.json` directly in the song's cache dir, guided by the brief-authoring skill and the per-run schema, and SHALL run `xlo validate-brief` and correct the brief until it validates before presenting it. The brief SHALL be presented to the user in plain language (what a viewer sees per section, the palette, the key moments), not as JSON.

#### Scenario: Validation loop
- **WHEN** the first draft of the brief names a group that is not targetable
- **THEN** Claude reads the validator's error for that path, replaces the group with an allowed one, re-validates, and only then presents the brief

#### Scenario: Plain-language presentation
- **WHEN** the brief validates
- **THEN** the user sees a section-by-section description in viewer terms with the fabric and scene choices named, and may request changes before realize

### Requirement: Interpretation is a conversation, not a file
Claude SHALL interpret the song (structure, mood, narrative, where the boundaries fall) from the analysis digest in conversation with the user, and SHALL encode the agreed interpretation in the brief's `experience`, `concept`, section labels, and `key_moments`. No separate interpretation artifact SHALL be required by any later stage.

#### Scenario: User corrects structure
- **WHEN** the user says a section Claude called a chorus is the bridge
- **THEN** the brief's section label and treatment reflect the correction and no other file needs updating

#### Scenario: Later stages need only the brief
- **WHEN** `xlo realize`, `xlo finalize` (timing tracks), or `xlo video-plan` runs
- **THEN** it reads section labels from the brief and never requires an interpretation file

### Requirement: Review is manual and brief-driven
After `apply`, the user reviews the show in xLights (and Claude may read the `stills` and `qa.json`). Feedback SHALL be applied by editing the brief, re-validating, re-realizing, and re-applying the whole show. Claude SHALL NOT run an automatic critique-and-revise loop.

#### Scenario: Section feedback
- **WHEN** the user says "section 4 is too busy, calm it down"
- **THEN** Claude edits that section's intensity/treatment/fabric in the brief, validates, realizes, and applies, leaving other sections' brief entries unchanged

#### Scenario: Time-range feedback
- **WHEN** the user says "redo 1:05 to 1:30, bluer" and that range is inside a longer section
- **THEN** Claude splits the section at those times in the brief (the new boundaries carry the requested changes), validates, realizes, and applies

#### Scenario: QA findings are proposals
- **WHEN** `qa.json` reports a dark mid-energy section
- **THEN** Claude proposes a brief edit and waits for the user rather than applying it unasked

### Requirement: No model API key is required
The `xlights-orchestrator` package SHALL make no model API calls and SHALL have no model-client dependency; the only external credential it reads is the optional lyrics token.

#### Scenario: Clean environment
- **WHEN** `xlo analyze`, `xlo realize`, `xlo apply`, `xlo qa`, and `xlo finalize` run with no `ANTHROPIC_API_KEY` or `GEMINI_API_KEY` set
- **THEN** each completes normally

### Requirement: The video story is authored under a skill
Claude SHALL write `video_story.json` (logline, recurring motifs, one beat per section, no time fields) under the video skill, and `/xlo:video` SHALL then run `xlo video-plan` to validate, time, and media-plan it.

#### Scenario: Story to storyboard
- **WHEN** the user runs `/xlo:video` for a song with a validated brief
- **THEN** Claude writes the story file, runs the planner, and presents the timed storyboard and media summary

### Requirement: Unresolved layout props are classified under a skill
`/xlo:init-layout` SHALL run the deterministic classifier in dry-run mode, read the review file of unresolved props, have Claude assign each a semantic role using the layout skill, write those assignments to the show folder's `layout_overrides.json`, and re-run the classifier to apply.

#### Scenario: Tail resolved by Claude
- **WHEN** the deterministic pass leaves props unresolved
- **THEN** Claude's assignments land in `layout_overrides.json` and the second pass reports zero unresolved props before any file is written
