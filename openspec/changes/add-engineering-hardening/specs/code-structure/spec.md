## ADDED Requirements

### Requirement: Refine-loop guards are named, individually-testable units
The refine loop's control-flow guards SHALL each exist as a named function or small class that can be unit-tested in isolation, rather than being reachable only through the whole loop body. The extraction SHALL be behavior-preserving: the golden pipeline snapshot SHALL remain byte-identical (no regeneration), and the full hermetic refine suite SHALL stay green. The loop and its guards SHALL live in a dedicated module while `run.py` retains `run_pipeline` as the stage skeleton and re-exports the moved names so every existing import keeps resolving.

#### Scenario: Each guard is tested in isolation
- **WHEN** the refine-guard test suite runs
- **THEN** the skip-high-objective gate, objective-regression revert, plateau detector, design-escalation implication, best-tracker, escalation ledger, report builder, iteration recorder, and revision application are each exercised directly, without driving the whole loop

#### Scenario: Decomposition changes no behavior
- **WHEN** the pipeline runs after the loop is extracted
- **THEN** the golden pipeline snapshot is byte-identical with no `XLO_REGEN_GOLDEN`, and the refine suite passes unchanged

#### Scenario: Historical import paths still resolve
- **WHEN** existing code imports the refine-loop names from their original module path
- **THEN** the imports resolve via re-export aliases

### Requirement: Scattered tuning constants and per-effect metadata are single-sourced
The refine-loop thresholds and the parallel per-effect metadata tables SHALL each live in a single source of truth rather than being duplicated across modules with cross-module imports. Refine-control thresholds SHALL move into the tuning module under a labelled section that keeps each value's provenance comment, and the parallel per-effect tables SHALL be consolidated into one data-driven metadata table with derived views. All historical import paths SHALL continue to resolve via re-export aliases so no caller breaks.

#### Scenario: Refine thresholds have one home
- **WHEN** a refine-control threshold (e.g. the regression margin, stall limit, or skip-objective cutoff) is read
- **THEN** its definition lives in the tuning module's refine-control section with its provenance comment, and any prior location re-exports it

#### Scenario: Per-effect metadata has one home
- **WHEN** effect speed keys, direction knobs, energy bands, duration classes, and motion/bed/bounce/chase sets are read
- **THEN** they derive from one consolidated metadata table, the former cross-module imports are gone, and the old names still resolve via aliases
