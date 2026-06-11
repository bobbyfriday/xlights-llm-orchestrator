## Context

The keystone capability. Built on facts established by exploring the real corpus at `/Users/rob/xlights` (see project memory `preset-corpus`):

- **Corpus:** 17 community-authored `.xsq` (`<author>` empty or "John Storms", xLights 2020.45–2023.20). Exclude `xlight-autosequencer`-authored files (19) and `Backup/` (~797 snapshots).
- **.xsq dedup-by-reference:** `<EffectDB>` is an ordered list of distinct settings strings; `<ColorPalettes>` an ordered list of palette strings. Each placed effect is `<Effect ref="R" name="TYPE" startTime endTime palette="P"/>` referencing `EffectDB[R]`/`ColorPalettes[P]`. (Verified: 0/29,014 placed effects miss `name=`/`palette=`.)
- **Settings string** = CSV of `KEY=VALUE`. Keys are **self-describing**: `E_/B_/T_/C_` prefix + control type (`SLIDER`, `CHOICE`, `CHECKBOX`, `VALUECURVE`, `TEXTCTRL`, `NOTEBOOK`, `BUTTON`). 98.4% of keys classify by prefix. Value-curves embed a `|…|`-delimited blob. **Palette string** = `C_*` only.
- **Measured scale:** 42 types, 4,108 distinct non-asset settings, 1,469 palettes (416 color-sets), 29,014 placed. Colors 100% decoupled (0/29,014 settings carry a hex/`C_BUTTON`). Comma-in-value: 0 cases (naive `,` split is safe). Empty/default settings: 15 distinct.
- **Parameterization is mechanical:** worst-case look (Shockwave, 1,656 placements) → 4 frozen + 6 typed knobs (a CHOICE with 8 options, sliders with clean numeric ranges).

## Goals / Non-Goals

**Goals:**
- A committed, offline-generated catalog of **parameterized looks** + a palette catalog, with a lookup + assemble API.
- Strong offline guarantees: lossless round-trip; every emittable value constrained to the corpus per knob.
- The final public contract (catalog schema + API) so downstream agents don't get refactored later.

**Non-Goals:**
- Asset-bound types (Faces, Pictures, Video, Shader, DMX).
- Live replay validation (needs `addEffect` → change `add-xlights-mcp-effect-editing`).
- LLM descriptions, semantic retrieval, palette parameterization.

## Decisions

### Parse `.xsq` via the EffectDB/ColorPalettes reference model
Read `<EffectDB>` and `<ColorPalettes>` into indexed lists, walk placed `<Effect ref name palette/>`, dereference. Settings/palette payloads are plain strings. `xml.etree.ElementTree` for structure; `<head>` gives `<author>`/`<version>` for the corpus filter + provenance.

### Corpus filter by `<author>`; skip `Backup/`
Include iff `<author>` does not start with "xlight" (case-insensitive); always skip paths under `Backup/`. Author is the reliable provenance discriminator from exploration.

### Settings parse: split on `,`, then `=` once
`KEY=VALUE` via `seg.split("=", 1)` per comma-segment. Safe because no value contains a comma (verified 0 cases); values *do* contain `=` (value-curves), so split only on the **first** `=`. Empty settings → a look with no keys (the "default" look).

### Look = key-signature group → frozen base + typed knobs
Group a type's settings by **key-signature** (sorted set of key names). For each group:
- **frozen base** = keys whose value is identical across every string in the group.
- **knobs** = keys whose value varies. Each knob is typed from its key (`SLIDER`/`CHOICE`/`CHECKBOX`/`VALUECURVE`/`TEXTCTRL`/`NOTEBOOK`/`BUTTON`/other) and records observed values + a default = most-frequent observed.
This compresses 4,108 strings → ~1,194 looks whose knob ranges *cover* all variants — resolving the earlier lossy-vs-bulky dilemma (knobs preserve variety without storing every string).

### Value curves (a knob whose value is a nested mini-DSL)
A value-curve key's value is itself `Active|Type|Min|Max|P1|P2|P3|RV|Values`. Corpus reality (mined): 957/4,433 settings use one; 77 VC-enabled keys; Active≈TRUE almost always. Type mix: **~85% parametric** (Ramp 635, Sine 342, Ramp Up/Down 149, Saw Tooth 93, Parabolic/Exp/Square ~10), **~8% Custom** (explicit `Values=t:v;…`), **~2% Timing-Track-Fade**.

Three classes, handled differently:
- **Parametric** (closed-form): xLights generates the shape from `Type` + numeric params. Parse into structured sub-fields. *Synthesizable later* (as safe as sliders, within observed ranges) — but **deferred**; v1 reuses observed values only.
- **Custom** (point list): opaque hand-drawn shape. Categorical-from-observed; never fabricated offline.
- **Timing-Track-Fade**: references a named timing track → **asset-dependent** (a hidden asset dep *inside* a value curve). Exclude/flag like Faces/Pictures — a reused one points at a track that may not exist.

**v1 decisions:** parse every VC into structured form and **classify** (parametric/custom/timing-track); store structured (not as an opaque blob) so parametric synthesis and audio-derived curves are clean later additions; emit **only observed** VC values (no synthesis); keep VC knob values **overridable** by callers. When synthesizing/regenerating a VC, the embedded `Id=ID_VALUECURVE_<keytail>` must stay consistent with its key — another reason to keep structure, not strings.

**Forward pointer (not this change):** value curves are the **audio→light bridge** — the orchestrator's real payoff is generating *Custom* curves from the audio analysis (a brightness curve = the energy envelope; a speed ramp into the drop). Those are novel strings → live-validated by change ③, then supplied via the override seam above. Designing VC values as overridable now is what makes that clean.

### Per-knob validity model (the new guarantee)
Assembly accepts a knob value iff:
- **SLIDER / numeric** → within the observed `[min,max]` (interpolation allowed; xLights sliders accept any in-range value).
- **CHOICE / CHECKBOX / TEXTCTRL / NOTEBOOK / BUTTON / value-curve / "other"** → categorical: must equal an observed value. Value-curves are **never** synthesized.
The 1.6% of keys not matching a known control prefix default to **categorical** (safest). `validators.py` enforces this before assembly.

### Assembly + ordering
`assemble(look, knob_values) -> settings_string`: for every key (frozen + knobs) emit `KEY=value` (frozen value, or chosen knob value, or knob default), joined by `,`. Emit in a **canonical key order** (the representative's order). xLights parses settings into a map, so order is assumed non-significant — flagged as an assumption to confirm during live validation (③). Lossless round-trip is guaranteed *per source* by re-emitting a source's own key order+values.

### Two-axis catalog as committed JSON under `knowledge/presets/`
`looks.json` (per type: looks with frozen base + knobs) and `palettes.json`. Also persist a **corpus membership set** (hashes of every observed settings/palette string) so `validators.py` can prove provenance offline. Catalog is committed (reviewable/diffable, runtime dependency-free), re-generated when the corpus changes.

### Palette dedup by color-set + mechanical tags
Canonicalize by sorted unique `#RRGGBB`; one representative per color-set; tag `count`, `monochrome`, `warm`/`cool` (hue heuristic). No LLM.

## Risks / Trade-offs

- **Knob independence (the key new risk):** observed variants are whole-string combos; choosing knobs independently can yield a combination never seen. It almost always still renders (xLights ignores cross-key correlation), but may be aesthetically odd or occasionally inert (a choice meaningful only when a checkbox is on). → Mitigation: this is exactly what **live validation (③: `addEffect` + `checkSequence` + visual preview)** catches, and novel combos are parameterization's payoff anyway. Until ③, callers can stay on defaults/observed values.
- **Validity guarantee weakened** from "exact corpus string" to "per-knob constrained." → Sliders-in-range are safe by xLights' nature; categorical knobs are corpus-exact; value-curves never synthesized. Net risk is low and bounded.
- **Cross-version drift (2020–2023 → 2026):** a look's signature may span versions (144 such groups). → Record the **set** of source versions per look; frozen-base values are taken from observed strings (prefer newest when a frozen value somehow differs — shouldn't, since frozen = constant). True confirmation is the deferred live check.
- **Key-order assumption:** assembled canonical order differs from some source strings. → Assumed non-significant (map parse); confirm in ③. Round-trip test uses per-source order to prove no data loss regardless.
- **Value-curve format fragility:** the nested `|`-delimited blob is strict, and `Id=ID_VALUECURVE_<keytail>` must match its key. → v1 reuses observed VC values verbatim (no reassembly risk); structured parsing is stored but only *round-tripped* (parse→reassemble == source) in tests, not synthesized. Parametric synthesis (which reassembles) is deferred to ③ where `checkSequence` can catch a malformed curve.
- **Hidden VC asset deps:** timing-track-fade curves reference a named track. → Classified and excluded/flagged alongside the asset-bound effect types.

## Open Questions

- Confirm the asset-bound set is complete against the full mined type list (e.g., any GPU/transform effect referencing files under a different type name).
- Final catalog totals (looks per type, knob counts, palettes) — log during extraction.
- Whether to also expose, per knob, the observed *frequency* (to weight a generator's defaults) — cheap to add; decide during build.
