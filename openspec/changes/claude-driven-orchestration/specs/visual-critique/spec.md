## REMOVED Requirements

### Requirement: Critique rendered frames into scoped findings
**Reason**: The multimodal critic is removed; stills are read by the user and by Claude in conversation.
**Migration**: Delete `agents/visual_critic.py` and `pipeline/visual.py`'s critique path; the still renderer is reused by `xlo stills`.

### Requirement: The refine loop consults the visual critic before escalating to a human
**Reason**: There is no refine loop.
**Migration**: None.

### Requirement: Visual critique is optional and degrades gracefully
**Reason**: There is no critique stage.
**Migration**: `xlo stills` skips with a message when no `.fseq` exists.

### Requirement: The visual critique is music-aware
**Reason**: The computable part (dark/static during energetic music) becomes deterministic QA findings; the rest is the user's judgment.
**Migration**: See the `qa` requirement in stage-commands.

### Requirement: The critique assesses dynamics, variety, and music-sync
**Reason**: Assessed by the user watching the show, with `qa.json`'s variety and musicality findings as support.
**Migration**: None.
