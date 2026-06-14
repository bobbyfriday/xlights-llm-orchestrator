## 1. Editor

- [x] 1.1 `brief_editor.py`: stdlib `ThreadingHTTPServer`; GET `/` → schema-driven HTML form (embeds brief/schema/color-map); POST `/save` → validate as ShowPlan, preserve `$schema` + unrendered fields, atomic write.
- [x] 1.2 Schema-driven widgets: enum→select, array-enum→multi-chip, palette→color rows w/ swatches, intensity→slider, text/textarea otherwise.

## 2. CLI

- [x] 2.1 `xlo edit-brief --song <mp3> | --brief <path> [--no-open]` → resolve the brief, `serve()` it.

## 3. Tests (hermetic)

- [x] 3.1 `save_brief` preserves `$schema` + unrendered fields, injects `$schema` if missing, rejects invalid (nothing written).
- [x] 3.2 `render_page` embeds brief/schema/colors and replaces all placeholders.
- [x] 3.3 Live smoke (done): GET `/` serves the form with dropdowns + swatches; POST `/save` writes the edit, preserves `$schema` + section count.
- [x] 3.4 Full suite passes.

## 4. Land

- [x] 4.1 Archive, commit, push, open PR (user merges).
