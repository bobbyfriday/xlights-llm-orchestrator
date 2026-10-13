## MODIFIED Requirements

### Requirement: Evaluate a draft with deterministic checks
The system SHALL evaluate a realized show (`instructions.json`, and the rendered `.fseq` series when present) using deterministic checks — timing synchronization to the beat grid/sections, placement survival, placement rules, variety, musicality, and rendered coverage — producing structured findings in `qa.json`, without calling xLights or a model. The findings SHALL be labeled objective (timing/placement) or advisory (variety/coverage/musicality/visual), and SHALL carry a `section_index` and a plain-language fix where scoped. The evaluation SHALL NOT gate any stage.

#### Scenario: Evaluate a realized show
- **WHEN** `xlo qa` runs
- **THEN** `qa.json` holds findings and sub-scores derived purely from the instructions, analysis, brief, and render series

#### Scenario: Off-beat transitions are flagged
- **WHEN** an effect's start/end falls outside the tolerance window around the nearest beat/section boundary
- **THEN** that transition is reported as a sync finding

#### Scenario: Objective vs advisory labeling
- **WHEN** the evaluation is produced
- **THEN** timing/placement findings are marked objective and the rest advisory, for the reader's prioritization only

## REMOVED Requirements

### Requirement: The objective score gates only regressions, not creative quality
**Reason**: There is no automatic loop to gate; the human decides what to keep.
**Migration**: Delete `BestTracker` and the revert path.

### Requirement: Judge the draft into scoped revisions
**Reason**: Revisions are decided in conversation.
**Migration**: Delete `agents/judge.py`, `refine.JudgeVerdict`, `refine.RevisionBrief`.

### Requirement: Refine by regenerating flagged scopes and rebuilding
**Reason**: Every change is a brief edit followed by a full realize and re-apply.
**Migration**: Delete `pipeline/regen.py`, `regenerate_section`, `replace_section`.

### Requirement: The loop is bounded and provably terminates
**Reason**: There is no loop.
**Migration**: Delete `pipeline/refine_loop.py`.

### Requirement: Human checkpoints
**Reason**: The whole flow is attended; the conversation is the checkpoint.
**Migration**: Delete the checkpoint gates and `--auto`.

### Requirement: Anti-oscillation
**Reason**: There is no automatic revision to oscillate.
**Migration**: Delete the escalation ledger.

### Requirement: Refinement is optional and always leaves a valid sequence
**Reason**: There is no refinement stage.
**Migration**: None; `apply` always leaves a complete sequence.

### Requirement: The Judge decides revisions from the visual critique
**Reason**: Judge and critic are removed.
**Migration**: None.

### Requirement: A regenerated section receives the visual issue
**Reason**: There is no regeneration; Claude edits the brief with the issue in hand.
**Migration**: None.

### Requirement: Narrow backstop for critic-confirmed defects
**Reason**: Critic removed; dark/static checks are plain QA findings.
**Migration**: See `qa` in stage-commands.

### Requirement: Visual findings remain advisory to the objective gate
**Reason**: There is no gate.
**Migration**: None.

### Requirement: The loop re-evaluates visually after regeneration
**Reason**: There is no loop; the user re-runs `qa`/`stills` after `apply --render`.
**Migration**: None.
