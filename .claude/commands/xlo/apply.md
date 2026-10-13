---
description: Apply the realized instructions into a clean-slate sequence in the running xLights and report skips
argument-hint: "[mp3 path]"
---

Emit `instructions.json` into xLights as a fresh sequence (always a full re-emit of the whole show)
and report what landed and what did not.

**Song.** `$ARGUMENTS` as the mp3 path when given; otherwise the song from this conversation. If
neither is known, ask and stop. `--cache "<song dir>"` works in place of `--song`.

**Steps**

1. Decide on `--render`. If the user has not said, ask once: "Render it as well? Rendering writes
   the `.fseq` that `/xlo:review` needs for stills and coverage QA; it adds a minute or so." (Apply
   always saves the sequence and reopens it with the song attached, rendered or not.) With no answer, don't render. If the user named the sequence, pass
   `--name "<name>"` here and keep the same name for `qa`, `stills` and `finalize`.
   ```bash
   uv run xlo apply --song "$ARGUMENTS"          # add --render to also render
   ```
   - Exit 2: a missing prerequisite (`instructions.json`); run `/xlo:realize` first.
   - Exit 1 `apply refused: …`: xLights would not give a clean slate (a sequence it can't close).
     Relay the message and stop.
   - A connection error means xLights is not running or its automation listener is off. Say so and
     stop.
   - xLights sometimes crashes during apply. If the command dies on a connection error partway
     through, tell the user to restart xLights and run the same command again: `instructions.json`
     is unchanged and apply always starts from a clean slate.

2. Read `<song dir>/applied.json` (`counts`, `placed`, `skipped` with a `reason` and
   `section_index` each, `rendered`, `saved`, `audio`, `sequence`). Report in viewer language:
   - placed and skipped out of the instruction count, whether it rendered, and whether the audio
     attached, with the sequence name;
   - the skips grouped by reason. For target-missing skips (`XLightsTargetMissing` in the reason),
     load the `xlo-layout` skill if it isn't loaded and follow its advice: name the groups xLights
     rejected, the sections that lose coverage because of them, and the `vocab.json` group of the
     same role you would substitute. A `layer budget` skip means a row stacked deeper than 4
     layers; mention it only when it costs a whole section;
   - any section that placed nothing at all: it will be dark.

3. Tell the user to watch it in xLights: the sequence is open in the sequencer with the song
   attached (`audio: true`). If the audio did not attach, they can reopen the `.xsq` from the show
   folder or play the song alongside. Point at `/xlo:review` for feedback and `/xlo:finalize`
   (timing tracks, render order) when it is right.

4. STOP. Do not fix skips, re-realize or re-apply unless the user asks. A target-missing fix is a
   brief edit: change the group, validate, `/xlo:realize`, then apply again.
