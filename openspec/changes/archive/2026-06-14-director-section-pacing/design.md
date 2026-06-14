## Context

`cap_long_segments` (aggressive-segmentation) caps the analysis at 32s and the MusicBrief carries the fine sections, but the director freely sets ShowPlan section boundaries and tends to merge fine sections into long ones (Canon intro → 63s + 37s). The user wants the director to keep making the call but to be informed that long sections are usually a poor viewer experience.

## Goals / Non-Goals

**Goals:** the director keeps sections short by default and treats long sections as a justified exception. **Non-Goals:** a deterministic cap on the ShowPlan (rejected — the user wants the director to decide); changing the analysis-level cap; per-section content.

## Decisions

**D1 — Steer, don't enforce.** A prompt note, not a post-pass split. The user explicitly wants the director to own grouping; the fix is to give it the missing information (long = boring) and a default (keep the provided sections), while leaving the exception open.

**D2 — Anchor to ~35s and the provided structure.** The note cites the same ~35s threshold the segmentation uses ("a look past ~35s reads as static") and tells the director the song is ALREADY split — so the default is "keep it," merging is the deviation that needs a reason.

## Risks / Trade-offs

- [Steering may not always land] → accepted (the user chose steering over a hard cap); if the director still over-merges in practice, a deterministic ShowPlan split remains available as a follow-up.
- [Director over-splits to obey] → unlikely; the note frames short as the norm and allows justified long sections, and the analysis sections bound the granularity.

## Migration Plan

Prompt-only; additive. Branch `change/director-section-pacing`, PR (user merges). Verify by regenerating a song with a long passage and checking the director keeps sections shorter.

## Open Questions

- If steering proves unreliable across songs, add a deterministic ShowPlan section cap (split director sections > ~40s, inheriting the plan) as a floor — deferred per the user's preference.
