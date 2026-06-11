## Why

The shakedown's biggest defect: **15 of 42 effects skipped and 4 whole sections rendered black** — because the planner targeted groups xLights won't accept effects on. `run_pipeline` feeds the Director/Generator **all ~88 layout groups** from `get_group_names()`, but many aren't `addEffect`-targetable: xLights returns *503 "target element doesn't exist"* (`XLightsTargetMissing`) for groups like `All Props`, `Small Flakes`, `Windows and Doors`, while `02_GEO_Center`, `Matrixes`, `Arches`, and the numbered taxonomy all place fine.

Investigated and ruled out: it's **not** the active View (Master View is the same), **not** bad names (all are in `get_group_names`), **not** preset coverage (every effect type had 4–12 looks). The structural cause is murky — `All Props` is a group-of-groups (`Spinners, Flakes GRP` are themselves groups), others have stale/empty members — and not reliably derivable from the layout file. The only robust signal is **empirical: does `addEffect` accept it?** This change probes that once and plans only with the targetable set. The prop grouping itself is fine (the numbered taxonomy is intentional and good) — we just stop targeting the junk.

## What Changes

- A **`targetable_groups(client)`** probe: on a disposable sequence, attempt a tiny `addEffect` on each group from `get_group_names()`; keep the ones that succeed, drop those that raise `XLightsTargetMissing`; discard the sequence.
- **Cache the result per layout** (keyed by a hash of the group list) so the probe runs once and is reused across all runs/songs; re-probe only when the layout changes.
- `run_pipeline` sets `available_groups` to the **targetable** set, so the Director plans with — and the Generator targets — only placeable groups.
- **Graceful:** if the probe fails or xLights is unavailable, fall back to the full `get_group_names()` list (today's behavior) — never worse.

**Non-goals:** re-grouping/renaming props (the taxonomy is good); palette realization or beat-aware generation (separate work); surfacing the GEO/TYPE/BEAT roles to the Director (optional later); fixing *why* a group is non-targetable in xLights (we just avoid it).

## Capabilities

### Modified Capabilities
- `show-orchestration`: the planner targets only prop groups the application accepts effects on — determined empirically (an `addEffect` probe) and cached per layout — so generated sections stop going black; falls back to the full group list if targetability can't be determined.

## Impact

- **`xlights-orchestrator`**: a `targetable_groups` probe (new helper) + a layout-keyed cache; `pipeline/run.py:254` uses it for `st.available_groups` instead of raw `get_group_names()`. Director/Generator code unchanged (they receive a clean list).
- **Builds on** the sequence-element finding (memory `sequence-elements-vs-groups`) and the clean-slate/disposable-sequence mechanics. Directly addresses the shakedown regression.
