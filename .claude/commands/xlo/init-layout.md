---
description: Onboard an xLights layout — classify props into SEM_ groups, resolve the unresolved tail, then write the groups
argument-hint: "[show folder]"
---

Set up the semantic `SEM_` groups the brief targets, from the layout in an xLights show folder. The
deterministic classifier does most of it; you classify what it could not into
`layout_overrides.json`. Nothing is written to `xlights_rgbeffects.xml` until the user says so.

**Show folder.** `$ARGUMENTS` is the show folder (the directory that holds
`xlights_rgbeffects.xml`). If it is empty, use the `show_folder` recorded in a song dir's
`layout.json` if you know one; otherwise ask and stop.

Load the `xlo-layout` skill with the Skill tool and follow its "Classifying the unresolved tail"
section.

**Steps**

1. Dry-run (it leaves `xlights_rgbeffects.xml` untouched and writes only
   `<show folder>/layout_review.json`):
   ```bash
   uv run xlo init-layout --show-folder "$ARGUMENTS" --dry-run
   ```
   Add `--invert-x` when the user says their preview is mirrored, or when the sweep check
   recommends it. Read the output: the classification counts, the membership diff, and the
   `WARNING: N props still need review` line. Props needing review are the job, not a failure: the
   dry run exits 0 either way. Exit 1 means no show folder or no `xlights_rgbeffects.xml` there.

2. Resolve the tail. Read `<show folder>/layout_review.json`: its `props` list has, per prop still
   needing review, its `name`, `display_as`, `nodes`, `pos` [x, y], the user's `groups` it belongs
   to, the classifier's current `role` and `confidence`, and the `candidate_roles` (the closed
   enum). (A rare entry with only a `name` has no parsed model behind it.) Classify each
   into ONE role from the skill's closed enum
   (`MEGA_TREE`, `MINI_TREE`, `ARCH`, `CANE`, `ICICLES`, `STAR`, `SPINNER`, `MATRIX`, `WINDOW`,
   `OUTLINE`, `FLOOD`, `SINGING_FACE`, `SIGN`, `PATH`, `SNOWFLAKE`, `CUSTOM_PROP`): the name and the
   user's group names first, node count and DisplayAs for geometry. Keep `CUSTOM_PROP` when unsure.
   Ask the user about the props you can't justify, all in one question; they know their yard.

3. Write the decisions to `<show folder>/layout_overrides.json`, merging into any existing entries
   (never drop an earlier override), as `{"<exact model name>": {"role": "<ROLE>"}}`. Show the user
   a table of prop → role → why.

4. Re-run the dry run. Confirm it reports nothing left to review; if not, go back to step 2 for
   what remains. Present the membership diff in viewer terms: each `SEM_` group that would be
   created or changed and what it holds, what is excluded and why, and what the manifest says about
   the display (the hero, symmetry, the bands). Name any family the layout lacks.

5. STOP before writing. The write needs xLights CLOSED: xLights rewrites `xlights_rgbeffects.xml`
   from memory on exit and would clobber the edit, and the command refuses while xLights answers
   its port. Ask the user to close xLights and say to apply. Only when they have said to apply (now,
   or when they invoked the command) run:
   ```bash
   uv run xlo init-layout --show-folder "$ARGUMENTS"
   ```
   It exits 1 without writing while xLights still answers its port (ask again), and exits 1 after
   writing when props were still unreviewed (they stay in the manifest's `review` list); 0 is a
   clean write. A backup is taken and only `SEM_` groups are regenerated; the user's own groups are
   untouched.
   Tell them to restart xLights; the next `/xlo:analyze` (its `xlo groups` probe) picks up the new
   groups.
