# xLights Layout Semantics and Grouping Specification

**Purpose:** This document instructs an agent on how to derive a semantic model of an xLights display from `xlights_rgbeffects.xml`, and how to create and name model groups inside xLights so that downstream sequencing tools (planners, compilers, effect libraries) can choreograph against roles and ensembles instead of raw model names.

**Audience:** An agent with read access to the xLights show directory and the ability to edit `xlights_rgbeffects.xml` or drive the xLights UI to create groups.

**Core principle:** Pixels are not choreography. The planner must never reason about node counts, world coordinates, or model names. It reasons about roles ("the arches"), ensembles ("everything on the roofline"), and ordered sequences ("arches left to right"). The grouping structure created in xLights is the contract that makes that possible.

---

## 1. Inputs

The single source of truth is `xlights_rgbeffects.xml` in the show directory. Relevant elements:

- `<models><model ...>` entries. Key attributes:
  - `name` (user-assigned, unreliable but high-signal)
  - `DisplayAs` (model type: `Arches`, `Tree 360`, `Tree Flat`, `Matrix`, `Star`, `Spinner`, `Icicles`, `Single Line`, `Poly Line`, `Custom`, `Candy Canes`, `Circle`, `Window Frame`, `Wreath`, `Sphere`, `Cube`, `DMX...` variants)
  - `parm1` / `parm2` / `parm3` (strings, nodes per string, strands; meaning varies by type)
  - `WorldPosX`, `WorldPosY`, `WorldPosZ`, `ScaleX/Y/Z`, `RotateX/Y/Z`
  - `StringType` (RGB nodes vs single color, relevant for capability)
  - `<subModel>` children (named pixel subsets, preserve these)
- `<modelGroups><modelGroup ...>` entries: `name`, `models` (comma-separated member list). These represent the user's existing mental organization. Read them as classification hints. Do not delete them.
- `<layoutGroups>` if present (separate previews, e.g. a second display).

Do not parse `.xsq` sequence files for this task. Layout semantics are sequence-independent.

---

## 2. Role taxonomy

Every model must be assigned exactly one role from this closed enum. Do not invent new roles; use `CUSTOM_PROP` as the catch-all.

| Role | Description | Typical model types |
|---|---|---|
| `OUTLINE` | House structural lines: rooflines, gutters, eaves, ridgelines, columns | Single Line, Poly Line, Custom |
| `WINDOW` | Window and door frames | Window Frame, Poly Line, Custom |
| `MEGA_TREE` | Large focal tree, typically 800+ nodes | Tree 360, Tree Flat |
| `MINI_TREE` | Small trees, usually in multiples | Tree 360/Flat with low node count, Cone |
| `MATRIX` | 2D pixel surface capable of images/text | Matrix, Custom grid |
| `ARCH` | Leaping arches, usually in ordered sets | Arches |
| `SPINNER` | Radial spinner props | Spinner, Custom |
| `STAR` | Stars, tree toppers | Star |
| `ICICLES` | Icicle drops along eaves | Icicles |
| `CANE` | Candy canes | Candy Canes |
| `SNOWFLAKE` | Snowflake props | Custom, Circle |
| `FLOOD` | Floods, wash lights, single-pixel or low-count color washes | Custom, Single Line with very low node count, DMX floods |
| `SINGING_FACE` | Singing faces / talking props | Custom with face submodels |
| `SIGN` | Tune-to signs, text props | Matrix, Custom |
| `PATH` | Driveway, walkway, fence lines along the ground | Single Line, Poly Line |
| `CUSTOM_PROP` | Anything unclassifiable | Custom |

### Capability tags (derived from role + geometry)

Assign each model a resolution class. This gates which effects are legal on it:

- `2D_SURFACE`: matrices, high-density custom grids. Supports pictures, text, video, shader-style effects.
- `2D_RADIAL`: mega trees, spinners, stars. Supports spirals, radial waves, pinwheels.
- `LINEAR_HIGH`: outlines and paths with 100+ nodes. Supports smooth chases, wipes, bars.
- `LINEAR_LOW`: arches, canes, icicle segments under ~100 nodes. Supports simple chases, fills, bounces.
- `POINT`: floods and single-color props. Color washes and intensity only.
- `SPECIAL`: singing faces. Excluded from general choreography; driven by dedicated face tracks only.

---

## 3. Classification procedure

Run these steps in order. Each step only classifies models not yet resolved by an earlier step.

**Step 1: DisplayAs direct mapping.** Native types map directly: `Arches → ARCH`, `Icicles → ICICLES`, `Candy Canes → CANE`, `Star → STAR`, `Spinner → SPINNER`, `Matrix → MATRIX`, `Window Frame → WINDOW`.

**Step 2: Pixel-count disambiguation for trees.** `Tree 360` / `Tree Flat` with >= 600 nodes → `MEGA_TREE`. Below that → `MINI_TREE`. If exactly one tree exists and it is the largest prop in the display, classify as `MEGA_TREE` regardless of count.

**Step 3: Name heuristics.** Case-insensitive substring matching on `name`, applied to remaining models (mostly Single Line, Poly Line, Custom):

- `roof`, `gutter`, `eave`, `ridge`, `outline`, `peak`, `fascia`, `column`, `garage` → `OUTLINE`
- `window`, `door` → `WINDOW`
- `flood`, `wash`, `up light`, `uplight` → `FLOOD`
- `face`, `sing`, `carol`, `mouth` → `SINGING_FACE`
- `sign`, `tune` → `SIGN`
- `drive`, `walk`, `path`, `fence`, `yard line` → `PATH`
- `flake` → `SNOWFLAKE`

**Step 4: Existing group hints.** If an unclassified model belongs to a user group whose name matches a heuristic (e.g. group "All Outline"), inherit that role.

**Step 5: LLM fallback.** For any model still unclassified, send a compact record to an LLM and request a role from the enum above, with a confidence score:

```json
{"name": "GE_Bethlehem_Star_v2", "DisplayAs": "Custom",
 "nodes": 322, "width_m": 1.2, "height_m": 1.4, "groups": ["Yard Props"]}
```

Models classified at low confidence go to a review list (see Section 7) rather than silently into `CUSTOM_PROP`.

---

## 4. Spatial derivation

After classification, compute spatial attributes from world positions:

1. **Normalize.** Compute the bounding box of all models. Express each model's position as `x` in `[0, 1]` left to right and `y` in `[0, 1]` ground to top, from the audience's viewpoint (the default xLights house preview orientation).
2. **Vertical bands.** Assign each model `GROUND`, `MID`, or `ROOF` by thresholding normalized `y` (suggested cuts at 0.33 and 0.66, adjusted if the outline models clearly define a roofline).
3. **Sweep order.** Within each role that has multiple instances (`ARCH`, `MINI_TREE`, `CANE`, `WINDOW`, `SNOWFLAKE`, `SPINNER`), sort by normalized `x` and assign `sweep_order` 1..N.
4. **Symmetry pairs.** Two models of the same role whose `x` positions are approximately mirrored around the display centerline (tolerance 0.05) and whose `y` positions match are a `mirror_pair`. Record both directions.
5. **Center distance.** For each model, compute normalized Euclidean distance from the display's focal center (the `MEGA_TREE` if present, otherwise the bounding-box center). This enables radial wave choreography.
6. **Focal flags.** Mark `MEGA_TREE`, `MATRIX`, and any prop occupying more than ~15% of the display's visual area as `focal: true`.

---

## 5. Grouping structure to create in xLights

This is the deliverable inside xLights itself. Create the following model groups. Use the exact naming convention so downstream tools can rely on it. Prefix everything with `SEM_` to keep generated groups visually separate from the user's own groups and trivially identifiable for regeneration.

### 5.1 Role groups (one per role present in the display)

```
SEM_OUTLINE        all OUTLINE models
SEM_WINDOWS        all WINDOW models
SEM_ARCHES         all ARCH models
SEM_MINITREES      all MINI_TREE models
SEM_CANES          all CANE models
SEM_ICICLES        all ICICLES models
SEM_FLOODS         all FLOOD models
SEM_SNOWFLAKES     all SNOWFLAKE models
SEM_SPINNERS       all SPINNER models
SEM_PATH           all PATH models
```

Single-instance roles (`MEGA_TREE`, `MATRIX`, `STAR`, `SIGN`) do not need a group; the planner addresses the model directly. If multiples exist, create the group.

### 5.2 Ordered groups (for sweeps)

For each multi-instance role, also create a left-to-right ordered group. In xLights, member order within a group determines effect traversal order, so add members in `sweep_order`:

```
SEM_ARCHES_LTR     arches in sweep order 1..N
SEM_MINITREES_LTR  mini trees in sweep order 1..N
SEM_CANES_LTR      canes in sweep order 1..N
```

Right-to-left variants are unnecessary; the compiler reverses direction via effect parameters.

### 5.3 Band groups (vertical structure)

```
SEM_BAND_ROOF      all models in ROOF band
SEM_BAND_MID       all models in MID band
SEM_BAND_GROUND    all models in GROUND band
```

### 5.4 Side groups (horizontal structure)

```
SEM_SIDE_LEFT      models with x < 0.45
SEM_SIDE_CENTER    models with 0.45 <= x <= 0.55
SEM_SIDE_RIGHT     models with x > 0.55
```

### 5.5 Ensemble groups (choreography vocabulary)

```
SEM_ALL            every model except SINGING_FACE and SIGN
SEM_FOCAL          all focal: true models (mega tree, matrix, large props)
SEM_ACCENTS        all non-focal, non-outline props (arches, minis, canes, flakes, spinners)
SEM_HOUSE          OUTLINE + WINDOW + ICICLES (the structure itself)
SEM_YARD           everything in GROUND band except FLOODS
```

### 5.6 What NOT to do

- Do not delete or rename the user's existing groups. They coexist.
- Do not put `SINGING_FACE` models into any `SEM_` group except where explicitly listed. Faces are driven independently.
- Do not nest `SEM_` groups inside each other unless xLights group-of-group rendering has been verified for the target version. Flat membership is safer and renders predictably.
- Do not flatten submodels. If `OUTLINE` models have submodels (Roof_Left, Peak, Garage_Line), additionally create `SEM_OUTLINE_SEGMENTS` containing the submodels in left-to-right order to enable section-by-section builds.

### 5.7 Default render order guidance

In each group's settings, prefer "Per Preview" or "Horizontal Per Model" layout depending on intent: ensemble groups that receive whole-display effects (`SEM_ALL`, `SEM_BAND_*`) should use Per Preview so effects map across the display spatially; ordered groups (`SEM_*_LTR`) should use Horizontal Per Model so chases traverse members in order. Record the chosen mode per group in the output manifest.

---

## 6. Output manifest

Alongside the groups created in xLights, emit `layout_semantics.json` to the show directory. This is the artifact the planner consumes. Schema:

```json
{
  "version": 1,
  "generated": "ISO-8601 timestamp",
  "display": {
    "width_m": 18.3,
    "traits": {
      "has_matrix": true, "has_megatree": true,
      "arch_count": 6, "symmetric": true, "focal_x": 0.5
    }
  },
  "props": [
    {
      "id": "MegaTree",
      "role": "MEGA_TREE",
      "res": "2D_RADIAL",
      "nodes": 1600,
      "pos": {"x": 0.50, "y": 0.20, "band": "GROUND", "center_dist": 0.0},
      "focal": true,
      "confidence": 1.0
    },
    {
      "id": "Arch_1",
      "role": "ARCH",
      "res": "LINEAR_LOW",
      "nodes": 50,
      "pos": {"x": 0.12, "y": 0.05, "band": "GROUND", "center_dist": 0.41},
      "sweep_order": 1,
      "mirror_of": "Arch_6",
      "confidence": 1.0
    }
  ],
  "groups": {
    "SEM_ARCHES_LTR": {"members": ["Arch_1", "Arch_2", "Arch_3", "Arch_4", "Arch_5", "Arch_6"],
                        "ordered": true, "layout_mode": "Horizontal Per Model"},
    "SEM_FOCAL": {"members": ["MegaTree", "Matrix_P10"], "ordered": false,
                   "layout_mode": "Per Preview"}
  },
  "review": []
}
```

Rules:

- `confidence` below 0.8 puts the prop id into the `review` array.
- The manifest must be regenerable idempotently: rerunning the agent deletes and recreates all `SEM_` groups and rewrites the manifest, touching nothing else.
- Keep the manifest under ~10 KB for typical displays. It is the only layout representation downstream LLM planners receive.

---

## 7. Validation procedure

Classification errors poison every downstream sequencing decision, so validate before declaring done:

1. **Role color test.** Generate a short test sequence assigning each role group a distinct solid color for 2 seconds in succession (OUTLINE white, ARCHES red, MINITREES green, etc.), render it against the house preview via xLights' headless render, and produce a video or frame captures.
2. **Inspection.** Review the frames, either by a human or a vision model, with the question: "does each colored region correspond to its labeled role?" Mega tree vs mini tree confusion and outline segments misclassified as PATH are the most common failures.
3. **Sweep test.** Run a single chase across each `_LTR` group and confirm traversal goes left to right from the audience view. If it runs backward, the world-coordinate x axis was inverted; flip the normalization and regenerate.
4. **Review list resolution.** Every prop in the `review` array must be resolved by a human decision or explicitly accepted as `CUSTOM_PROP` before the manifest is marked final.

---

## 8. Edge cases

- **Multiple previews / layout groups.** Process only the default preview unless instructed otherwise. Props assigned to other layout groups are excluded from `SEM_ALL`.
- **DMX models** (moving heads, projectors). Classify as `CUSTOM_PROP`, exclude from all `SEM_` groups. They need dedicated handling.
- **Whole-house mesh / pixel curtain.** A very large Custom model covering the house is a `MATRIX` functionally. Classify by node density and area, not by name.
- **Duplicate or stale models.** Models with zero channels or positioned far outside the main bounding box (> 2x display width) are likely parked or abandoned. Exclude them and list them in `review`.
- **Inverted or rotated previews.** If the user's preview is mirrored (some are, depending on how they photographed the house), all left/right semantics invert. The sweep test in Section 7 is the guard.
- **Single-color (non-RGB) strings.** Classify normally but tag `res: POINT` capability override, since color choreography does not apply.
