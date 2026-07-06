## ADDED Requirements

### Requirement: A shared transient-only retry primitive with bounded backoff
The system SHALL provide one shared async retry primitive that re-runs a callable on a caller-supplied "retryable" predicate using bounded exponential backoff with full jitter, and no third-party dependency. The primitive SHALL cap attempts (default 3), grow the delay geometrically to a ceiling (defaults base 1.0s, factor 2.0, max 20.0s), and apply a ±50% jitter band so concurrently-launched callers do not re-collide on the same rate-limit window. A non-retryable exception, and the final failure after the last attempt, SHALL propagate unchanged so every existing `except`/`isinstance` path still works; each retry SHALL log a warning naming the label, attempt count, and cause. The primitive SHALL live in the lowest package so both transport and LLM seams can reuse it, and SHALL be disable-able (attempts 0/1) for tests.

#### Scenario: A transient failure is retried then succeeds
- **WHEN** a wrapped call raises a retryable exception and a subsequent attempt would succeed
- **THEN** the primitive backs off with jittered exponential delay and returns the successful result within the attempt cap

#### Scenario: A non-retryable failure propagates immediately
- **WHEN** a wrapped call raises an exception the predicate does not classify as transient
- **THEN** the primitive re-raises it unchanged without any retry

#### Scenario: The terminal failure keeps its type
- **WHEN** every attempt raises the retryable exception
- **THEN** the original exception (type and content) propagates after the last attempt, and each retry was logged at warning

### Requirement: Transient classification is explicit and unit-tested
The system SHALL decide retryability by explicit, unit-tested predicates rather than a blanket "5xx means retry" rule, because xLights overloads 5xx for non-transient semantic states and LLM schema/auth failures repeat identically at full token cost. The xLights transport predicate SHALL retry only connection failures and timeouts, and SHALL NOT retry not-implemented, target-missing, unsaved-changes, or generic response errors. The LLM predicate SHALL retry provider overload/rate-limit/timeout classes (HTTP 408/429/500/502/503/529 and escaping transport/timeout errors) and SHALL NOT retry validation, auth, bad-request, content-filter, or usage-limit errors. Each predicate SHALL be isolated in one function next to its taxonomy so a provider library rename fails a unit test rather than a run.

#### Scenario: xLights semantic 5xx is not retried
- **WHEN** an xLights request returns a semantic 503/504 (busy, unknown model, not implemented, unsaved changes)
- **THEN** the transport predicate classifies it as non-transient and it is not retried

#### Scenario: An LLM rate-limit is retried but a schema failure is not
- **WHEN** an LLM call raises a 429/529 or an escaping timeout
- **THEN** the LLM predicate classifies it transient and it is retried
- **AND** a validation/auth/bad-request error is classified non-transient and re-raised immediately

### Requirement: Retry is applied at the LLM, transport, and panel-analyst seams
The system SHALL apply the retry primitive at exactly three seams with per-site attempt budgets, leaving all other call sites untouched. LLM calls SHALL route through one wrapper with run-fatal roles (director, synthesizer, generator, judge) getting 3 attempts and best-effort roles (panel analysts, visual critic, section redesigner) getting 2. The xLights transport boundary SHALL retry reads on connection error and timeout, and SHALL retry mutations on connection error only while holding the write lock across the backoff to preserve ordering, excluding the long-running render and video-export commands. A panel analyst SHALL retry once before being dropped, and the drop SHALL log at warning naming the analyst key.

#### Scenario: A mutation retries only when provably unsent
- **WHEN** an xLights mutation fails with a connection error (the request provably never reached xLights)
- **THEN** it is retried inside the write lock, whereas a post-send timeout surfaces immediately without retry to avoid double-application

#### Scenario: Render and export are excluded
- **WHEN** a long-running render-all or video-export call times out
- **THEN** it is not retried (a timeout means "still rendering", and re-issuing would pile work on the app)

#### Scenario: A dropped analyst is named
- **WHEN** a panel analyst fails its retry and is dropped from the brief
- **THEN** the drop is logged at warning naming the analyst key, and panel concurrency never exceeds its semaphore
