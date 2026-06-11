## Why

The refine loop judges the show from *data* (sync/placement/variety metrics) and a text Judge — it never **looks at** the rendered result. That blind spot is real: our generated Baby Shark show *scored* fine on metrics but, rendered, is "85% black, lights clumped in the lower-right" — a coverage failure only a pair of eyes catches. This change gives the loop eyes: render the show to a still image **offline** and have a multimodal model critique it, so vision models evaluate the work **before** anything escalates to a human.

Crucially, this does **not** use xLights. Driving xLights' export/preview to get pixels crashes it every way we tried (H.264 bitrate-0 encoder crash; media-attach re-entrant-HTTP crash; no playback/seek/screenshot commands — see memory `xlights-automation-quirks`). Instead we render our own preview from the **compiled render data on disk** — the same approach proven in the sibling project `xlight-autosequencer`.

## What Changes

- An **offline preview renderer** (`xlights-core`, no LLM/xLights dependency): from the show's `.fseq` (compiled per-frame channel output) + `xlights_rgbeffects.xml` (model geometry) + `xlights_networks.xml` (controller channel ranges), produce a **still PNG of the show at any timestamp** — world positions → orthographic projection → pixel splat. Ported/adapted from the user's proven `xlight-autosequencer/src/video/` modules (fseq zstd reader; layout with the `Scale×2` boxed vs per-pixel matrix gotcha + Matrix/Arch/Custom/Cube/Star/Tree geometry; renderer → stills instead of video).
- A **`visual_critic` agent** (multimodal, planner/vision tier — the role already exists in the registry): per section it gets **a still (spatial) + a short rendered MP4 clip (dynamic)** + the ShowPlan/MusicBrief intent, and returns **scoped findings / `RevisionBrief`s** covering both coverage/color ("section 2 dark", "monotone") **and motion/energy** ("static then harsh strobe", "no build into the chorus", "chase doesn't match the beat"). Uses PydanticAI `BinaryContent` for **both image AND video** input (both proven this session), routed to `gemini-3.1-pro-preview` or Opus.
- **Wired into the refine loop, before the human checkpoint:** the visual critic runs in the test/decide phase alongside the deterministic QA and text Judge; its findings feed the verdict, and the loop **escalates to the human only when the critic/QA/Judge flag issues** — realizing "models evaluate, then escalate to a human for approval."
- **Sampling:** per MusicBrief section, render a **brightest still** (spatial coverage) **+ a short clip** (the section window, capped length, low-res/fps to bound size) from the show's `.fseq` — stills catch dark/monotone, clips catch static-vs-moving and build/energy. (Beat-timing is already covered objectively by the deterministic Sync QA.)

**Already landed this session** (no spec needed): Gemini upgraded to 3.x (`gemini-3.1-pro-preview` planners/critics, `gemini-3.5-flash` workers, `google:` prefix), and the `visual_critic` registry role.

**Non-goals (later):** pixel-perfect rendering of every exotic model type (good coverage from the ported layout; unknown types fall back to a strip — acceptable for critique); temporal/video critique (stills suffice); auto-applying the critic's suggestions; the checkpoint edit/redirect UX.

## Capabilities

### New Capabilities
- `visual-critique`: Render the show to a still image offline (from compiled render data + layout, no xLights) and critique it with a multimodal model into scoped findings, consulted by the refine loop before escalating to a human.

## Impact

- **`xlights-core`** gains `preview/` (`fseq.py`, `layout.py`, `render.py`); new deps `numpy`, `zstandard` (+ `pillow`; `scipy` optional for bloom) under a `[preview]` extra.
- **`xlights-orchestrator`** gains `agents/visual_critic.py` and a call in the refine test-phase; consumes `xlights-core[preview]`.
- **Consumes** the show's `.fseq` (written by the orchestrator's render/save) + `rgbeffects.xml`/`networks.xml` from the show folder. The critic never drives the crashy xLights export commands.
- **Builds on** `show-refinement` (the loop/checkpoint), `music-interpretation` (section timestamps), `show-orchestration` (the rendered sequence). Reuses proven code from the sibling `xlight-autosequencer` repo (credited).
