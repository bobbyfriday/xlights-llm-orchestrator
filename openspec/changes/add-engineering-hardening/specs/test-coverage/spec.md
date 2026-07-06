## ADDED Requirements

### Requirement: The human/shell/HTTP/LLM edges are covered hermetically
The test suite SHALL cover the surfaces where a human, a shell, an HTTP client, or an LLM provider touches the system, none of which are exercised today: the `cli.py` argument wiring, the `models/registry.py` routing point, the `brief_editor.py` HTTP layer, and the entire `xlights-mcp` server. Coverage SHALL be hermetic — no live xLights, no real LLM provider, and no network — so the tests run in CI.

#### Scenario: CLI wiring is exercised
- **WHEN** the CLI test suite runs
- **THEN** it exercises the `run`, `regen`, and `edit-brief` subcommands and their flags, the `--auto`/`--refine` checkpoint matrix, guard exits, and the exception→`SystemExit` mapping
- **AND** it does so without contacting xLights or an LLM provider

#### Scenario: The LLM routing point is exercised
- **WHEN** the registry test suite runs
- **THEN** it covers provider/model resolution, the `XLO_PROVIDER` override, and the no-sampling-params invariant that previously caused a silent Opus 400
- **AND** it uses no real provider

#### Scenario: The brief-editor HTTP surface is exercised
- **WHEN** the brief-editor HTTP test runs against a real loopback server
- **THEN** GET, POST, 404, and 400 paths are covered, and an invalid save leaves the on-disk file untouched

#### Scenario: The MCP server goes from zero tests to covered
- **WHEN** the MCP server test suite runs
- **THEN** every exposed tool's happy-path or gate is exercised, the typed-error translation is covered, and the raw add-effect gate is enforced

### Requirement: A schema-drift guard freezes agent outputs and cached artifacts
The test suite SHALL freeze a known-good payload for each agent `output_type` and for each persisted cache artifact, and SHALL validate them in CI so that an additive or renaming schema change fails a test rather than surfacing mid-run or being silently discarded by the stale-cache-recompute branch. A required-fields manifest SHALL accompany the frozen payloads so that dropping or newly requiring a field is detected.

#### Scenario: A breaking schema change fails a test
- **WHEN** a pydantic field is renamed, dropped, or made newly required on an agent `output_type` or a cached artifact
- **THEN** the schema-drift test fails in CI
- **AND** the failure occurs before any run or cache load would have silently discarded work

#### Scenario: Frozen payloads validate
- **WHEN** the schema-drift suite runs on an unchanged schema
- **THEN** every frozen agent-output and cache-artifact payload validates against its current model
