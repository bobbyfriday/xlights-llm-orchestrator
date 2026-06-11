> **Environment notes (this session):** `uv` was not installed, so workspace resolution
> and tests were verified with a `venv` + `pip` install instead (equivalent).
> **Live verification completed** against xLights `2026.01.1` on `127.0.0.1:49913`: real
> responses confirmed our shapes exactly (`getModels` → name arrays, 81 models / 88 groups;
> `getModel` → rich attrs; `getControllers` → rich objects; unknown model → `503
> {"msg":"Unknown model."}`). A real `getModel` capture is saved under
> `tests/fixtures/live/`; the synthetic unit fixtures are shape-accurate and retained.

## 1. Workspace scaffold

- [x] 1.1 Create root `pyproject.toml` declaring a uv workspace with members `packages/xlights-core` and `packages/xlights-mcp`
- [x] 1.2 Scaffold `packages/xlights-core` (pyproject: deps `httpx`, `pydantic`; `src/xlights_core/` package)
- [x] 1.3 Scaffold `packages/xlights-mcp` (pyproject: deps `xlights-core`, `mcp[cli]`; `src/xlights_mcp/` package)
- [x] 1.4 Add `.env.example` (`XLIGHTS_BASE_URL=http://127.0.0.1:49913`) and a README quickstart — including the precondition that xLights must be running with the automation/REST listener enabled
- [x] 1.5 Verify the workspace resolves and both packages import (done via `pip` venv; `uv sync` is the documented path once `uv` is available)

## 2. Probe & capture (do this BEFORE modeling — shapes are unknown)

- [x] 2.1 Capture the read-command response envelopes as fixtures under `tests/fixtures/` — derived from xLights source (`getModels` returns name strings only; envelope `{"<key>": <value>}`). ⚠ Replace with a live capture in 6.2.
- [x] 2.2 Capture the error shapes too: `getModel` unknown name → `503 {"msg":"Unknown model."}`; connection failure when xLights is stopped — recorded as fixtures/tests
- [x] 2.3 Note the actual field sets so models/error mapping are built from reality (recorded in `design.md` + `tests/fixtures/README.md`)

## 3. Core: config, errors, transport

- [x] 3.1 Add config loading for `XLIGHTS_BASE_URL` (default `http://127.0.0.1:49913`)
- [x] 3.2 Define the error taxonomy: `XLightsError` base + `XLightsConnectionError`, `XLightsTimeout`, `XLightsNotImplemented` (`504`), `XLightsResponseError` (carries status + message; covers `503` operational errors)
- [x] 3.3 Implement the async `httpx` client with an internal `_request(cmd, params, method)` helper: command→path mapping, lazy connection, JSON decode, status/`res` handling
- [x] 3.4 Map transport outcomes to the taxonomy (connect→`XLightsConnectionError`, timeout→`XLightsTimeout`, `504`→`XLightsNotImplemented`, other error status→`XLightsResponseError`); do NOT string-parse messages to synthesize a not-found type

## 4. Core: typed layout models + read commands (built from §2 fixtures)

- [x] 4.1 Define pydantic models `Model` (from `getModel`) and `Controller` (from `getControllers`), lenient (tolerate/keep unknown fields). Note: `getModels` returns names only, so no `Group` body type.
- [x] 4.2 Implement `get_version()` and `get_show_folder()`
- [x] 4.3 Implement `get_models(*, include_models=True, include_groups=True) -> list[str]` (names; empty layout returns `[]`, not an error) and a split helper exposing models-only / groups-only via the query params; and `get_model(name) -> Model` (unknown name surfaces as `XLightsResponseError`)
- [x] 4.4 Implement `get_controllers()`

## 5. MCP server: read tools

- [x] 5.1 Create the FastMCP server in `xlights-mcp`, constructing one shared client from `XLIGHTS_BASE_URL` at startup and closing it (`aclose`) on shutdown (via lifespan)
- [x] 5.2 Add tools `xl_get_version`, `xl_get_show_folder`, `xl_get_models`, `xl_get_model`, `xl_get_controllers` as thin wrappers returning structured data
- [x] 5.3 Translate client exceptions into clear, typed tool errors for the MCP client
- [x] 5.4 Add a `xlights-mcp` console entry point so the server is runnable

## 6. Tests & verification

- [x] 6.1 Unit tests (no live dependency): parse each §2 fixture into the typed models; assert each error path maps to the correct taxonomy type — 11 passing
- [x] 6.2 Live smoke test (opt-in): against running xLights `2026.01.1`, `get_version` + `get_show_folder` + `get_models` returned real data — `pytest -m live` → 1 passed
- [x] 6.3 MCP integration check: in-memory MCP client session drove the server against live xLights — listed all 5 tools; `xl_get_version`→`2026.01.1`; `xl_get_models`→81 models/88 groups; `xl_get_model("Tree")`→ok; unknown model → clean `isError` with typed `XLightsResponseError`
