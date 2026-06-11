> **Build result (verified live):** `targetable_groups(client, cache_root)` probes a trivial On per group on a disposable sequence (settle 0.8s, exclude ONLY on XLightsTargetMissing, close+discard), caches per-layout by group-name fingerprint, fail-safe to the full list (no poisoned cache on transient errors); `run.py:254` uses it for available_groups. **132 hermetic tests pass** (5 new). LIVE probe: 88 groups → 60 targetable (All Props/Small Flakes/Windows and Doors EXCLUDED; numbered taxonomy + Matrixes/Arches KEPT). Re-shakedown: skips 15→0, dead sections 4→0, zero placement errors in the revision log.

## 1. Probe + cache

- [x] 1.1 `targetable_groups(client, *, cache_root) -> list[str]`: layout fingerprint = `sha1(",".join(sorted(get_group_names())))[:16]`; if `<cache_root>/targetable_groups_<fp>.json` exists → return it (no probe)
- [x] 1.2 Probe (cache miss): `close_sequence(force,quiet)` → `new_sequence(duration_secs=10, force=True)` → **`await asyncio.sleep(0.8)` (elements-populate race — load-bearing)** → for each group `place_preset(... "On", candidate_look_ids("On")[0] ...)`, keep successes, skip **only on `XLightsTargetMissing`**; then `close_sequence` (never save); write the success list to the cache
- [x] 1.3 Fail-safe: a non-`XLightsTargetMissing` error mid-probe, a setup failure, or an empty result → return the full `get_group_names()` list and **do NOT write the cache** (never `[]`, never a poisoned cache)

## 2. Wiring

- [x] 2.1 `run_pipeline` (run.py:254): `st.available_groups = await targetable_groups(client, cache_root=_cache_root())` instead of `get_group_names()` — Director/Generator code unchanged

## 3. Tests & verification

- [x] 3.1 `targetable_groups`: fake client whose `place_preset` succeeds for some names and raises `XLightsTargetMissing` for others → returns only the successes; sequence is never saved
- [x] 3.2 Cache: first call writes `targetable_groups_<fp>.json`; second call returns it WITHOUT re-probing (fake client records 0 probe calls the second time); changing the group set → new fingerprint → re-probe
- [x] 3.3 Graceful: a probe that yields empty → full list. **A non-`XLightsTargetMissing` error mid-probe → full list AND no cache file written** (no poisoned cache); next call re-probes
- [x] 3.4 Live (gated): probe the real layout → `All Props`/`Small Flakes`/`Windows and Doors` EXCLUDED, `02_GEO_Center`/`Matrixes`/`Arches`/numbered groups INCLUDED; re-run the Mad Russian shakedown → skip count + dead sections drop sharply
