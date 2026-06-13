## 1. Stem-parameterized triggers

- [ ] 1.1 `triggers.py`: `TriggerSpec.stem` (default "drums"); detector signature → `(sa, sections, spec)`; `stem_onsets` detector reads `spec.stem`; `drum_onsets` = alias forcing drums
- [ ] 1.2 `stem_prominent` eligibility reads `spec.stem` (drum_prominent kept); parse `stem` in the cookbook loader

## 2. Cookbook + palette

- [ ] 2.1 `xlights-trigger-cookbook.md`: a "Piano Note Chase" trigger (stem_onsets / stem piano / stem_prominent / groups rhythm / On pop / rotate) + document the `stem` field
- [ ] 2.2 `agents/director.py`: holiday red/green/white palette bias in the per-section palette guidance

## 3. Tests & verification

- [ ] 3.1 Hermetic: `stem_onsets` fires on the named stem; `stem_prominent` uses it; default stem = drums (back-compat); piano trigger rotates groups per note; unknown/absent stem → no events
- [ ] 3.2 Live: re-run Christmas Canon → piano-note pops walk the props in the piano-prominent intro; the palette leans red/green/white; objective holds; user verdict
- [ ] 3.3 PR (user merges)
