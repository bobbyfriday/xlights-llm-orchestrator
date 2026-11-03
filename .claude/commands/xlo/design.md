---
description: Design the show — write creative_brief.json, validate it until clean, present it in viewer language
argument-hint: "[mp3 path]"
---

Write the creative brief for this song, validate it until it is clean, and present it section by
section so the user can change it before anything is realized.

**Song.** Use `$ARGUMENTS` as the mp3 path when given; otherwise the song from earlier in this
conversation (the song dir `/xlo:analyze` printed). If neither is known, ask which song and stop.
`--song "<mp3>"` and `--cache "<song dir>"` are interchangeable on every `xlo` command below.

**Load the skills first**, by name with the Skill tool: `xlo-brief` (the file and the loop),
`xlo-sequencing` (effects, energy, palette; read the effects catalog in full as it says),
`xlo-effects` (open `effects/<Type>.md` for every effect type you choose; design from an anchor and
permute), `xlo-scenes` (scenes, `scene_cast`, the trigger layer), `xlo-layout` (what the groups are). Follow
them; this command only orders the work.

**Steps**

1. Read from the song dir: `analysis_digest.md`, `vocab.json`, `creative_brief.schema.json`.
   - No `analysis_digest.md`: tell the user to run `/xlo:analyze` first and stop.
   - No `vocab.json`: run `uv run xlo groups --song "$ARGUMENTS"` (xLights must be running). If
     that fails, say xLights must be running for design and stop.
   - A `creative_brief.json` already exists: say so and ask whether to revise it or start fresh.

2. Settle the interpretation, briefly, before writing: the concept in a sentence or two, the
   palette (named colors from `vocab.json` `colors`, spanning warm and cool), and where the peak is
   and what happens there. Build on whatever the user already settled in `/xlo:analyze` instead of
   re-asking. Ask a question only when something is genuinely ambiguous (two plausible peaks, a
   mood you cannot read from the digest, a holiday or theme the user has not named). Otherwise
   state your reading in a few lines and move on; the brief is where they will edit.

3. Write `<song dir>/creative_brief.json` in one pass, following `xlo-brief`:
   `"$schema": "creative_brief.schema.json"`; the show fields (`experience`, `concept`, `palette`,
   `key_moments`, with lyric captions as `kind: "lyric"` + `text` when the layout has a matrix);
   one section per digest section, with boundaries from the digest's section table in integer
   milliseconds, tiling the whole song. Per section: `label`, `target_groups` in priority order,
   `effect_family`, `effect_types`, `intensity`, `look`, `palette`, `phrasing`, `treatment`,
   `scene_id` with `scene_cast` (and `scene_adaptation` as the prose note), the rhythmic-intent
   fields, and `fabric` where the beat's motion matters (an explicit `fabric.carrier` also weaves
   under `pulse` and `feature`). Every group, effect, scene, stem, color and blend comes from
   `vocab.json`. Recurring parts share a label; write chorus 1 at about 70%.

4. Validate and fix until clean:
   ```bash
   uv run xlo validate-brief --song "$ARGUMENTS"
   ```
   Exit 1 means errors. Read `<song dir>/validation.json`. For every entry in `errors`, go to its
   `path` (e.g. `sections[3].target_groups[1]`), replace the value with one from its `allowed`
   list (or fix the time), and re-run. Loop until `ok` is true. Never present a brief that has not
   validated. Warnings do not block; they are judgment calls: snap a boundary to the downbeat the
   message names, split a section longer than 32 s, vary a repeated family unless the repetition
   is deliberate. Mention the notable warnings you chose to keep.

5. Present the brief in viewer language. No JSON, no field names. For each section: its time
   range in m:ss and label, what a viewer sees (the `look`), the colors, and the scene and fabric
   choice in a few plain words ("the arches and canes trade a ping-pong chase every two beats").
   Then the show palette, the key moments with their times, and one line on the arc: where it is
   held back and where it pays off. A short paragraph per section, not a table of every field.

6. STOP and wait for the user's edits. Apply each edit to the brief, re-validate (step 4), and
   re-present only the sections that changed. Do not run `xlo realize` or `xlo apply` here. When
   the user is happy, point them at `/xlo:realize`, or continue if they say so.
