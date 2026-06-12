## 1. Contracts + realization

- [x] 1.1 Branch `change/add-directional-sweeps`; `CellRecipe.direction` (default ""); generator prompt direction vocabulary (builds→up, releases→down, call-and-response→bounce/ltr+rtl)
- [x] 1.2 `weave.py`: `DIRECTION_KNOBS` per-effect map (SingleStrand Chase_Type1 incl. From/To Middle + Bounce variants; Bars up/down/H-expand/H-compress/expand/compress; Garlands; Meteors Up/Down/Explode/Implode; Fill/Wave/Curtain/Butterfly/Marquee/Fan/Galaxy/Pinwheel) — corpus values only; direction setting emitted per cell; static-direction effects flip value at bar boundaries under `bounce`; unknown pairs no-op
- [x] 1.3 `place_beat_accents`: bar-alternating rotation order (forward even bars, backward odd)
- [x] 1.4 `fallback_weave`: carrier direction "bounce"

## 2. Tests & verification

- [x] 2.1 Hermetic: knob emission per (effect, direction); native-bounce vs per-bar value flip; bar boundaries honored; accent rotation reverses per bar; fallback carries bounce; ""/unknown → byte-identical back-compat
- [x] 2.2 Live: one round-trip sanity check (SingleStrand `Chase_Type1=Bounce from Left` placed + read back); re-run carol of the bells → per-bar direction changes visible in the clip; no skip regression; objective holds
- [ ] 2.3 PR: push branch, `gh pr create` with change summary + live verification (user merges)
