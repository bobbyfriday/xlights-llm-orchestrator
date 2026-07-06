# F-J spike write-up — "what truly requires live xLights?"

**Status:** decision-first spike (this change ships the durable artifact + the decision, NOT a
headless emitter). The live S1/S3 probes are `XLO_LIVE=1`-gated in `scripts/spike_fj_fidelity.py`
and never run in CI.

## What shipped in this change (durable artifacts)

1. **A checked-in fixture** `tests/fixtures/fj_headless/` — a 69-byte zstd `.fseq` (36 channels ×
   20 frames, a dark first half + a bright second half) plus its `xlights_rgbeffects.xml` /
   `xlights_networks.xml` layout pair. Small by construction so the CI eval seed doesn't bloat the
   repo (`test_fixture_fseq_is_small` guards `< 4 KB`).
2. **A hermetic eval seed** — `tests/test_headless_fixture.py` runs the offline `PreviewRenderer`
   lit-pixel sampler and the coverage QA + a Tier-0-style peak-normalized lit-fraction metric over
   the fixture, with **no live xLights**. It proves the offline stack (fseq decode → world-pixel
   projection → render → coverage) is fully exercisable in CI. This is the seed of the eventual
   full-pipeline CI eval suite.
3. **The spike's pure helpers, unit-tested** — `project_group_mask`, `frame_deltas`
   (brightness/lit-fraction-agreement/hue-distance), and `fseq_channel_diff` (S3's ≤1-LSB gate)
   live in `scripts/spike_fj_fidelity.py` and are tested against tiny synthetic inputs + the real
   fixture, so the fidelity/CLI-render *logic* is verified even though the live probes are gated.

## S2 — client-call re-inventory (hermetic, done here)

Re-grepping `client.*` across `packages/xlights-orchestrator/src` and `xlights_core/editing.py`
confirms the design's inventory holds: the run touches a small set of `XLightsClient` methods →
REST commands, of which only two genuinely require the *live* app mid-run:

- the **once-per-layout targetability probe** (`groups._probe` → `newSequence`/`addEffect`/
  `closeSequence` on a disposable sequence), and
- **`render_all`** (producing the `.fseq` the offline replayer then reads).

Everything else (reads, `addEffect` placement, `saveSequence`) is I/O the offline `.xsq` mutation
path in `finalize.py` already proves is doable off the live app. **Confirmed inference:**
`RealRender` never engages mid-run on the media-less in-run ANIMATION sequence — the guardrail
(`get_open_sequence().media` empty → `False`) short-circuits before any export, so the refine
loop's in-flight critique/sampler decisions *already* run on offline renders today. The live app's
irreplaceable mid-run contribution is producing the `.fseq`.

## S1 / S3 — live probes (gated, not run in CI)

`run_s1_fidelity` (offline-vs-real per-section/per-group deltas → `fidelity_report.json`) and
`run_s3_cli_render` (prototype xLights batch/CLI render on macOS then Linux/Xvfb; byte/channel diff
of the produced `.fseq` against the REST render) are documented skeletons behind `XLO_LIVE=1`. They
are the evidence gate for option (a) and require a workstation with xLights + the fixture open.

## Decision table → chosen follow-up

Against the design's decision table (`design.md` `## Notes` → F-J):

| Outcome | Follow-up |
|---|---|
| S3 headless render works on Linux (Xvfb) **and** `.fseq` ≤1 LSB/channel **and** wall time ≤2× REST `renderAll` | **option (a)** — a file-based emitter + `BatchRenderer` behind the existing `emitter=` seam (a separate OpenSpec change), live xLights only for the pre-seeded targetability probe |
| S1 per-group lit-fraction decisions agree ≥95% and keep/revert outcomes match | **hybrid** — offline eval + batched renders, one real-render gate before finalize (shares I8 Tier-0 code) |
| S3 fails / S1 gap large | **fallback** — keep live xLights, batch the interactions |

**Recommendation pending the live probes: pursue the two cheap wins now, gate option (a) on S3
evidence.** The fixture-based CI eval seed (shipped) and the optional `get_models` prefetch batching
seam land regardless of S3's outcome. Option (b) — reimplementing the xLights render engine in
Python — stays **rejected without a spike task**: the render *is* the ground truth the offline
replay is measured against, so approximate parity is worse than useless.

**Named follow-up:** *"file-based emitter + `BatchRenderer`"* as its own OpenSpec change, gated on a
green S3 run (`XLO_LIVE=1 uv run python scripts/spike_fj_fidelity.py --step s3`). Until then the
fixture + hermetic eval seed is the concrete progress.
