## 1. Core — colors.py achromatic anchor fallback

- [x] 1.1 Add a small value-variant helper in `xlights_core/knowledge/colors.py` (same hue/sat,
      value scaled to ~0.35) or reuse `_variant` if it fits
- [x] 1.2 Rework the `contrast_anchors()` fallback: when the floored palette has <2 chromatic
      colors, return the two most value-separated resolvable colors; when value separation is
      still small (all near-white), pair the brightest color with its dimmed variant — replacing
      the `(first, "#FFFFFF")` fallback
- [x] 1.3 Unit tests in `tests/test_led_readability.py`: all-achromatic palette returns a
      value-separated pair (never two near-whites); single-chromatic palette still gets a
      complement pair; existing chromatic behavior unchanged

## 2. Pipeline — the section-palette floor in the color script

- [x] 2.1 Add a floor move to `pipeline/color_script.py`: a helper that floors one palette via
      `ensure_contrast`, snapping any injected complement to the nearest chromatic
      `NAMED_COLORS` entry by hue (skip candidates within 60° of the existing cluster; fall back
      to the raw hex)
- [x] 2.2 Run the floor as the final move of `apply_color_script` (after anchor thread, chorus
      signature, bridge contrast), mutating `sec.palette` in place; update the module docstring
      to "four moves"
- [x] 2.3 Unit tests in `tests/test_color_script.py`: all-warm section gains a cool complement
      (spread ≥60°); all-achromatic section unchanged; already-contrasting section unchanged;
      idempotent on a second run; snapped color is a `NAMED_COLORS` name when hue-close
- [x] 2.4 Fix any existing test fixtures/assertions that assume unfloored all-warm palettes

## 3. Verification and docs

- [x] 3.1 Run the full test suite and the mypy gate; fix fallout
- [x] 3.2 End-to-end smoke: generate a plan for a warm-leaning song and confirm every section's
      realized palette has `hue_spread ≥ 60°` or is all-achromatic (assert via a quick script or
      test over the emitted show plan)
- [x] 3.3 Update `docs/color-design.md`: §1.3/§1.4 describe the floor as shipped behavior,
      §1.6 #1–2 drop off the missing list, §5 #1 status flips to built
