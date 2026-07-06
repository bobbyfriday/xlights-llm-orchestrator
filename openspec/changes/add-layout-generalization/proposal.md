## Why

The orchestrator's entire choreography stack targets `SEM_` semantic groups — roles (`SEM_ARCHES`),
ensembles (`SEM_ALL`, `SEM_ALL_LESS_FOCAL`), bands and sides. The July roadmap's *Prop-grouping
assessment* confirmed this architecture is the right contract: it matches community practice,
respects the hard xLights constraint that groups load only at startup (so a static, pre-built
vocabulary is the only practical design), and several specifics — subtractive ensembles, empirical
targetability probing, one source of truth for names, flat groups — beat the obvious alternatives.

But the implementation covers only **half of `xlights-layout-semantics-spec.md`**. The current
`SEM_` group vocabulary was classified **once, by hand** for a single layout; that hand-classification
is the root of the single-layout coupling. The five gaps, verbatim from the assessment:

1. **The classifier is prose, not code.** Spec §3 (DisplayAs mapping → pixel-count disambiguation →
   name heuristics → group hints → LLM fallback) has no implementation; `layout_semantics.py` starts
   from already-classified `Prop` objects. No code writes the `SEM_` modelGroups either — group
   creation is agent/manual today.
2. **The §6 manifest is designed but never emitted or consumed — the biggest miss.**
   `layout_semantics.json` exists nowhere. The Director receives a flat list of group names, so the
   LLM plans knowing nothing of scale, geometry, or symmetry; QA fakes capability gating with name
   prefixes (`qa/rules.py::_LINEAR_PREFIXES`).
3. **Group render modes aren't code-managed.** Spec §5.7 requires "Per Preview" on ensembles and
   "Horizontal Per Model" on `_LTR` groups, but only `GridSize` is patched — a wrong mode silently
   breaks every sweep on that group.
4. **The choreography vocabulary is hardcoded to this layout's prop mix** (`METRIC_RING`,
   backbeat/bed preferences). A different prop mix gets a weaker beat anchor by accident, not by
   decision.
5. **Validation is manual.** The spec's §7 role-color and sweep tests are described but not
   implemented, even though the offline preview renderer and visual critic could run them — and
   misclassification poisons every downstream decision.

**Why now:** F-E is the step that turns a personal tool into a shareable one. Today, onboarding a new
layout means a human (or an ad-hoc agent session) reading the spec and hand-editing
`xlights_rgbeffects.xml` — exactly what `docs/usage.md` ("One-time layout setup", lines 53–69)
documents as a "manual/agent step today". F-E closes all five gaps as one guided CLI command,
`xlo init-layout`, and unblocks F-F (submodel targeting), sharing the tool with any layout,
manifest-grounded Director designs, and capability-class QA.

## What Changes

**F-E `xlo init-layout` onboarding — the new command:**
- Add a guided CLI subcommand `xlo init-layout [--show-folder PATH] [--dry-run] [--yes]
  [--no-validate] [--no-llm] [--invert-x] [--review-web]` that onboards an arbitrary xLights layout:
  analyze → review → write → manifest → validate.
- The command runs **fully deterministically with no LLM key** (steps 1–4 of the classifier) and
  must **not** require xLights to be running (it requires xLights *closed* for the write step).

**F-E classifier + spatial derivation (spec §3/§4 as real code):**
- New `knowledge/layout_classify.py`: `parse_props(rgb_path)` (dependency-free parser capturing
  `StringType`, `<subModel>` children, and user group membership), `classify(props)` (DisplayAs map →
  tree pixel-count disambiguation → name heuristics → group hints), `capability(role, nodes,
  string_type)` (capability classes from role + geometry), and `derive_spatial(props)` (outlier
  exclusion, normalization, bands/sides, sweep order, mirror pairs, center distance, focal flags).
- `Prop` gains three defaulted, backward-compatible fields: `mirror_of`, `string_type`, `submodels`.
- New optional `agents/layout_classifier.py`: one batched, enum-constrained LLM call for the
  unresolved tail; a `classifier` role in `models/config.yaml` routed to the worker tier.

**F-E the `SEM_` group writer (spec §5 + §5.7):**
- Extend `knowledge/layout_semantics.py` with `write_sem_groups()` — idempotently create/replace the
  `SEM_` `<modelGroup>` elements (never touching user groups), setting members, `GridSize`, and the
  §5.7 layout-mode attribute; timestamped backup; atomic tmp + `os.replace`; no-op when unchanged.
- Add `layout_modes(groups)` and a `LAYOUT_MODE_ORDERED`/`LAYOUT_MODE_ENSEMBLE` constant pair pinned
  by a per-version round-trip spike (not guessed).
- An **xLights-must-be-closed guard**: a connectivity-probe that refuses to write while the
  automation port answers.

**F-E the manifest (spec §6, emitted *and* consumed):**
- New `knowledge/layout_manifest.py`: `LayoutManifest`/`PropRecord`/`GroupRecord` pydantic models,
  `emit_manifest()` (writes `layout_semantics.json` < 10 KB to the show dir + a cache copy), and a
  tolerant `load_manifest()` (returns `None` when absent or version-mismatched).
- Consume the manifest in three independent integrations: (a) a compact Director traits/props block;
  (b) manifest-derived capability gating in `qa/rules.py` (prefix table kept as fallback); (c)
  mirror-pair/sweep-order choreography data.

**F-E derived choreography vocabulary:**
- `pipeline/semantic_groups.py` gains `ChoreoVocabulary` + `derive_vocabulary(manifest)` that ranks
  rhythm families by count, spread, and node budget; today's constants become `DEFAULT_VOCAB` (the
  no-manifest fallback and the tie-break prior). Thread `vocab` through `select_rhythm_groups`,
  `place_beat_accents`, and the weave bed selection.

**F-E automated §7 validation (offline, deterministic-first):**
- New `pipeline/layout_validate.py`: `write_fseq_v2_uncompressed()`, `role_color_frames()`,
  `sweep_frames()`, a **deterministic** sweep-centroid check (lit-pixel world-x centroid must be
  strictly increasing), and a role-color contact sheet PNG. Optional visual-critic pass (advisory).

**Migration (the existing hand-built layout must converge):**
- `xlo init-layout --dry-run` against the current real layout SHALL produce a byte-for-byte-or-
  explained-only membership diff. A per-layout `layout_overrides.json` records the irreducible
  judgment calls; divergences are fixed in the classifier or the overrides file, never by weakening
  the diff. A converged re-run is a byte-level no-op write.

## Capabilities

### New Capabilities
- `layout-onboarding`: the `xlo init-layout` command and its pipeline — classify props from an
  arbitrary `rgbeffects.xml`, review low-confidence classifications, write the `SEM_` groups + layout
  modes + grid size, emit the `layout_semantics.json` manifest, and validate role-color/sweep
  correctness offline.

### Modified Capabilities
- `show-orchestration`: the manifest requirement defers to `layout-onboarding` as the contract's
  single canonical home, and the QA-capability-gating and choreography-vocabulary requirements
  become manifest-derived (rather than hardcoded), with a no-manifest fallback that keeps today's
  behavior byte-identical. The classifier/spatial-derivation source of `SEM_` groups (replacing the
  hand-classification), the §5.7 layout-mode attribute, and the convergence-with-current-layout
  invariant live in `layout-onboarding` (above); the semantic-group requirement itself is
  deliberately not modified here, to avoid overlapping `add-asset-bound-placement`'s delta on the
  same requirement.

## Impact

- **xlights-core:** new `knowledge/layout_classify.py`, new `knowledge/layout_manifest.py`, extended
  `knowledge/layout_semantics.py` (`Prop` fields, `write_sem_groups`, `layout_modes`); reuses
  `preview/layout.py`, `preview/render.py`, `preview/fseq.py`.
- **xlights-orchestrator:** new `pipeline/init_layout.py`, new `pipeline/layout_validate.py`, new
  optional `agents/layout_classifier.py`; modified `pipeline/semantic_groups.py`
  (`ChoreoVocabulary`/`derive_vocabulary`), `pipeline/beats.py` (`select_rhythm_groups` vocab param),
  `pipeline/weave.py` (bed selection), `agents/director.py` (`render_layout_block` + manifest arg),
  `qa/rules.py` (`_target_res`/manifest-aware `_is_linear`), `pipeline/run.py` (wiring behind
  `load_manifest`), `cli.py` (`init-layout` subcommand), `models/config.yaml` (`classifier` role).
- **Docs:** `docs/usage.md` "One-time layout setup" rewritten around the command.
- **Tests:** synthetic fixture rgbeffects (`layout_basic.xml`, `layout_tricky.xml`), a sanitized real
  layout (`layout_real.xml`) + golden manifest, a `layout_modes_roundtrip.xml` spike artifact;
  hermetic classifier/spatial/writer/manifest/validation/consumption/CLI tests; one opt-in `-m live`
  suite. The golden pipeline test stays byte-identical (DEFAULT_VOCAB == today's constants).
- **Risk profile:** additive and backward-compatible everywhere on the current layout — no manifest
  means byte-identical Director prompt, prefix-fallback QA, and `DEFAULT_VOCAB`. The one behavioral
  change gated by a golden snapshot is the derived vocabulary, which must reproduce today's constants
  from the real-layout manifest before shipping as default. Live-verified once on the real layout.
