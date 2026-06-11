> **Build result (verified live on Gemini):** `xlights-core/preview` (fseq zstd reader, layout with scale/matrix geometry + placed-vs-skipped log, dual-mode renderer → still PNG + clip MP4) ported from the sibling repo; `visual_critic` agent (image+video, advisory findings); sampler + sandbox `.fseq` resolution + loop wiring + human-readable review bundle. **86 hermetic tests pass** (10 new). Live: rendered our own show's stills+clips offline (no xLights) and gemini-3.1-pro-preview caught a DARK CHORUS (coverage error) + static intro (motion) → wrote a review bundle (4 stills + 4 clips + findings.json + review.md). No batchRender, no crashes. Gemini upgraded to 3.x (google: prefix) + visual_critic role landed earlier.

## 1. Offline renderer (xlights-core/preview, ported)

- [x] 1.1 Add `[preview]` extra to `xlights-core` (`numpy`, `zstandard`, `pillow`; `scipy` optional for bloom)
- [x] 1.2 `preview/fseq.py`: port the FSEQ v2 zstd reader (`load_fseq(path) -> (FseqHeader, frames[num_frames,channels] uint8)`); credit `xlight-autosequencer/src/video/fseq.py`
- [x] 1.3 `preview/layout.py`: port `parse_controllers` + `resolve_start_channel` (`!Controller:N`→absolute) + `parse_models` + `model_world_pixels` (Scale×2 boxed vs per-pixel matrix; Horiz/Vert Matrix, Arches, Custom, Cube, Star, Tree; strip fallback); credit origin. **Return/log placed-vs-skipped model count** (models dropped on unresolved start channel)
- [x] 1.4 `preview/render.py` **dual-mode** `PreviewRenderer(fseq, rgbeffects, networks)` (precompute world pixels + channel map + ortho projection once): `.render_frame(t_ms) -> PNG bytes` (splat via np.maximum; bloom optional) AND `.render_clip(start_ms,end_ms, canvas=(640,360)) -> MP4 bytes` (ffmpeg rawvideo→libx264 silent clip, adapted from sibling `renderer.py`); guarded imports → graceful if `[preview]`/`ffmpeg` missing (clips skipped, stills still work)
- [x] 1.5 `preview/__init__.py` exports; brightest-frame-in-window helper for sampling

## 2. Visual critic agent

- [x] 2.1 `agents/visual_critic.py`: `VisualFindings` (**`summary: str`** + `findings: list[Finding]`, each `Finding` carrying a section/`frame` ref + plain-language `detail`); `visual_critic_agent()` (role `visual_critic`, multimodal output_type); `render_input(media:list[(label,png,mp4)], plan, brief) -> list[BinaryContent|str]` (intent + per section: still `BinaryContent(image/png)` + clip `BinaryContent(video/mp4)`; ask for spatial findings from stills + motion/energy findings from clips)
- [x] 2.2 Map `VisualFindings` → refine `Finding` shape; mark **advisory** (informs Judge/human; NOT added to `objective_score`/`_obj`)
- [x] 2.3 **Persist a human-readable review bundle** per iteration → `data/orchestrator/<song>/visual_review/<iter>/`: the sampled PNG frames, `findings.json` (the `VisualFindings`), and `review.md` (each frame + its findings + the Judge score/verdict + what escalated)

## 3. Frame sampling + loop wiring

- [x] 3.1 Sampler: per MusicBrief/ShowPlan section, render the **brightest still + a capped section clip** (length/res config; ~4–6 sections); build `(label, png, mp4)` list via `PreviewRenderer`; video config-gateable (stills-only fallback if disabled / no ffmpeg)
- [x] 3.2 **Resolve the `.fseq`** (already written by the existing render+save) from the macOS sandbox container `~/Library/Containers/org.xlights/Data/<seq>.fseq`, then `getShowFolder` (non-sandboxed fallback); if absent or `[preview]` not installed → skip visual critique gracefully. **No batchRender / no extra render step.**
- [x] 3.3 `pipeline/run.py` refine test-phase: render sampled frames → `visual_critic` → merge findings into the QA report / Judge input; escalation to human now also fires on visual findings (reuse existing checkpoint gate)
- [x] 3.4 Injectable (`visual_critic=`, `render_frames=`) so the loop stays hermetic; visual critique only runs when `refine=True` and render data is present

## 4. Tests & verification

- [x] 4.1 `fseq`: synthetic FSEQ v2 fixture (header + one zstd block) → `load_fseq` returns expected `[frames, channels]`
- [x] 4.2 `layout`: synthetic Vert-Matrix / Arch / Boxed models → `model_world_pixels` expected pixel counts + bounded extents; `resolve_start_channel("!Ctrl:N")` correct
- [x] 4.3 `render`: synthetic models + a channel frame → `render_frame` returns a non-empty PNG with lit pixels at expected locations; `render_clip` returns a non-empty MP4 (skipped/graceful if `ffmpeg` absent)
- [x] 4.4 `visual_critic`: PydanticAI TestModel stubs `VisualFindings` (no real vision call); `render_input` produces `BinaryContent` images
- [x] 4.5 Loop: stub visual critic finding → loop consults + escalates AND a review bundle (frames + findings.json + review.md) is written; none → no vision-driven escalation; **visual findings do NOT change `objective_score`/`_obj`** (advisory-only assertion); `.fseq`/`[preview]` absent → skipped (graceful); `refine=False` unchanged
- [x] 4.6 `parse_models` placed-vs-skipped count is reported (synthetic model with an unresolvable start channel → counted, not silently dropped)
- [x] 4.7 Live (gated): after an orchestrator render+save, **resolve `LLM_ORCH_SHOW.fseq` from the sandbox container** → render real **stills + clips** (PROVEN this session on our own show) + `gemini-3.1-pro-preview` critique of **image AND video** returns spatial + motion findings + a review bundle (stills/clips/findings/review.md) is written
