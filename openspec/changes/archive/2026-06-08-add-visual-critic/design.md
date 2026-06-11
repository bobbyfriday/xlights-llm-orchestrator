## Context

Gives the refine loop eyes. The whole pipeline was **proven live this session**: ported the sibling repo's fseq+layout, rendered the real Baby Shark show (3853 frames, 81 models, 67k pixels) to a recognizable still, and `gemini-3.1-pro-preview` critiqued it accurately. This change packages that into `xlights-core` + an orchestrator agent + loop wiring.

Hard grounding — **we do not use xLights for pixels.** Every xLights export/preview route crashes or hangs (`exportVideoPreview` H.264 bitrate-0 encoder abort; media-attach re-entrant-HTTP crash + interactive modal; no playback/seek/screenshot commands). See [[xlights-automation-quirks]]. We render offline from on-disk artifacts instead.

## Goals / Non-Goals

**Goals:** offline still-frame renderer from `.fseq` + `rgbeffects.xml` + `networks.xml`; a multimodal `visual_critic` returning scoped findings; consulted by the refine loop before the human checkpoint; hermetic tests; graceful when render data is absent.

**Non-Goals:** pixel-perfect rendering of every model type; video/temporal critique; auto-applying suggestions; checkpoint edit/redirect UX.

## Decisions

### Offline renderer in `xlights-core/preview/` (ported from `xlight-autosequencer/src/video/`)
Three modules, adapted from the user's **proven** sibling code (credited in module docstrings):
- **`fseq.py`** — FSEQ v2 (PSEQ) zstd reader → `(header, frames[num_frames, channels] uint8)`. Walks the compression-block index, zstd-decompresses each block. Reused near-verbatim.
- **`layout.py`** — `parse_controllers(networks.xml)` (sort by Id, accumulate channel ranges) + `resolve_start_channel("!Controller:N" → absolute)`; `parse_models(rgbeffects.xml)`; `model_world_pixels(model)` returning Nx3 world coords per pixel. **Carries the hard-won gotchas:** boxed models use `Scale×2` (full extent), matrix/custom use `Scale` as per-pixel units; Horiz/Vert Matrix string/strand/zigzag node order; Arches half-sine; Cube/Star/Tree; unknown → strip fallback. Reused near-verbatim. **Added:** `parse_models` returns/logs a **placed-vs-skipped count** (models dropped because `resolve_start_channel` is `None`) — a silently-incomplete layout would make the critic mis-judge coverage, so partial coverage is surfaced.
- **`render.py`** — **dual-mode** (both proven live this session). A `PreviewRenderer(fseq, rgbeffects, networks)` precomputes world pixels + channel map + ortho projection once (load fseq once), then:
  - **`render_frame(t_ms, canvas=(1280,720)) -> bytes(PNG)`** — splat the frame's RGB (`np.maximum`) at each pixel's screen position; optional Gaussian bloom; PNG via Pillow.
  - **`render_clip(start_ms, end_ms, canvas=(640,360), crf=30) -> bytes(MP4)`** — adapted from the sibling `renderer.py` ffmpeg pipe: stream the frame range as rawvideo `rgb24` → `libx264` silent MP4 (low-res/low-crf to bound size; a 10s clip ≈ 160KB). Used for the **dynamic** critique. Requires the `ffmpeg` system binary (graceful: no ffmpeg → skip clips, stills still work).
  Both modes proven on our own `LLM_ORCH_SHOW.fseq` this session.

`[preview]` optional-dependency extra on `xlights-core`: `numpy`, `zstandard`, `pillow` (+ `scipy` only if bloom enabled). No LLM/xLights deps. Guarded imports → if `[preview]` absent, the orchestrator skips visual critique (graceful).

### `visual_critic` agent (`agents/visual_critic.py`, multimodal)
`build_agent("visual_critic", output_type=VisualFindings, ...)` (role already in the registry → `gemini-3.1-pro-preview`/Opus). `render_input(media: list[(label, png, mp4)], plan, brief) -> list[BinaryContent|str]` — a prompt describing the show intent (themes/sentiment, per-section labels) followed, per section, by the **still** as `BinaryContent(media_type="image/png")` and the **clip** as `BinaryContent(media_type="video/mp4")` (both proven). The prompt asks for spatial findings (coverage/color) from the still and motion/energy findings from the clip. Output `VisualFindings{ summary: str, findings: list[Finding] }` — an overall natural-language paragraph **plus** per-finding `Finding{ scope, severity, detail, frame }` (the `detail` is the model's plain-language observation; `frame` references which still it came from). Mapped into the refine `Finding`/`RevisionBrief` shape. Findings are **advisory** to the loop (like variety) — they inform the Judge/human, they **do not** enter `objective_score`/`_obj`, so a vision model never silently triggers the objective revert (taste ≠ objective regression).

### Human-readable, persisted review artifacts
Each refine iteration (and the initial draft) writes a **reviewable bundle** to `data/orchestrator/<song_key>/visual_review/<iter>/`: the sampled **PNG stills** + the **MP4 clips** (named `s<idx>_<label>_<t>s.{png,mp4}` — exactly what the model saw), **`findings.json`** (structured `VisualFindings`), and **`review.md`** (each still + a link to its clip with the critic's findings beneath it + the Judge's score/verdict + which findings escalated). So a human can open the frames/clips and read the analysis side-by-side, and diff across iterations. The checkpoint also prints the `summary` + findings to the terminal.

### Sampling — still + clip per section (`preview` + orchestrator glue)
For each `MusicBrief`/ShowPlan section: render (a) the **brightest still** in the window (spatial) and (b) a **short clip** of the section window (dynamic) — capped clip length (e.g. ≤10–12s, low-res `640×360`, ~20fps) to bound video size/token cost. Cap ~4–6 sections/critique. Timestamps come from the section boundaries already in `State`. Stills are cheap (every iteration); clips are the dynamic signal. (Config knobs: include-video on/off, clip length/res, sections cap.)

### Wiring into the refine loop (`pipeline/run.py`)
In the **test/decide phase** (already built in `show-refinement`): after `renderAll`+save, **locate the `.fseq`** in the sandbox container Data dir (`~/Library/Containers/org.xlights/Data/<seq>.fseq`; already written — no batchRender; skip if absent), render the sampled frames, write the **review bundle**, run `visual_critic`, and **merge its findings into the Judge/checkpoint input** — as **advisory** findings only (they go to the Judge and the human render; they are **not** added to `objective_score`/`_obj`, so they never drive the objective revert at `run.py:108`). The existing escalation logic (escalate to the human only when QA/Judge flag issues) now also fires on visual findings — so "models evaluate, then escalate to a human" falls out of the existing checkpoint gate. The visual critic is **injectable** (`visual_critic=`, `render_frames=`) like the rest, so the loop stays hermetic.

### `.fseq` resolution (no batchRender — render+save already writes it)
**Verified empirically:** the orchestrator's existing `renderAll` + `saveSequence` **already writes the `.fseq`** — we just looked in the wrong place. xLights on macOS is **sandboxed**: `getShowFolder` reports the configured show folder (`/Users/rob/xlights`), but the live sequence and its `.fseq` are written to the **app container** — `~/Library/Containers/org.xlights/Data/<seqname>.fseq` (confirmed: `LLM_ORCH_SHOW.fseq`, 9.5M, rendered from it successfully). So **no `batchRender`, no extra render step, no probe** — the `.fseq` is a side effect of the render+save we already do (`renderAll` is also safe/fast, ~2s). `render+save` to `getShowFolder` does NOT write a `.fseq`; the sandbox container does. **Resolution:** look up `<seqname>.fseq` in `~/Library/Containers/org.xlights/Data/` first, then `getShowFolder` (non-sandboxed installs), then skip gracefully if absent or `[preview]` isn't installed. (Earlier the "Baby Shark" proof used the user's pre-existing render; this now works on our own generated show.) **Rejected alternative:** parse the `RenderCache/` dir — internal/undocumented vs the documented `.fseq`. See [[xlights-automation-quirks]] for the sandbox-path finding.

### Testing (hermetic)
- **fseq**: commit a tiny synthetic FSEQ v2 fixture (or build one in-test: header + one zstd block) → `load_fseq` returns the expected `[frames, channels]`.
- **layout**: synthetic `Model`s (a Vert Matrix, an Arch, a Boxed) → `model_world_pixels` returns expected pixel counts and bounded extents; `resolve_start_channel` maps `!Ctrl:N` correctly.
- **render**: synthetic models + a frame of channel values → `render_frame` returns a non-empty PNG with lit pixels where expected.
- **visual_critic**: PydanticAI `TestModel` (stub `VisualFindings`) — no real vision call; `render_input` builds `BinaryContent` correctly.
- **loop**: stub visual critic returns a finding → the refine loop consults it and escalates; returns none → no escalation from vision; `[preview]`/`.fseq` absent → skipped.
- **Live (gated):** render the real show + `gemini-3.1-pro-preview` critique (the proof already run).

## Risks / Trade-offs

- **Renderer fidelity** — exotic model types fall back to a strip; acceptable for coverage/color critique (the proven render was clearly recognizable). If a critic finding traces to a mis-rendered prop, that's a layout-coverage bug to extend, not a correctness gate.
- **`.fseq` timing/availability** — depends on the orchestrator having rendered+written it; we resolve-or-skip, never force via the crashy export path.
- **Vision cost/latency** — stills + short clips/iteration on `gemini-3.1-pro-preview`; bounded by section cap + clip length/res (10s @ 640×360 ≈ 160KB inline, well under Gemini's inline limit); only when refine is on; video is config-gateable (stills-only fallback). Workers stay on flash.
- **`ffmpeg` system dependency** for clips — render+critique stills regardless; if `ffmpeg` is missing, skip clips (graceful), so the dynamic critique degrades to spatial rather than failing.
- **Advisory, not gating** — visual findings inform the Judge/human but don't drive the objective revert gate (taste ≠ objective regression), consistent with `show-refinement`'s objective/advisory split.
- **Ported-code drift** — we copy the sibling modules rather than depend on that repo; pin behavior with the fseq/layout fixtures so a future xLights format change is caught by tests.

## Open Questions

- Best frames-per-critique and canvas size for the cost/signal tradeoff — tune against the real show.
- Whether to also feed the visual critic's "All-Props group" style suggestions back as concrete `RevisionBrief`s the Generator can act on, vs. surfacing to the human — start with surfacing + advisory findings; auto-action later.
