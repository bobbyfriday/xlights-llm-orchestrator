## ADDED Requirements

### Requirement: mypy passes as a hard CI gate
The CI pipeline SHALL fail any pull request whose `mypy` run reports one or more errors, checking every package source file against the CI dependency set with zero findings. The `Type check (mypy)` step SHALL NOT carry `continue-on-error`; the gate is "mypy exits 0". `[tool.mypy]` SHALL enable `warn_unused_ignores` and `warn_redundant_casts` so a stale `# type: ignore` is itself an error, and every inline `# type: ignore[code]` SHALL carry an error code and a same-line reason. The gate SHALL be measured against the canonical CI environment (`uv sync --extra preview` then `uv run --no-sync mypy`), not a dependency-light venv.

#### Scenario: A type error fails the PR
- **WHEN** a pull request introduces code that `mypy` reports as an error (e.g. `x: int = "a"`)
- **THEN** the CI `Type check (mypy)` step exits non-zero and the pull request fails
- **AND** the step has no `continue-on-error`, so the failure is not advisory

#### Scenario: Clean tree passes
- **WHEN** `uv run --no-sync mypy` runs in the CI environment on a tree with no findings
- **THEN** it exits 0 having checked every package source file
- **AND** the pull request's type-check gate passes

#### Scenario: A stale ignore is an error
- **WHEN** a `# type: ignore` remains on a line mypy no longer flags
- **THEN** `warn_unused_ignores` makes it an error and the gate fails until it is removed

### Requirement: Every package ships a PEP 561 py.typed marker
Each distributed package SHALL ship a `py.typed` marker so downstream consumers and cross-package checks see the package as typed. The marker SHALL be present in `xlights-core`, `xlights-orchestrator`, and `xlights-mcp`, and SHALL be included in each package's built wheel.

#### Scenario: Marker present in source
- **WHEN** the repository is inspected
- **THEN** `py.typed` exists under each of `src/xlights_core`, `src/xlights_orchestrator`, and `src/xlights_mcp`

#### Scenario: Marker present in the built wheel
- **WHEN** a package is built (`uv build --package <pkg>`)
- **THEN** the resulting wheel contains `py.typed`
- **AND** a downstream consumer resolves the package's inline types under PEP 561
