> **Build result (verified live):** client.get_open_sequence/export_video_preview; RealRender in pipeline/visual.py (media GUARD — never exports media-less [the crash precondition], .xsq-mtime export cache, ffprobe lead-in offset, ffmpeg frame/clip extraction, all best-effort); make_lit_sampler prefers real frames (offline fallback → neutral); make_visual_critique uses real stills/clips when refreshed (offline picks the brightest moment + remains fallback); the refine loop exports once per evaluation after the save. 218 tests. LIVE: export via automation in ~17s, lead-in 7447ms auto-measured, real-frame coverage operational and AGREES with the offline approximation on the current fixed show (100/100 both).

## 1. Client + RealRender
- [x] 1.1 client.py: `get_open_sequence()`, `export_video_preview(filename)` (write-path)
- [x] 1.2 `RealRender(save_as, duration_s)` in visual.py: `refresh(client)` (media guard → export → ffprobe offset; cached by .xsq mtime), `frame_png(t_ms)`, `clip_mp4(s,e)` via ffmpeg, all best-effort
## 2. Consumers
- [x] 2.1 `make_lit_sampler(..., real=None)`: real frame first, offline fallback, raise → neutral
- [x] 2.2 `make_visual_critique(..., real=None)`: stills/clips from real when refreshed; offline picks brightest + remains fallback
- [x] 2.3 run.py: one shared RealRender; `_refine_loop(real_render=)` refreshes after each save
## 3. Tests & verification
- [x] 3.1 refresh guard: media empty → no export; media set + file appears → True with offset = video−song; failure → False
- [x] 3.2 frame_png lit-counting on a generated test clip (white → lit, black → 0); sampler prefers real
- [x] 3.3 Live: refresh against the open sequence → export lands; coverage over REAL frames recomputed; critic bundle contains real stills
