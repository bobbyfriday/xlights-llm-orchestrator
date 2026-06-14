## Context

`creative_brief.json` carries a `$schema` ref to a generated `creative_brief.schema.json` whose constrained fields have `enum`s (groups, effect types, scenes, stems, colors). That schema is everything a form needs. This is "option 2" from the editing discussion — the nicest UX (real color/dropdown widgets), built on the same schema as the VS Code path.

## Goals / Non-Goals

**Goals:** point-and-click editing of the per-section creative direction with real widgets; no data loss (preserve unrendered fields); no new dependencies. **Non-Goals:** a hosted/multi-user app; auth; editing the song analysis; a full visual show preview (that's the render).

## Decisions

**D1 — Consume the JSON files, don't import the generator.** The editor reads `creative_brief.json` + the sibling schema file and writes the brief back. It does NOT import `brief_schema`, so it's independent of that change and works wherever the files exist (and can branch off main). A missing schema → text-only form (graceful).

**D2 — Stdlib only.** `http.server.ThreadingHTTPServer` + a single embedded HTML/JS page. No Flask/FastAPI, no React/CDN — keeps the tool dependency-free and offline. The page embeds the brief/schema/colors as JS literals (one GET), and Save is one POST.

**D3 — Schema-driven widget mapping.** Per SectionPlan property: `enum` → `<select>`; `array`+`items.enum` → multi-select chips; `palette` → color rows (name `<select>` + a swatch coloured from a name→hex map sent by the server); `number` (intensity) → range slider; else → text/`<textarea>` (long fields get a textarea). New schema fields render automatically.

**D4 — Read-modify-write, never reconstruct.** The page holds the FULL brief object and only mutates rendered fields; Save sends the whole object, so unrendered fields (group_motifs, key_moments, show palette) and `$schema` survive verbatim. The server re-validates as `ShowPlan` (minus `$schema`) before writing, and writes atomically (tmp+replace).

**D5 — Color swatches from a server-supplied name→hex map.** The schema's palette enum is color NAMES; the server embeds `{name: hex}` (from `NAMED_COLORS`) so the form can show swatches. Names (not raw hex) keep the brief in its existing vocabulary; a true hex picker can be added later.

## Risks / Trade-offs

- [An edit makes the brief invalid] → the server validates as `ShowPlan` and rejects with the error surfaced in the form; nothing is written.
- [Form doesn't render every field] → intentional (start/end times read-only; complex nested fields preserved as-is, editable in VS Code if needed).
- [Concurrent edits / stale page] → single-user local tool; last Save wins. Acceptable.

## Migration Plan

Additive. Branch `change/add-brief-editor`, PR (user merges). `xlo edit-brief --song <mp3>` after a run.

## Open Questions

- A true hex color picker (`<input type=color>`) alongside the name dropdown — easy to add if the user wants custom colors beyond the 54-name vocab.
- A "Save & re-render" button that kicks off `xlo run` after saving — deferred (keep editing and running separate for now).
