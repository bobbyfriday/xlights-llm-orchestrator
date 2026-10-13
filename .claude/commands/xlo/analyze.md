---
description: Analyze a song and probe the layout, then summarize its structure and the layout's groups for discussion
argument-hint: "<mp3 path>"
---

Analyze `$ARGUMENTS` and tell the user what the song is made of, so the two of you agree on its
structure before `/xlo:design`. Nothing creative happens here: this is the shared reading of the
music and the layout.

**Song.** If `$ARGUMENTS` is empty, ask which song (an mp3 path, or an existing song dir under
`$XLO_CACHE_DIR/orchestrator/`) and stop until you have it. Every `xlo` command below takes
`--song "<mp3>"`; a song dir is passed as `--cache "<dir>"` instead.

**Steps**

1. Run the analysis (audio, stems, lyrics, the digest). The first run on a song can take a few
   minutes; later runs reuse the cache.
   ```bash
   uv run xlo analyze --song "$ARGUMENTS"
   ```
   The last line is `song dir: <path>`. That is the song's cache dir; every later stage reads and
   writes there. Keep it for the rest of the conversation. Exit 1 means the file was not found or
   the analysis failed: relay the message and stop.

2. Probe the layout. This needs xLights running with its automation listener on.
   ```bash
   uv run xlo groups --song "$ARGUMENTS"
   ```
   It writes `vocab.json`, `creative_brief.schema.json` and `layout.json` into the song dir. If it
   fails because xLights is not reachable (a connection error), say so in one line ("xLights isn't
   running, so I can't see which groups are targetable yet; start it and I'll re-probe before
   design") and continue with whatever `vocab.json` an earlier probe left. If there is none,
   continue with the music alone and say that `/xlo:design` needs the probe first.

3. Read `<song dir>/analysis_digest.md` in full, and `<song dir>/vocab.json` when it exists.

4. Present the song in viewer language. No JSON, no field names.
   - **Structure**: a table of the sections with time ranges in m:ss, each one's normalized energy
     as a word plus the number ("quiet 0.18", "driving 0.74"), its dominant stems, and its first
     lyric line when it has one. Name the peak.
   - **Lyric hooks**: the repeated lines, and any lyric section markers the digest found.
   - **Entrances and mood**: where instruments come in, then key and mood in one line.
   - **The layout's group families**, from `vocab.json` `groups`, grouped by role as the
     `xlo-layout` skill describes (hero, house/frame, rhythm families, sparkle/accent, bands, sides,
     the user's own groups). Name a missing family (no `SEM_FOCAL`, no arches) because it limits
     the design. List the stems available for `follow_stem`.

5. Invite corrections and STOP. Ask the user to confirm or fix the structure: are the boundaries
   right, is something the digest calls a verse really a chorus, where is the real peak, what is the
   song about to them. Their reading wins. Do not write a brief or start `/xlo:design` until they
   answer or say to go ahead.
