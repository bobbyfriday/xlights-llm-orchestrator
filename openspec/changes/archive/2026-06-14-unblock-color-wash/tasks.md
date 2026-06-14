## 1. Unblock

- [x] 1.1 `agents/catalog.py`: empty `KNOWN_REJECTED_TYPES` (remove "Color Wash"), with a comment recording the 2026-06-14 re-verification (places + renders; was a `+`/`%20` casualty).
- [x] 1.2 `agents/generator.py`: reword the scene substitution example that used "Color Wash bed → dim On" (Color Wash is now placeable).

## 2. Tests & memory

- [x] 2.1 `tests/test_orchestrator.py`: assert "Color Wash" IS in `placeable_effect_types()`; keep the reject-mechanism check.
- [x] 2.2 Correct the `xlights-automation-quirks` memory note (Color Wash placeable after the encoding fix).
- [x] 2.3 Full suite passes.

## 3. Verify + land

- [x] 3.1 Live (done during investigation): `addEffect("Color Wash")` → worked=true; `renderAll` clean.
- [x] 3.2 Archive, commit, push, open PR (user merges).
