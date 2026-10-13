---
description: Save the open sequence and patch the .xsq with the audio, render order and timing tracks
argument-hint: "[mp3 path]"
---

Finish the show: save the sequence `/xlo:apply` left open in xLights, close it, and patch the saved
`.xsq` offline so it opens as a Media sequence with the song attached and the reference timing
tracks in place.

**Song.** `$ARGUMENTS` as the mp3 path when given; otherwise the song from this conversation. If
neither is known, ask and stop. `--cache "<song dir>"` works in place of `--song`.

**Steps**

1. Settle the sequence name. The default is derived from the song filename, the same default
   `xlo apply` used. If the user named the sequence at apply time, use that name; if they want a
   different final name, ask once.
   ```bash
   uv run xlo finalize --song "$ARGUMENTS" --name "<sequence name>"
   ```
   xLights must be running with the sequence from `/xlo:apply` still open. Exit 2 names a missing
   file (the brief or the analysis): the show was never built in this song dir, so point at
   `/xlo:design` and `/xlo:apply`. A connection error means xLights is not reachable: say so and
   stop. Add `--no-timing-tracks` only if the user asks for no reference tracks.

2. Report from the summary line, in plain words:
   - the sequence name, saved;
   - the audio: `attached`, or `not staged` (the show folder couldn't be found; the sequence is
     saved without the song, and the user can attach it in xLights);
   - the timing tracks patched in: Sections (from the brief's labels), Beats, Bars, Onsets, and
     Lyrics/Faces when the song has timed lyrics;
   - where the file is: `<show folder>/<sequence name>.xsq`.

3. Remind the user to open it in xLights (File → Open Sequence) to play it with audio; the patched
   file is on disk, not the copy xLights had open. A later `/xlo:review` round re-applies the show
   and needs another finalize.
