## REMOVED Requirements

### Requirement: Append a record per refine iteration
**Reason**: There is no refine loop to log.
**Migration**: Delete `revision_log.py`; existing `revisions.jsonl` files are left in place and unread.

### Requirement: Capture the iteration's decisions and outcome
**Reason**: There are no iterations.
**Migration**: None.

### Requirement: Provide a human-readable view
**Reason**: The conversation transcript is the record of what was changed and why.
**Migration**: Delete `xlo report` and `reporting.py`.

### Requirement: Capture the human decision when attended
**Reason**: There are no checkpoints.
**Migration**: None.

### Requirement: Logging is pure observability
**Reason**: Nothing to observe.
**Migration**: None.

### Requirement: Logging is optional and degrades to no-op
**Reason**: Removed with the log.
**Migration**: Remove `--no-log`.
