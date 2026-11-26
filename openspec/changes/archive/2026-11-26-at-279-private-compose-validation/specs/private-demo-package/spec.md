# Private demo package

## ADDED Requirements

### Requirement: Fixed synthetic package validation

The private demo package validation SHALL reconstruct API and app from exact public commit hashes and SHALL reject any byte drift from its recorded manifest and archive digest before building containers.

#### Scenario: Source or package drift

- **WHEN** a source file or package configuration differs from the recorded private snapshot
- **THEN** the validation fails before Docker build.

### Requirement: Local-only Compose proof

The validation SHALL prove that only the web service has a loopback host port; API and seed SHALL have no published ports; the API store SHALL be mounted read-only.

#### Scenario: Real same-origin evaluation

- **WHEN** the synthetic stack starts in an ephemeral runner
- **THEN** Angular loads from loopback and five evidence-backed evaluations are served through the web origin.

#### Scenario: Reopen without reseeding

- **WHEN** seed runs a second time and the API restarts
- **THEN** seed reports reuse, the store hash remains identical and the evidence evaluation still succeeds.
