## ADDED Requirements

### Requirement: Transient transport failures self-heal with bounded retry
The system SHALL transparently retry transient transport failures against xLights within a bounded budget so a momentary hiccup does not fail a stage that the next request would satisfy. Reads SHALL retry on both connection failure and timeout; mutations SHALL retry on connection failure only and SHALL do so while holding the write lock across the backoff, so ordering and the single-open-sequence invariant are preserved. The long-running render and video-export commands SHALL be excluded from retry. The terminal failure after the attempt budget SHALL keep its original typed condition, and the retry budget SHALL be configurable to zero to disable it for tests.

#### Scenario: A momentary connection blip self-heals
- **WHEN** a read or mutation fails with a connection error and the next attempt would succeed
- **THEN** the client retries within its bounded budget and returns the result, without surfacing the failure

#### Scenario: A post-send timeout on a mutation is not retried
- **WHEN** a mutation times out after the request may already have been applied
- **THEN** the client surfaces the timeout immediately rather than risk double-applying the mutation

#### Scenario: Retry can be disabled
- **WHEN** the client is constructed with a zero retry budget
- **THEN** every request is attempted exactly once, reproducing the pre-retry behavior

## MODIFIED Requirements

### Requirement: Distinguish failure modes via typed conditions
The system SHALL surface read failures as distinct, typed conditions so callers can react differently to a connection failure, a timeout, an unimplemented command, and an operational error reported by xLights. The connection-failure condition SHALL further distinguish the provably-never-sent case from the sent-but-response-lost case (as a subtype that existing connection-failure handlers still catch), so that retry logic can require the provably-unsent case for non-idempotent mutations.

#### Scenario: Connection failure
- **WHEN** no xLights instance is listening at the configured endpoint
- **THEN** the system raises a connection-failure condition distinct from all other failure types

#### Scenario: Provably-unsent vs response-lost
- **WHEN** a transport error occurs before the request is sent versus after it was sent but its response was lost
- **THEN** the system distinguishes the two as a connection-failure subtype that existing connection-failure handlers still catch, so mutation retry can require the provably-unsent case

#### Scenario: Timeout
- **WHEN** a request does not complete within the allotted time
- **THEN** the system raises a timeout condition distinct from a connection failure

#### Scenario: Unimplemented command
- **WHEN** xLights reports that a command is not implemented (status `504`)
- **THEN** the system raises a distinct not-implemented condition rather than a generic error

#### Scenario: Operational error from xLights
- **WHEN** xLights returns an operational error status (e.g. `503`) for an otherwise well-formed request
- **THEN** the system raises an error-response condition carrying the status and message reported by xLights
