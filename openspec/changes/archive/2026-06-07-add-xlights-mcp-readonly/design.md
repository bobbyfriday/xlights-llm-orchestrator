## Context

Greenfield project, empty repo. The full system (parallel LLM agents that generate xLights sequences) is captured in `PLAN.html`. This change builds only the foundation: a read-only path to xLights, exposed as a library and as MCP tools.

The transport facts are fixed by xLights (verified against `src-ui-wx/automation/xLightsAutomations.cpp`): the automation API serves each command as `GET /<cmd>?param=val` or `POST /<cmd>` with a JSON body, on `http://127.0.0.1:49913` (instance "A"; `49914` = "B"). Responses are JSON carrying a `res`/status code. Status semantics observed in the source:
- `200` — success.
- `503` — **operational error** (generic): used for "Unknown model.", "No sequence open.", bad params, etc. The *message* disambiguates; the status alone does not.
- `504` — **not implemented** (e.g. `prepareAudio`).

Read-command scoping (also verified in source): `getVersion`, `getShowFolder`, `getModels`, `getModel`, `getControllers` read **show-level** state (`AllModels`, `OutputManager`, `showDirectory`) and succeed with no sequence open. `getViews` is **sequence-scoped** (`CurrentSeqXmlFile == nullptr → 503 "No sequence open."`) and is therefore excluded from this change.

This change deliberately establishes the transport + error taxonomy that the next change (`add-xlights-mcp-effect-editing`) will extend with the write path and the write-lock.

## Goals / Non-Goals

**Goals:**
- A reusable async client in `xlights-core` for read commands, with a clean typed error taxonomy.
- A `xlights-mcp` FastMCP server exposing those reads.
- A uv workspace that the later packages (`xlights-orchestrator`) slot into without restructuring.
- Behavior verifiable by recorded-response unit tests plus a live smoke test.

**Non-Goals:**
- Any mutation, the write-lock, presets, audio, orchestration (later changes).
- Multi-instance (A/B) modeling — a single configurable base URL only.
- Caching/retry sophistication beyond a basic timeout.

## Decisions

### Async `httpx` client
Use `httpx.AsyncClient`. The orchestrator (later) is async and concurrent; establishing async now avoids a sync→async rewrite. MCP tool handlers `await` the client directly. **Alternative:** sync `requests` — rejected because it would force a rewrite when the orchestrator arrives.

### Transport shape: GET path = command, params as query; POST for JSON bodies
A single internal `_request(cmd, params, method)` helper maps a command name to a path and issues the call. Reads are GET with query params. The helper centralizes response decoding and error mapping so every command method stays a thin typed wrapper. **Alternative:** one bespoke method per command with inline HTTP — rejected as repetitive and inconsistent for error handling.

### Error taxonomy as an exception hierarchy
A base `XLightsError` with subclasses: `XLightsConnectionError`, `XLightsTimeout`, `XLightsNotImplemented` (the `504` case), and `XLightsResponseError` (carries status + message; covers all `503` operational errors). Callers — including MCP tools — can branch on type. The spec's "typed conditions" requirement maps directly onto this hierarchy.
**Note on not-found:** `getModel` of a missing name is a `503 "Unknown model."` — i.e. an `XLightsResponseError`, **not** a dedicated not-found type. We deliberately do **not** parse the message string to synthesize a not-found exception (messages are unstable). Callers that need to distinguish not-found inspect `status`/`message` on the response error. **Alternative:** error codes in a result object — rejected; exceptions compose better with async and keep happy-path signatures clean.

### Typed layout models via pydantic
**Grounded in source — the response shapes are not uniform:**
- `getModels` returns a flat JSON array of **name strings only** (`{"models":["Arches","Matrix",…]}`), mixing models and groups. Query params split them: `?groups=false` → models only, `?models=false` → groups only. So `get_models()` returns `list[str]`; to distinguish kinds we make the two filtered calls.
- `getModel` returns one model's full attributes (`GetAttributesAsJSON()`) → parsed into a lenient pydantic `Model`.
- `getControllers` returns an array of rich objects → parsed into a lenient pydantic `Controller`.

So the only rich pydantic types are `Model` and `Controller` (both tolerant of unknown/extra fields — xLights' JSON is broad and version-dependent). There is **no** `Group` body type (groups surface as names from `getModels`; `getModel` on a group name returns its attributes if needed). **Alternative:** force a uniform typed layout — rejected; it would misrepresent the API. **Alternative:** raw dicts everywhere — rejected for `getModel`/`getControllers`; typed models give the MCP layer and tests a stable contract.

### Response envelope (verified in source)
With `Accept: application/json`, the server wraps results as `{"<key>": <value>}` where `<value>` is a quoted string for text results (`version`, `folder`) or raw JSON for structured results (`models`, `model`, `controllers`). Errors carry the HTTP status (`503` operational, `504` not-implemented) with body `{"msg":"…"}`. The client keys error handling off the **HTTP status code**, and extracts `msg` for the message.

### MCP via FastMCP, one tool per read
`xlights-mcp` instantiates a FastMCP server; each tool is a thin wrapper that calls the shared client and returns structured data, translating client exceptions into clear tool errors. A single shared client instance is created at server startup from `XLIGHTS_BASE_URL` (construction does not open a connection — `httpx.AsyncClient` connects lazily per request, so the server starts even when xLights is down). The client is closed (`aclose`) on server shutdown.

### uv workspace, two packages now
Root `pyproject.toml` declares a uv workspace; `packages/xlights-core` and `packages/xlights-mcp` are members (`xlights-mcp` depends on `xlights-core`). `xlights-orchestrator` is added by a later change without restructuring. Layout follows `PLAN.html`.

## Risks / Trade-offs

- **xLights JSON shape differs from research** → lenient pydantic parsing (ignore unknown fields) + recorded-response tests captured from a real instance; the live smoke test catches drift early.
- **xLights not running during dev/tests** → unit tests use recorded/mocked responses (no live dependency); the live smoke test is separate and opt-in.
- **`504` ambiguity** (could be a gateway timeout in other stacks) → here it specifically means "not implemented" per the xLights source; documented and mapped to `XLightsNotImplemented`.
- **Establishing async early adds a little ceremony for a read-only tool** → accepted; it is strictly cheaper than migrating later.

## Open Questions

- **Exact field sets** returned by `getModels`/`getModel`/`getControllers` — unknown until observed. Implementation is **capture-first**: probe a live instance and pin recorded fixtures *before* finalizing the pydantic models and error mapping (reflected in tasks.md ordering). Parse leniently so unexpected fields don't break reads.
- **Should `mcp-server` be its own capability?** Server-level concerns (stdio transport, lifecycle, config, exception→tool-error translation) currently live only in this change's design and will be re-used by future tool groups (write tools, audio tools). Option A: keep capability-vertical (server concerns stay in design across changes). Option B: introduce a thin `mcp-server` capability spec that owns the shared server contract. **Deferred decision** — revisit when `add-xlights-mcp-effect-editing` adds the second tool group; do not bake in now.
