## Why

"Color Wash" — a standard, common xLights wash/bed effect with 666 mined looks — was on `KNOWN_REJECTED_TYPES`, excluded from the placeable set because `addEffect` returned `worked=false` for it. A live re-test (2026-06-14) shows that conclusion is **stale**: `addEffect(target, "Color Wash", …)` now returns **`worked=true` and renders cleanly**. Only the no-space `"ColorWash"` and lowercased `"Color wash"` fail.

The original rejection was almost certainly a casualty of the `+`-vs-`%20` GET-encoding bug (fixed 2026-06-10, the same bug behind the "dark chorus"): back then `"Color Wash"` went over the wire as `"Color+Wash"`, didn't match xLights' effect registry, and failed. The encoding fix repaired it, but Color Wash stayed blacklisted and was never re-tested — the editable-brief schema validation surfaced it (the director used Color Wash 7× in one brief, all flagged).

Keeping it blocked means the director's frequent, legitimate wash choices are silently dropped/substituted, and a genuinely useful bed effect is unavailable.

## What Changes

- **Unblock Color Wash (code):** remove `"Color Wash"` from `KNOWN_REJECTED_TYPES` (the set stays as the mechanism for any genuinely-unplaceable type; it's now empty). Color Wash joins `placeable_effect_types()`, so the director may use it and the brief schema enumerates it.
- **Fix a stale substitution example (code):** the generator's scene note used "a Color Wash bed → a dim On" as its substitute-the-non-placeable example; swap it for a neutral phrasing since Color Wash is now placeable.
- **Correct the memory/quirks note** so the blacklist rationale isn't re-applied.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `show-orchestration`: "Color Wash" SHALL be treated as a placeable effect type (available to the director and the brief schema), having been re-verified to place and render via `addEffect`.

## Impact

- `agents/catalog.py` (`KNOWN_REJECTED_TYPES` emptied); `agents/generator.py` (substitution example); `tests/test_orchestrator.py` (assert Color Wash placeable, mechanism intact). Back-compat: additive — Color Wash becomes available; nothing that worked stops working. Re-running a song lets its washes actually place instead of being dropped.
