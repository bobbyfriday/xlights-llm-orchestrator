## Context

Stage 1 of "set the stage." The Director hallucinates because interpretation hands it nothing real: flat raw-RMS intensity (0.05–0.19), a single `"other"` instrument label for all 14 sections, no description. Yet `SongAnalysis` already carries the raw material — beats/bars, key/mode, chords, onsets, harmonic-change points, `stems` + `section_instrumentation` (per-section shares + dominant), mood, timed lyrics, track id. This change **surfaces, normalizes, and describes** it into a deep, reviewable song description, gated by a hard checkpoint. No new DSP.

## Goals / Non-Goals

**Goals:** normalized per-section dynamics; per-section stem shares (not just dominant); featured lyric moments with timestamps; a rich layered human-readable `description.md`; a hard review checkpoint. Hermetic tests.

**Non-Goals:** Stage 2 creative direction; new extractors; effect/generation changes; auto-apply.

## Decisions

### Extend the interpretation output into a `SongDescription`
Enrich the brief rather than replace it (downstream still reads `MusicBrief.sections`). New/changed fields:
- **Per `LabeledSection`:** `intensity` becomes the **normalized** value; add `stem_shares: dict[str,float]` (vocals/drums/bass/other → fraction, ~sums to 1), `instrumentation_phrase: str` ("driven by kick+bass, orchestral pads under"), `musical_description: str` (2–4 sentences), `accents_ms: list[int]` (hits in this section).
- **Global:** `identity` (title/artist/genre/bpm/time-sig/key/mode/character), `dynamic_arc` (climax_ms, builds[], drops[], range note), `harmony_summary` + `transition_cues_ms`, `narrative_or_journey: str`, `featured_lyric_moments: list[{line, start_ms, end_ms, why}]`.
A `description.md` is rendered from these (the human-facing artifact).

### Normalize intensity in CODE, overwriting the model's value
**Pre-mortem fix:** the flat 0.05-0.19 *is* the model's/raw value, so trusting the prompt to normalize is what failed. `normalize_intensities(sections, energy_arc)` runs as a **deterministic code pass post-synthesis** (beside `merge_dominant_instruments`) and **overwrites** `sec.intensity`. It takes each section's mean `energy_arc` RMS in its window and maps to 0..1 via a **robust min/max** (5th-95th percentile of section energies, clipped) so one transient doesn't flatten the rest. The number is explicitly **relative** ("0=this song's quietest, 1=its peak"), stated in the description; the prompts may *describe* dynamics but the value is code-owned.

### Surface stem shares via the existing overlap match
`merge_dominant_instruments` already aligns each brief section to the best `section_instrumentation` by **time-overlap**; extend that same loop to set `sec.stem_shares = dict(best.shares)` + synthesize `instrumentation_phrase`. `dominant` stays as a convenience. If `stems` is None, omit shares + note "instrumentation detail unavailable." (mad russian read all-"other" because only `dominant` was kept; the shares show drums/bass rising in louder sections.)

### Bust the interpret cache
**Pre-mortem fix:** interpret caches at `_cache_path(key,"music_brief")`; an old flat brief would shadow the richer one forever. **Rename the stage key** (`music_brief` -> `song_description`) so existing caches don't load and every song re-interprets through the new pipeline (one-time recompute; analysis stays cached).

### Featured lyric moments from timed lyrics (defensive)
The Lyric Analyst already yields `featured_lines`; pair each with its time window from `SongAnalysis.lyrics` — which is an **untyped `dict | None`**, so parse it defensively (lines/words + timing in whatever shape it takes) and **fuzzy-match** the featured text to the nearest timed line (the analyst text may not equal the timed text verbatim). Result `{line, start_ms, end_ms, why}`; drop a moment on no-match; empty list when `lyrics is None` (instrumental). Never raises on a malformed/empty dict.

### Richer agents, rendered description
The existing analyst panel + synthesizer produce the structured `SongDescription` — with **substantially deeper prompts** demanding per-section musical description, the dynamic arc, instrumentation-over-time reading, harmony/tension, and the narrative/journey (for instrumentals, the emotional journey, no fabricated lyrics). `description.md` is a **pure render** of the structured data (+ the synthesizer's prose fields), written to the song cache dir (`data/.../<key>/description.md`) — same pattern as `revision_log.md`. Keeping the doc a pure render keeps it consistent with the data and unit-testable.

### Hard review checkpoint at interpret
After interpretation, an **interpret checkpoint** presents `description.md` for review/edit/approve and **gates** the pipeline (attended). `--auto` writes it and continues. Reuse the existing checkpoint plumbing (the refine loop's human checkpoint pattern) — injectable so tests can stub it; on "edit," the human's corrected description is taken as the source of truth downstream. (Edit UX can be as simple as "approve / abort to hand-edit the file then re-run" initially; the gate is the requirement.)

## Risks / Trade-offs

- **Normalization choice** — robust percentile vs plain min/max; percentile avoids a single loud transient flattening everything. Tunable; stated as relative either way.
- **Agent verbosity/cost** — deeper prompts cost more tokens on the planner tier; bounded (one interpretation per song, cached). Worth it — this is the foundation.
- **Checkpoint friction** — a hard stop every run; that's the intent now (revisit once quality is consistent, per the plan). `--auto` bypasses for unattended/dev runs.
- **Lyric alignment gaps** — if timing is sparse, a featured line maps to its best-effort window; acceptable (it informs, not gates).
- **Stems absent** — degrades to no shares + a note; the rest of the description still stands.

## Open Questions

- Edit mechanism depth — approve/abort-and-hand-edit vs an inline redirect; start simple (approve/abort), richen later.
- Exact normalization percentiles — tune live against a few songs (mad russian + a vocal track).
