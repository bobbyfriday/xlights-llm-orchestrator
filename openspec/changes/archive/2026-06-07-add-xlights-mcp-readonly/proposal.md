## Why

This is the first slice of a greenfield system that will use parallel LLM agents to generate xLights light-show sequences. Before any generation logic, we need a proven, safe path from a client to a running xLights instance. Starting read-only gives us the thinnest end-to-end pipe (MCP client → xLights automation API → back), is safe to run against a live sequence, and retires the project's first risk: *does the xLights REST automation API behave as researched?*

## What Changes

- Establish a minimal **uv workspace** with two packages: `xlights-core` (shared library) and `xlights-mcp` (MCP server). The `xlights-orchestrator` package is intentionally deferred to a later change.
- Add a **read-only client** in `xlights-core` that connects to the xLights automation API and exposes the show-level read commands: `getVersion`, `getShowFolder`, `getModels`, `getModel`, `getControllers`, returning typed layout data. (All of these read show-level state and work whether or not a sequence is open — verified against the xLights source.)
- Define a **typed error taxonomy** so callers can distinguish connection failure, timeout, an unimplemented command (`504`), and an operational error reported by xLights (e.g. `503` for "unknown model").
- Add an **MCP server** (`xlights-mcp`) exposing those reads as tools: `xl_get_version`, `xl_get_show_folder`, `xl_get_models`, `xl_get_model`, `xl_get_controllers`.
- Make the endpoint configurable via `XLIGHTS_BASE_URL` (default `http://127.0.0.1:49913`).
- Add recorded-response unit tests for parsing/error mapping and a live smoke test against a running xLights.

**Non-goals (explicitly deferred):** any mutation (`addEffect`, `saveSequence`, `new`/`openSequence`); the write-lock; `getViews` and other **sequence-scoped reads** (they require an open sequence — `getViews` returns `503 "No sequence open."` otherwise — so they belong with sequence-lifecycle, not this show-level read change); effect presets; audio/lyrics analysis; orchestration/agents; and multi-instance (A/B `49913`/`49914`) modeling.

## Capabilities

### New Capabilities
- `xlights-read-access`: Connect to a local xLights automation endpoint and read its show-level state (version, active show folder, model/group layout, controllers), surfacing failure modes — including unimplemented commands — as distinct, typed conditions. Exposed both as a library and as MCP tools.

### Modified Capabilities
<!-- None — this is the first change in a greenfield project; no existing specs. -->

## Impact

- **New packages:** `packages/xlights-core` (read client, typed layout models, error taxonomy), `packages/xlights-mcp` (FastMCP server, read tools).
- **New dependencies:** `httpx`, `pydantic` (core); `mcp[cli]` (mcp); `uv` workspace tooling; `pytest` (dev).
- **Config/runtime:** requires a running xLights with the automation API enabled; endpoint set via `XLIGHTS_BASE_URL`.
- **External systems:** read-only HTTP calls to the local xLights automation API. No writes, so safe against a live sequence.
- **Downstream:** establishes the transport + error taxonomy that the next change (`add-xlights-mcp-effect-editing`) extends with the write path. Note the keystone change `add-effect-presets` has an external dependency — the path to the user's existing `.xsq` corpus — to be resolved before it is implemented.
