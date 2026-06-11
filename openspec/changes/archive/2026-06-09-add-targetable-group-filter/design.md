## Context

`run_pipeline` feeds the planner all ~88 layout groups (`get_group_names()`), but only a subset are `addEffect`-targetable; the rest produce `XLightsTargetMissing` → skipped effects → black sections. Targetability isn't reliably derivable from `rgbeffects.xml` (nested groups like `All Props`→`Spinners,Flakes GRP`, stale/empty members), and isn't view-dependent (Master View is the same). The robust signal is empirical — probe `addEffect`. See memory `sequence-elements-vs-groups`.

## Goals / Non-Goals

**Goals:** plan only with addEffect-able groups; determine empirically; cache per layout; graceful fallback. Hermetic tests + a live skip-rate check.

**Non-Goals:** re-grouping props; palette/beat work; explaining xLights' targetability rules; surfacing taxonomy roles.

## Decisions

### `targetable_groups(client, *, cache_root)` — probe + cache
1. `names = await client.get_group_names()`.
2. `fp = sha1(",".join(sorted(names)))[:16]` — the **layout fingerprint**. Look up `<cache_root>/targetable_groups_<fp>.json`; if present, return it (no probe).
3. Otherwise **probe** on a disposable sequence: `close_sequence(force,quiet)` → `new_sequence(duration_secs=10, force=True)` (animation, no media) → **`await asyncio.sleep(0.8)` so the sequence elements populate** (this is load-bearing — `apply_instructions` settles 0.6s for the same race; probing too early makes *good* groups fail). Then for each `name`: `try: place_preset(client, name, "On", candidate_look_ids("On")[0], layer=0, start_ms=0, end_ms=500)` → on **`XLightsTargetMissing` ONLY**, skip that group and continue. Collect the successes, then `close_sequence(force,quiet)` (discard — never saved).
4. Write the success list to the cache file; return it.
5. **Best-effort, fail-safe:** the whole probe is wrapped — if `get_group_names`/`new_sequence` fails, a **non-`XLightsTargetMissing`** error hits mid-loop (timeout/transient), or the result is empty → return the full `names` and **do NOT write the cache** (so a blip never poisons the cache; next run re-probes). Never return `[]`. Excluding only on the specific 503 means a transient error can't wrongly drop a real target.

Probe cost: ~88 quick `addEffect` calls on a throwaway sequence (a few seconds), one-time per layout. The effect used is a trivial `On` (always available); only the *target acceptance* matters, not the effect.

### Wiring
`run_pipeline`: `st.available_groups = await targetable_groups(client, cache_root=_cache_root())` replacing `get_group_names()` at run.py:254. Everything downstream (Director `available_groups`, Generator targets, group_motifs) then references only real targets — no other code changes. The probe runs before the design stage so the Director never sees junk groups.

### Where the cache lives
`<cache_root>/targetable_groups_<layout_fp>.json` (cache_root = `data/analyses/orchestrator`). Layout-keyed (not song-keyed) since targetability is a property of the prop layout, shared across all songs. Changing the layout (add/remove groups) changes the fingerprint → automatic re-probe.

## Risks / Trade-offs

- **Probe side effects** — it places effects on a disposable sequence; we never save it and the real run starts clean (`apply_instructions` closes + creates fresh). No lasting effect.
- **Probe latency** — ~seconds, one-time per layout (cached). Acceptable; the first run pays it, the rest are instant.
- **A targetable group that errors transiently during the probe** would be wrongly excluded for that layout until re-probe; mitigated because the probe only excludes on the specific `XLightsTargetMissing` (not generic errors → those bubble to the fallback).
- **Over-exclusion** — if the probe itself is flaky, we lose groups; the empty-result fallback (return all) caps the downside, and the cache means a clean probe sticks.
- **Stale cache after layout edits in xLights** — the fingerprint is the group-name set; reordering/renaming triggers re-probe. (Adding models *inside* an existing group without changing names wouldn't re-probe, but that doesn't change targetability of the group name.)

## Open Questions

- Whether to also tag each targetable group with its taxonomy role (GEO/TYPE/BEAT/…) for the Director — deferred to a later enhancement; this change only filters.
- Probe the trivial effect on layer 0 at t=0–500ms vs an even cheaper "dry-run" if xLights ever exposes one — use `place_preset` for now (proven).
