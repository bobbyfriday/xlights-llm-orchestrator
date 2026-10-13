---
description: Write the video story for the centerpiece matrix and plan it into a timed storyboard
argument-hint: "[mp3 path]"
---

Write the short film for the show's video matrix (the song's story, never the lights) as
`video_story.json`, then let `xlo video-plan` time it, media-plan it and write the storyboard.

**Song.** `$ARGUMENTS` as the mp3 path when given; otherwise the song from this conversation. If
neither is known, ask and stop. `--cache "<song dir>"` works in place of `--song`. The brief must
exist and validate (`/xlo:design`): the planner cuts the film on its sections.

Load the `xlo-video` skill with the Skill tool and follow it for the story rules and the file shape.

**Steps**

1. Plan the media first, so each beat is written for its medium:
   ```bash
   uv run xlo video-plan --plan-only --song "$ARGUMENTS"
   ```
   Add `--no-veo` for an all-procedural film, or `--veo-clips N` / `--filmed-sections I,J` when the
   user has asked for them. Read `<song dir>/media_plan.json`: each section's `medium` (filmed or
   procedural). Exit 2 means the brief is missing; run `/xlo:design` first.

2. Read `creative_brief.json` for `sections[].label` and `intensity`, the show `palette` and
   `concept` only (not the lighting fields), and `analysis_digest.md` for the lyric lines, hooks
   and mood. If the user has said what the song is about, that is the story's spine. Ask one
   question only when the subject is genuinely unclear (an instrumental whose identity you can't
   name).

3. Write `<song dir>/video_story.json`: a logline, a short list of recurring motifs (with a proxy
   object for any character), and exactly one beat per brief section by `section_index`. No time
   fields, no on-screen words. Honor the plan: filmed sections may show people and real places;
   procedural sections use only the procedural vocabulary (no people, faces, hands, animals). Give
   every beat a `procedural_stand_in`. Sections with the same label share imagery and action.

4. Plan the story. The matrix resolution is never guessed: if the user hasn't given it, ask ("what
   is the video matrix's resolution, e.g. 1024x768?") and wait.
   ```bash
   uv run xlo video-plan --song "$ARGUMENTS" --matrix-size <WxH>
   ```
   Exit 1 lists the story's problems (a missing beat, a time field, a person in a procedural beat).
   Fix the named beats in `video_story.json` and re-run. Pass `--max-shot-s N` only when the user
   wants a different filmed clip length.

5. Read `<song dir>/video_script.md` and present the storyboard in viewer terms: the logline and
   motifs; per shot its time range in m:ss, its medium, and what we see in a line; then the
   summary (filmed vs procedural sections, clips planned against the budget). Offer to revise any
   beat; a revision is an edit to `video_story.json` and step 4 again.
