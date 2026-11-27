# Specialty handoff

## ADDED Requirements

### Requirement: Local typed handoff preserves unknown evidence

The handoff SHALL use an AT-246 scope draft and AT-261 routing result. It SHALL reject confirmed facts without matching local project, field, typed value, and revision bindings and SHALL not create proposal lines. Source authentication remains the caller's responsibility.

#### Scenario: Untrusted model claim

- **WHEN** a confirmed camera fact cites an unadmitted evidence ID
- **THEN** the handoff rejects the input

#### Scenario: Wi-Fi capacity unknown

- **WHEN** a Wi-Fi camera count is confirmed but existing capacity is not
- **THEN** the handoff asks for wireless capacity evidence and does not assign PoE link work
