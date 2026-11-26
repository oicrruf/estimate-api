## ADDED Requirements

### Requirement: Fixed public Git source for Coolify candidate

The Coolify candidate SHALL build from the two approved public source commits, verify each fetched commit identity, and use no mutable application image tags or external runtime service.

#### Scenario: Source identity differs

- **WHEN** a remote source does not resolve to its recorded commit SHA
- **THEN** the build fails before installing dependencies or starting a container.

### Requirement: Proxy-only web exposure

The candidate SHALL publish no host ports, SHALL expose only web port 8080 to the Coolify proxy, and SHALL keep API and seed on a private internal network with a persistent synthetic store mounted read-only by API.

#### Scenario: CI starts the candidate

- **WHEN** the candidate is built and started in an isolated runner
- **THEN** the real evidence evaluations work through web, API and seed have no host ports, and the store survives seed and API restart without mutation.
