---
description: Realize the brief into effect instructions and run deterministic QA; report findings as proposals
argument-hint: "[mp3 path]"
---

Turn the validated brief into `instructions.json` and run the deterministic QA over it. Everything
here is code; your job is to read the results and turn them into proposals.

**Song.** `$ARGUMENTS` as the mp3 path when given; otherwise the song from this conversation. If
neither is known, ask and stop. `--cache "<song dir>"` works in place of `--song`.

Load the `xlo-brief` skill (its review-feedback and qa.json notes) if it is not already loaded.

**Steps**

1. Realize:
   ```bash
   uv run xlo realize --song "$ARGUMENTS"
   ```
   - Exit 2 names a missing prerequisite (`missing <file>: run xlo <stage> first`, or the brief
     with a pointer to `/xlo:design`). Run that stage or command and come back.
   - Exit 1 with `refusing to realize` means the brief has validation errors. Read
     `<song dir>/validation.json`, give the user a one-line summary of the errors in plain words,
     fix the brief (each error's `path` → a value from `allowed`), re-run
     `uv run xlo validate-brief --song "$ARGUMENTS"` until it is clean, and realize again.
   - Exit 0 prints the effect count, the per-section range, the faces placed, and how many effects
     the 4-layer budget trimmed. Relay those in one line.

2. QA:
   ```bash
   uv run xlo qa --song "$ARGUMENTS"
   ```
   Then read `<song dir>/qa.json`. If the summary says `rendered series: no`, there is no render
   yet (that needs `xlo apply --render`), so the coverage checks (`visual:dark`, `visual:static`)
   are neutral and only the instruction-level checks (sync, placement, variety, musicality)
   report. Say that in one sentence so the user doesn't over-read a clean result.

3. Report the findings grouped by section (each finding's `section_index`; `global` findings
   last), in viewer language, as proposals:
   - Per section with findings: its label and time range, then one line per finding saying what it
     means for the viewer and the brief edit you would make (the finding's `fix` when it has one,
     otherwise your reading of `detail` against the `xlo-sequencing` craft). Severity in a word
     (error, warn, info). Never paste the JSON.
   - Give the objective and advisory scores once, and say that nothing in `qa.json` gates any
     stage; the user decides.
   - No findings: say so and skip the list.

4. STOP. Ask which proposals, if any, to apply. For the accepted ones, edit only the sections
   named, validate, re-run realize and qa, and summarize what changed. When the user is satisfied,
   point them at `/xlo:apply`.
