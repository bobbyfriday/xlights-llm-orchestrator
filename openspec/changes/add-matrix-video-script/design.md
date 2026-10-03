## Context

The video matrix is a ~1024×768 centerpiece whose job is narrative: a film that tells the song's
story while the rest of the display plays the lights. The cache already holds the story material
(timed lyrics; narrative, themes, sentiment, mood, featured lines; section structure and energy) and
the show's colour world (named palette, concept). It does not hold a story. That has to be written.

## Goals / Non-Goals

**Goals:** a storyboard per song that tells a coherent visual story fitted to the song's real
structure and timing; harmonized with, not copied from, the light show; usable directly by a video
agent; cheap to try on every cached song.

**Non-Goals:** generating, ingesting or placing video; enforcing the matrix's dedication; changing the
show pipeline.

## Decisions

### D1 — Story material in, lighting description out
The Videographer's input is: song identity (from cached lyrics' title/artist, else the filename —
`MusicBrief.identity` is empty on current caches), full lyrics with line timings, `narrative_or_journey`,
`candidate_themes`, `sentiment`, `key_mood`, `featured_lines`, labeled sections with energy, the climax,
and the show's named palette and `concept`.

It is **not** given per-section `look`, `motion`, `effect_types` or target groups. Those describe props;
handing them over invites a film of the house. Palette and energy are enough to make the film and the
lights feel like one show.

*Alternative rejected:* exporting `look` verbatim (the previous draft). Its output could only replicate
the display.

### D2 — A storyboard, not independent shots
Output is `{logline, motifs[], beats[]}`. Motifs are recurring visual elements (a window, a candle, a
child, a tree) the agent commits to up front so the film has continuity; each beat names which motifs
it carries and how it follows from the previous beat. Without this a model produces a slideshow of
pretty, unrelated images.

### D3 — One beat per section; code owns every timestamp
Beats are keyed by `section_index`. Code fills `start_ms`/`end_ms` from the cached section boundaries
(already downbeat-aligned), frame counts from the derived fps, and attaches any lyric line whose timing
falls in the section. A missing beat inherits the previous one; an extra or out-of-range index is
dropped. Section cuts are where the lights change too, so the film and the show move together.

`--max-shot-s` optionally splits long beats on cached downbeats for tools with clip-length limits
(sections run up to ~57 s); the parts share the beat and carry a part index. Off by default.

### D4 — The contract
Supplied `--matrix-size` (required — refuse rather than guess), fps from the sequence frame interval,
durations and frame counts, full-frame opaque footage, no rendered words (text has its own matrix).
At ~1024×768 real subjects, faces and detail are fine, so the earlier low-resolution restrictions are
gone.

### D5 — Opt-in and priced
Subcommand only, never inside `xlo run`. `videographer` routes to an already-priced planner model
(`estimate_cost` turns a whole run's cost to unknown if any role is unpriced); a test asserts it. Usage
is recorded under its own role.

## Risks / Trade-offs

- **[Generic Christmas imagery]** → The prompt requires the story be built from *this* song's narrative,
  themes and lyrics, and each beat to cite what it draws on. Judged by reading real output.
- **[Weak story material on some songs]** → Instrumental or poorly-analyzed songs (Ghostbusters'
  cached `narrative`/`key_mood` describe the audio texture, not the song) yield thinner input. Lyrics
  and featured lines still carry it; the agent is told which fields are present.
- **[Film and lights pull apart]** → Shared palette, shared energy arc, shared cut points.

## Open Questions

- Which video tool, and its clip limit — decides a sensible `--max-shot-s` default.
- Whether the agent should ever split a section into multiple story beats itself. Not now; revisit
  if one-beat-per-section reads too static on long sections.
