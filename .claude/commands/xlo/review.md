---
description: Review the applied show — stills and QA when rendered, the user's feedback, brief edits, re-realize and re-apply
argument-hint: "[mp3 path]"
---

One manual review cycle: look at what there is to look at, ask the user what they saw, turn their
feedback into brief edits, then re-realize and re-apply the whole show. The user drives. Never run
an automatic critique loop, and never change what they did not ask about.

**Song.** `$ARGUMENTS` as the mp3 path when given; otherwise the song from this conversation. If
neither is known, ask and stop. `--cache "<song dir>"` works in place of `--song`. Use the same
`--name` that `/xlo:apply` used, if one was given.

Load the `xlo-brief` skill (applying review feedback, splitting a section). Load `xlo-sequencing`
and `xlo-scenes` when an edit touches effects, palette, scenes or rhythm.

**Steps**

1. If the show was rendered (`<song dir>/applied.json` has `"rendered": true`), gather the
   evidence:
   ```bash
   uv run xlo stills --song "$ARGUMENTS"
   uv run xlo qa --song "$ARGUMENTS"
   ```
   When there is no render, `xlo stills` prints `no rendered .fseq … run: xlo apply --render` and
   exits 0. Then skip the stills, say so in one line, and offer a rendered apply if the user wants
   pictures. When stills exist, Read each PNG in `<song dir>/stills/` (one per section,
   `NN-<label>.png`) and describe in a line what the display is doing (which props are lit, the
   colors, whether it matches the section's `look`). Then read `qa.json` and mention only the
   findings that matter (`visual:dark`, `visual:static`, errors), as proposals.

2. Ask the user what they saw: which sections worked and which didn't, anything too busy, too dark,
   the wrong color, off the beat. Wait for the answer. If they gave feedback with the command, use
   it and skip the question.

3. Translate each piece of feedback into a brief edit, following `xlo-brief` → Applying review
   feedback:
   - **By section** ("section 4 is too busy", "the bridge should be bluer"): edit only that
     section's fields (intensity, treatment, effect family and types, phrasing, palette, fabric,
     pulse_groups, scene). Every other section stays byte-identical.
   - **By time range** ("redo 1:05 to 1:30, calmer"): find the section(s) the range falls in. Inside
     one section, split it at those times into pieces that tile the parent exactly, copy the
     parent's fields into every piece (same label), and change only the middle piece. Across
     sections, edit each one the range covers and split only the first and last where the range
     cuts inside them. Tell the user the exact times you used, especially after moving a boundary
     to the downbeat the validator names.
   - **Whole-show feedback** ("more contrast", "less white"): apply it consistently and say which
     sections you touched.
   State each edit in one plain line before making it ("verse 2: calmer, intensity 0.55 → 0.35,
   a single hero spotlight, softer edges"). If a request goes against the craft (Strobe in a verse,
   a dark peak), say so once, then do what they ask.

4. Validate until clean, then realize and re-apply the whole show:
   ```bash
   uv run xlo validate-brief --song "$ARGUMENTS"
   uv run xlo realize --song "$ARGUMENTS"
   uv run xlo apply --song "$ARGUMENTS"          # add --render if they want stills/coverage next round
   ```
   Fix validation errors from `validation.json` (`path` → a value from `allowed`) and re-validate
   before realizing. If apply exits 1 or loses the connection, relay it and stop (restart xLights,
   run apply again).

5. Summarize what changed, section by section, in viewer language, and tell the user it is open in
   xLights to watch again. STOP. Another round is another `/xlo:review`; `/xlo:finalize` when they
   are happy.
