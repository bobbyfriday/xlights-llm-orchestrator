## ADDED Requirements

### Requirement: Connect to a configurable xLights endpoint
The system SHALL connect to a local xLights automation endpoint whose address is configurable, defaulting to a conventional local address when unset.

#### Scenario: Default endpoint
- **WHEN** no endpoint is configured
- **THEN** the system targets the conventional local xLights automation address

#### Scenario: Overridden endpoint
- **WHEN** an endpoint is provided via configuration (`XLIGHTS_BASE_URL`)
- **THEN** the system uses that endpoint for all read operations

### Requirement: Report show-level context
The system SHALL report whether a reachable xLights instance is present, its version, and the active show folder, so that layout reads can be interpreted against the show they came from.

#### Scenario: Instance reachable
- **WHEN** a caller requests the version and xLights is running and reachable
- **THEN** the system returns the reported version string

#### Scenario: Active show folder
- **WHEN** a caller requests the active show folder
- **THEN** the system returns the path of the show folder currently loaded in xLights

#### Scenario: Instance unreachable
- **WHEN** a caller requests show-level context and no xLights instance is reachable at the configured endpoint
- **THEN** the system reports a connection failure rather than returning data

### Requirement: Read the show layout
The system SHALL return the names of the current show's models and groups, SHALL be able to distinguish models from groups, and SHALL return the full details of a single named model on request. These reads SHALL succeed whether or not a sequence is open, because the layout is show-level state.

#### Scenario: List model and group names
- **WHEN** a caller requests the layout from a running xLights instance
- **THEN** the system returns the names of the models and groups defined in the current show

#### Scenario: Distinguish models from groups
- **WHEN** a caller requests the layout split by kind
- **THEN** the system reports which names are models and which are groups

#### Scenario: Empty layout
- **WHEN** the current show defines no models or groups
- **THEN** the system returns an empty layout, not a failure

#### Scenario: Get one model's details
- **WHEN** a caller requests a model by name that exists in the layout
- **THEN** the system returns that model's full attributes

#### Scenario: Get a non-existent model
- **WHEN** a caller requests a model name that does not exist in the layout
- **THEN** the system surfaces xLights' error response (carrying its status and message), distinct from a connection failure or timeout

### Requirement: Read controllers
The system SHALL return the controllers configured in the running xLights instance.

#### Scenario: List controllers
- **WHEN** a caller requests the controllers
- **THEN** the system returns the controllers defined in the show

### Requirement: Distinguish failure modes via typed conditions
The system SHALL surface read failures as distinct, typed conditions so callers can react differently to a connection failure, a timeout, an unimplemented command, and an operational error reported by xLights.

#### Scenario: Connection failure
- **WHEN** no xLights instance is listening at the configured endpoint
- **THEN** the system raises a connection-failure condition distinct from all other failure types

#### Scenario: Timeout
- **WHEN** a request does not complete within the allotted time
- **THEN** the system raises a timeout condition distinct from a connection failure

#### Scenario: Unimplemented command
- **WHEN** xLights reports that a command is not implemented (status `504`)
- **THEN** the system raises a distinct not-implemented condition rather than a generic error

#### Scenario: Operational error from xLights
- **WHEN** xLights returns an operational error status (e.g. `503`) for an otherwise well-formed request
- **THEN** the system raises an error-response condition carrying the status and message reported by xLights

### Requirement: Expose read access as MCP tools
The system SHALL expose its read operations to MCP clients as discrete tools, one per read operation, returning structured results.

#### Scenario: Tool discovery
- **WHEN** an MCP client lists available tools
- **THEN** the server advertises tools for reading version, show folder, models, a single model, and controllers

#### Scenario: Tool invocation
- **WHEN** an MCP client invokes the models tool against a running xLights instance
- **THEN** the server returns the structured layout, and on failure returns a clear, typed error to the client

### Requirement: Read-only scope
This capability SHALL provide only read operations; it SHALL NOT expose any operation that creates, edits, renders, saves, or deletes a sequence, effect, or configuration.

#### Scenario: No write operation is exposed
- **WHEN** the capability's available operations (and MCP tools) are enumerated
- **THEN** every one is a read of xLights state, and no mutating xLights command is reachable through this capability
