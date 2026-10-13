---
description: Make a show end to end — analyze, design (pause for the brief), realize, apply (pause to review)
argument-hint: "<mp3 path>"
---

Run the whole flow for `$ARGUMENTS`, pausing twice: after the brief is presented, and after the
show is applied. Each stage has its own command file in `.claude/commands/xlo/`; follow each one as
written (same steps, same files, same voice) rather than taking shortcuts.

If `$ARGUMENTS` is empty, ask for the mp3 path and stop.

**Steps**

1. **Analyze**: follow `analyze.md` with `$ARGUMENTS`. If `xlo groups` can't reach xLights, stop
   here, because design needs the targetable groups: ask the user to start xLights and run
   `/xlo:show` again. Otherwise present the structure and ask for corrections. Continue once the
   user confirms or says to go ahead (or if they already stated their reading when invoking
   `/xlo:show`).

2. **Design**: follow `design.md`. Load the skills, settle the interpretation, write
   `creative_brief.json`, validate until clean, and present the brief in viewer language.
   **STOP for brief approval.** Apply the user's edits, re-validate, re-present what changed.
   Continue only when they approve.

3. **Realize**: follow `realize.md` (`xlo realize`, `xlo qa`, findings by section as proposals).
   Don't stop here unless the brief refused to realize or a finding is an error the user should
   decide on; otherwise give the proposals in a short block, note they can take them up in
   `/xlo:review`, and move on.

4. **Apply**: follow `apply.md`. Ask about `--render` once (default no), apply, and report placed
   and skipped with the target-missing advice. Tell the user to watch it in xLights.
   **STOP after apply.** Point at `/xlo:review` for feedback (stills and coverage QA need a
   rendered apply) and `/xlo:finalize` when it is right. Never finalize on your own.
