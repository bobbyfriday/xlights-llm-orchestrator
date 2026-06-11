> **Build notes (this session):** Implemented offline; verified with `venv`+`pip`. Ran the
> extractor over `/Users/rob/xlights`: **17 files, 37 effect types** (42 − 5 asset-bound),
> **1,183 looks, 376 palettes**; skipped 453 asset-type + 197 timing-track-VC effects. Catalog
> committed to `knowledge/presets/` (looks.json 2.1 MB, palettes.json 196 KB). All offline tests
> pass; live replay (6.6) deferred to the write-path change.

## 1. Knowledge package scaffold

- [x] 1.1 Create `packages/xlights-core/src/xlights_core/knowledge/` package (`__init__.py`) and a `presets/` output dir
- [x] 1.2 Define constants: `ASSET_BOUND_TYPES` + key→control-type classifier (`classify_kind`) + timing-track curve detector
- [x] 1.3 Pydantic models: `Knob`, `Look`, `Palette`, `Catalog`

## 2. Extractor: parse + dereference

- [x] 2.1 `xsq_extractor.iter_corpus(show_dir)`: yield community `.xsq` — author not starting "xlight"; top-level glob (never enters `Backup/`)
- [x] 2.2 Parse each file via ElementTree: `<EffectDB>` + `<ColorPalettes>` indexed lists; `<author>`/`<version>` from `<head>`
- [x] 2.3 Walk placed `<Effect ref name palette/>`; dereference; skip `ASSET_BOUND_TYPES` (logged)
- [x] 2.4 Settings parse helper (`settings.py`): split on `,`, then `split("=",1)`; empty → `[]`

## 3. Build parameterized looks

- [x] 3.1 Key-signature = sorted set of key names; group a type's settings by signature
- [x] 3.2 Per group: frozen base = keys constant across members; knobs = keys that vary
- [x] 3.3 Per knob: classify kind by prefix; SLIDER → numeric `[min,max]`; else option set; default = most-frequent
- [x] 3.4 Value-curve knobs: parse nested blob; classify parametric/custom/timing-track; store structured; observed-only (no synthesis); overridable via `assemble`
- [x] 3.5 Active timing-track value curves treated as asset-dependent → settings excluded (197 skipped)
- [x] 3.6 Record `source_versions` per look; empty/default settings → a look with no knobs

## 4. Build palettes + emit catalog

- [x] 4.1 Palette dedup by **color-set** (sorted unique `#RRGGBB`); representative keeps real slot order; tags `count`, `monochrome`, `warm`/`cool`
- [x] 4.2 Emit committed JSON: `knowledge/presets/looks.json`, `palettes.json`
- [x] 4.3 Log totals (types, looks, palettes, skipped) — printed by the CLI

## 5. Lookup + emit API (`preset_library.py`) and validators

- [x] 5.1 `PresetLibrary` loads committed catalogs (process-cached `get_library()`); `list_effect_types`, `get_looks`, `get_palettes`
- [x] 5.2 `assemble(look, knob_values=None)`: fill knobs (chosen/default), emit `KEY=VALUE` for frozen+knobs in canonical `key_order`
- [x] 5.3 `validators.py`: SLIDER ∈ observed `[min,max]`; categorical/value-curve ∈ observed set; reject otherwise (no VC synthesis)
- [x] 5.4 Provenance: enforced **per-knob** (observed sets) by validators, and palettes are emitted **verbatim** from the corpus. (Refined from the original "default-only assembled string ∈ corpus_members" — that whole-string check is unsound under parameterization since per-knob defaults may not co-occur; the per-knob guarantee is the correct, spec-aligned one. No separate `corpus_members` file needed.)

## 6. Tests & verification

- [x] 6.1 Mining test (corpus-gated): excludes `xlight*`-authored + `Backup/`; no `2026` versions; omits all `ASSET_BOUND_TYPES`; asset + timing-track skips > 0
- [x] 6.2 Lossless round-trip: every EffectDB settings string round-trips through parse/serialize (key/value equivalence; >1000 checked)
- [x] 6.3 Knob constraints: in-range slider accepted; out-of-range + unobserved categorical rejected; VC accepts only observed blobs
- [x] 6.3b Value curves: classification (parametric/custom/timing-track); no timing-track curves in catalog; numeric-knob override applied in assembly
- [x] 6.4 Decoupling/provenance: no look's frozen/knob values contain `#` hex or `C_BUTTON`; every look has `source_versions`
- [x] 6.5 API tests: `list_effect_types` excludes asset-bound; `get_looks` returns looks-with-knobs; `assemble` defaults + chosen knobs are well-formed; palette tag filter works
- [ ] 6.6 (Deferred — needs write path) Live validation by replay via `addEffect` + `checkSequence` (incl. novel knob combinations + key-order assumption); tracked against change `add-xlights-mcp-effect-editing`
