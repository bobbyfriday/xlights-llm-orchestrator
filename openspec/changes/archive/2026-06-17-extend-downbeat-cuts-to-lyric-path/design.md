## Context

`refine_segments_with_lyrics` rebuilds sections from timed lyric markers. Its boundaries — marker
starts, the outro tail, and interior in-fill cuts inside long instrumental spans — were each placed
with `_snap` (nearest beat). The `add-downbeat-aligned-section-cuts` change already added the
`_snap_downbeat(t, beats, downbeats, tol)` helper and `_downbeats(analysis)` and proved the approach
on the cap path; this change simply applies the same helper to the lyric path. No new mechanism.

## Goals / Non-Goals

**Goals:**
- Lyric-derived section boundaries land on the bar line when a downbeat is within tolerance.
- Christmas Canon intro moves from 29.118s (beat 2) to 28.677s (downbeat).
- Reuse the existing helper, tolerance, and graceful no-bar fallback verbatim.

**Non-Goals:**
- Any change to which markers/lines drive structure, the merge/min-section logic, or the cap path.
- New tolerance/constant (reuse `DOWNBEAT_SNAP_TOL_S`).

## Decisions

**Swap the three `_snap` calls for `_snap_downbeat`, with one `downbeats` lookup.**
Compute `downbeats = _downbeats(analysis)` once; pass it to the marker-cut, outro-tail, and in-fill
snaps. Monotonicity is preserved by the existing dedup guard (`t - cuts[-1][0] > 1e-6` skips a cut
that snaps onto/under the previous one).
*Alternative considered:* only fix the marker cuts (the intro). Rejected — the outro and in-fill are
section boundaries too and should be bar-aligned for the same reason; doing all three is consistent
and no riskier.

## Risks / Trade-offs

- **Two near markers snap to the same downbeat** → the existing dedup drops the duplicate, exactly as
  it already does for two markers snapping to the same beat. No new behavior.
- **No bar positions (legacy/odd meter)** → `_downbeats` is empty and `_snap_downbeat` is exactly
  `_snap`, so those analyses are unchanged (existing lyric tests use bar-less grids and stay green).
