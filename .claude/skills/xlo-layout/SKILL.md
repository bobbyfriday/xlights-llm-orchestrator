---
name: xlo-layout
description: The xLights layout as the brief sees it — the SEM_ semantic group vocabulary (roles, bands, sides, ensembles, ordered _LTR sweeps), the layout manifest (layout_semantics.json) and what it says about scale, geometry and symmetry, and how to classify an unresolved prop into a canonical role and write it to the show folder's layout_overrides.json. Load for /xlo:init-layout, when choosing target_groups or pulse_groups in a brief, or when applied.json reports a target-missing skip.
---

# xlo-layout

Source of truth: `xlights-layout-semantics-spec.md` at the repo root. Code that implements it:
`packages/xlights-core/src/xlights_core/knowledge/layout_classify.py` (parse + classify),
`layout_semantics.py` (SEM_ group plan, render order), `layout_manifest.py` (the manifest), and
the orchestrator conductor `packages/xlights-orchestrator/src/xlights_orchestrator/pipeline/init_layout.py`.

| Decision | Read |
|---|---|
| The 18 canonical roles and their capability classes | spec §2 |
| How a prop gets its role (DisplayAs → node count → name heuristics → user-group hints) | spec §3 |
| Bands, sides, sweep order, mirror pairs, focal flags | spec §4 |
| Every SEM_ group and what it contains | spec §5 |
| The manifest schema | spec §6 |

## The SEM_ vocabulary (what a brief may target)

The targetable list for a song is `vocab.json` `groups` (written by `xlo groups`). It holds every
group xLights accepted — the SEM_ groups below plus the user's own groups (e.g. `Matrixes`,
`Small Tree Stars`) — minus any group that resolves to no model (a layout keeps last season's
`Arches` or `Candy Canes` as empty groups; xLights still accepts effects on them, which light
nothing). Prefer SEM_ names: the deterministic layers reason in them.

| Group | Contains | Use it for |
|---|---|---|
| `SEM_ALL` | every prop except singing faces and signs | whole-display beds, washes, flashes, the peak |
| `SEM_ALL_LESS_FOCAL` | all minus the hero | a bed that leaves the hero clean (cookbook G0-ALL-LESS-HERO) |
| `SEM_ALL_LESS_FOCAL_RHYTHM` | all minus hero, arches, minis, canes | a bed under a feature and a rhythm voice |
| `SEM_FOCAL` | the mega tree; with no tree, the matrixes — or the one matrix that dwarfs the rest (≥4× the next); any other prop > ~15% of the display | the hero (melody, drops, showpieces) |
| `SEM_CANVAS` | every matrix that is not the hero (all of them when they all are) | the screens: canvas looks, text, media; a calmer echo of the hero |
| `SEM_HOUSE` | outline + windows + icicles | the frame bed |
| `SEM_OUTLINE`, `SEM_WINDOWS`, `SEM_ICICLES`, `SEM_PATH` | one role each | frame segments, outline chases, icicle drips |
| `SEM_ARCHES`, `SEM_CANES`, `SEM_MINITREES`, `SEM_STAKES` | rhythm families (stakes = tombstones, peace stakes, any yard row) | the beat (the metric ring walks these) |
| `SEM_*_LTR` | the same, in left-to-right order | sweeps that must traverse in order |
| `SEM_SNOWFLAKES`, `SEM_SPINNERS` | sparkle / accent props | hits, sparkle, featured "snow" moments — dark otherwise |
| `SEM_CHARACTERS` | figures with eye submodels (cats, ghosts, gingerbread men) | accents and featured moments — eyes/mouth/tail submodels for a wink, a look, a hit |
| `SEM_ACCENTS` | every non-focal, non-outline, non-matrix prop (arches, minis, canes, stakes, flakes, spinners, characters) | a broad "everything but the house and hero" statement |
| `SEM_FLOODS` | floods / washes | atmosphere, lightning |
| `SEM_BAND_ROOF` / `_MID` / `_GROUND` | vertical bands | zone beds (`SEM_BAND_GROUND` is the default bed under features) |
| `SEM_SIDE_LEFT` / `_CENTER` / `_RIGHT` | horizontal thirds | call-and-response, spatial chases, the backbeat |
| `SEM_YARD` | ground band minus floods | yard-wide statements |

Roles that code relies on: hero = `SEM_FOCAL`; bed = `SEM_BAND_GROUND` then `SEM_ALL`; rhythm
ring = arches → canes → minis → snowflakes, ranked with stakes by the manifest; sparkle = snowflakes +
spinners + characters; whole-house hits =
`SEM_ALL` / `SEM_HOUSE` (`pipeline/semantic_groups.py`). A layout missing a family simply
disables that sublayer.

## Reading the manifest (scale, geometry, symmetry)

`layout_semantics.json` lives in the show folder (and a copy under the cache root's `layout/`).
Plan to it:

- `display`: `width_units`, `focal_x` (0–1, where the hero sits), `symmetric`. A symmetric display
  supports mirrored left/right conversations; an off-center focal suggests sweeps toward it.
- per `props[]`: `role`, `res` (`2D_SURFACE` | `2D_RADIAL` | `LINEAR_HIGH` | `LINEAR_LOW` | `POINT`
  | `SPECIAL`), `nodes`, `pos` {`x`, `y`, `band`, `side`}, `sweep_order`, `mirror_of`, `focal`,
  `confidence`.
- per `groups[]`: `members`, `ordered` (an `_LTR` group), `layout_mode`.

Derive, per group you intend to target: role (or "mixed"), member count, total nodes, band, and
whether it is ordered or symmetric. Scale matters: a 50-node arch set cannot carry texture; a
1600-node tree can carry a 3-layer stack; a matrix (`2D_SURFACE`) is the only place for text or
media. Radial effects want `2D_RADIAL`; chases want `LINEAR_*`; floods (`POINT`) take color only.

## Classifying the unresolved tail (`/xlo:init-layout`)

1. Run `xlo init-layout --show-folder <dir> --dry-run` (exit 0 whether or not props need review;
   the layout file is untouched). The deterministic pass (spec §3 steps 1–4) resolves most props;
   every prop still needing review (the unresolved `CUSTOM_PROP` @ 0.5 tail, low-confidence
   guesses) is listed in `<show folder>/layout_review.json` under `props`, with
   what the classifier saw: `name`, `display_as`, `nodes`, `pos` [x, y], `groups` (the user's
   group names it belongs to), its current `role` + `confidence`, and `candidate_roles` (the enum
   below). A rare name-only entry has no parsed model behind it.
2. For each unresolved prop pick ONE role from the closed enum — `MEGA_TREE`, `MINI_TREE`, `ARCH`,
   `CANE`, `ICICLES`, `STAR`, `SPINNER`, `MATRIX`, `WINDOW`, `OUTLINE`, `FLOOD`, `SINGING_FACE`,
   `SIGN`, `PATH`, `SNOWFLAKE`, `STAKE`, `CHARACTER`, `CUSTOM_PROP`. Use the name and the user-group names as the
   strongest clues; use node count + DisplayAs for geometry (a big dense Custom grid is a `MATRIX`;
   a small point cluster is a `CUSTOM_PROP`; a Custom with face submodels is a `SINGING_FACE`; a figure with eye submodels is a `CHARACTER`;
   a repeated yard stake in a row is a `STAKE`).
   When unsure, keep `CUSTOM_PROP` — never invent a specific role you can't justify. Ask the
   user about anything ambiguous; they know their yard.
3. Write the decisions to `<show folder>/layout_overrides.json` (read by
   `init_layout._load_overrides`, applied by `layout_classify.apply_overrides`). The format is a
   map from the prop's exact model name to an object with `role`:

   ```json
   {
     "GE_Bethlehem_Star_v2": {"role": "STAR"},
     "Front Yard Mesh":      {"role": "MATRIX"},
     "Parked Old Arch":      {"role": "CUSTOM_PROP"}
   }
   ```

   An override is a human decision: confidence 1.0, out of the review queue. Roles outside the enum
   are ignored silently, so spell them exactly.
4. Re-run `xlo init-layout --show-folder <dir> --dry-run` and confirm "0 to review" (an empty
   `props` list) and read the membership diff. Then run without `--dry-run` with **xLights closed**
   (it rewrites `xlights_rgbeffects.xml` from memory on exit and would clobber the edit; it exits 1
   without writing while xLights answers its port). A backup is taken; only `SEM_` groups are
   regenerated — user groups are never touched. The write exits 1 if props were still unreviewed
   (they ship in the manifest's `review`), else 0. Restart xLights afterwards; the next
   `xlo groups` re-probes targetability.

Flags: `--invert-x` when the sweep test runs right-to-left (mirrored preview); `--yes` keeps every
suggestion unattended (they stay listed in the manifest's `review`).

## When `applied.json` reports a target-missing skip

The instruction named a group xLights rejected. Replace it in the brief with a name from
`vocab.json` `groups` (same role tier from the table above), re-validate, realize, apply.
