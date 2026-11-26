# private-demo-package Specification

## Purpose

Define how to verify the exact synthetic AT-278/AT-279 private package on an isolated CI runner, including its source identity, loopback boundary, same-origin evidence responses, and persistent read-only store behavior.

## Requirements

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
