## Context

`cap_long_segments` (`xlights-core/audio/structure.py`) subdivides any segment longer than
`INSTR_MAX_SECTION_S` (32s). Within each `[prev+INSTR_MIN_PIECE_S, prev+32]` window it builds
candidate seams — harmonic-change times scored by coincident |Δrms|, plus energy-delta points —
each **snapped to the nearest beat** by `_snap` (line 33), then picks the strongest (ties → earliest),
falling back to even beat spacing when a window has no seam.

The beat grid carries `bar_position` (1 == downbeat) on every `Beat` (`schema.py`; clean 4/4,
derived every 4 beats), and `Beat.is_downbeat` already exists — but `_snap` and the selection ignore
it. So a cut can land on any beat, including a weak pickup. Christmas Canon: the intro cut chose
**31.777s** (`bar_position==4`, the strongest energy seam near the cap); the musical phrase boundary
the ear wants is **28.677s** (`bar_position==1`, with a harmonic change at ~28.9s) — it scored lower
on energy and lost.

The prior "strongest seam, not the latest" requirement stopped cuts pinning to the cap but added no
bar awareness, so a loud off-beat seam still beats an earlier downbeat boundary.

## Goals / Non-Goals

**Goals:**
- Section cuts land on **bar lines (downbeats)** when a downbeat sits near a real seam.
- Prefer an earlier downbeat phrase boundary over a louder **off-beat** seam near the length cap.
- Verify the Christmas Canon intro cut moves from 31.777s to the ~28.7s downbeat.
- Preserve every existing guarantee: cap respected, min-piece floor, tiny-tail fold, idempotence,
  no-op when all sections fit, and graceful fallback when bar positions are missing.

**Non-Goals:**
- Changing the cap (32s), the min-piece floor, or the lyric-marker derivation logic itself (only
  bar-align its snapped boundaries within tolerance, no new markers).
- Any `SongAnalysis` schema change (`bar_position` / `is_downbeat` already exist).
- Re-deriving downbeats (trust the existing 4/4 bar grid).

## Decisions

**1. Add a downbeat-preferring snap, used for section boundaries.**
`_snap_downbeat(t, beats, downbeats, tol_s)` returns the nearest **downbeat** when one lies within
`tol_s`, else the nearest beat (today's behavior). `tol_s` seeds at ~one beat period (≈0.6s) — small
enough that only genuinely-near-the-bar seams move. When `downbeats` is empty (no bar info), it is
exactly `_snap` (graceful fallback).
*Alternative considered:* always snap to nearest downbeat. Rejected — a seam mid-bar could yank a
full beat or two, distorting timing; the tolerance keeps it honest.

**2. Snap candidate seams to downbeats, then window-filter — this drops the near-cap off-beat seam.**
In `cap_long_segments`, build candidates with `_snap_downbeat` instead of `_snap`. A loud seam at
31.777 snaps to its bar line 32.229, which falls **outside** the `[lo, cap]` window and is dropped;
the strongest remaining in-window candidate is the 28.677 downbeat (harmonic change). So bar-aligning
the candidates plus the existing window filter naturally removes the off-beat drift.
*Alternative considered:* keep beat-snapped candidates and add a multiplicative downbeat bonus to the
score. Rejected as the primary mechanism — harder to reason about / tune than snapping, and a loud
off-beat seam could still out-score a quiet downbeat. (Kept available as a fallback knob if live
tuning shows snapping alone is too aggressive.)

**3. Nudge the final chosen cut to the nearest in-window downbeat within tolerance.**
Belt-and-suspenders for the spacing fallback (no-seam windows) and any candidate that stayed
off-bar: after a cut is chosen, snap it to the nearest downbeat ≤ `cap` and `> prev+min` when within
`tol_s`. Guarantees boundaries land on bars wherever a bar line is reachable without violating the
cap or min-piece floor.

**4. Graceful, behavior-preserving when bars are absent.**
If no beat carries `bar_position` (older caches, odd meters the tracker couldn't label), `downbeats`
is empty and every path collapses to today's beat-snapped behavior — so non-4/4 and legacy analyses
are unaffected.

## Risks / Trade-offs

- **Over-snapping shifts a cut off a real musical break** → Mitigation: small `tol_s` (≈1 beat); a
  seam more than a beat from any downbeat keeps its beat position. Live-tune `tol_s` against the
  intro.
- **A loud seam's bar line lands just inside the window and still wins over the wanted earlier
  downbeat** → energy still scores; if needed, prefer the earliest among downbeat candidates within
  a small strength band. Decide against the live render (the user's reference is 28.7s).
- **Min-piece / cap interaction** → the nudge is clamped to `> prev+min_piece` and `≤ cap`, so
  bar-aligning can never produce a sub-min piece or exceed the cap; if no downbeat fits those bounds,
  keep the beat-snapped cut.
- **Changes existing golden/segment expectations** → instrumental segment boundaries shift to bars;
  regenerate the golden intentionally and confirm the diff is only boundary bar-alignment.

## Open Questions

- `tol_s` exact value (seed ≈0.6s / one beat) and whether to add the earliest-within-strength-band
  rule (decision-3 / risk-2) — resolve against the Christmas Canon live render (target intro ≈28.7s).
