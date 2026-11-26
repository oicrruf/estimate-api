## ADDED Requirements

### Requirement: Typed local intake preview

The local adapter SHALL preserve AT-246 scope questions and call AT-240 with
only explicit confirmed whole quantities. Missing or inferred quantities SHALL
remain pending. It SHALL return a review-required, unpersisted proposal.

#### Scenario: Eight PoE cameras and a distinct uplink

- **WHEN** a synthetic intake confirms eight PoE cameras and one uplink
- **THEN** the AT-240 proposal SHALL retain both separate requested needs and
  show the AT-267 total-port and PoE-port findings without marking commercial
  readiness

#### Scenario: Missing evidence

- **WHEN** a camera count is inferred or an uplink count is missing
- **THEN** no confirmed quantity SHALL be inferred and constraint checks SHALL
  remain pending

#### Scenario: Quantity change

- **WHEN** a new confirmed camera count follows a prior proposal
- **THEN** AT-240 SHALL report changed lines and the bridge SHALL reject reuse
  of the earlier constraint document, leaving checks pending

#### Scenario: Stale same-need constraint document

- **WHEN** an internal caller supplies a changed document with the same
  declared eight-camera and one-uplink counts
- **THEN** the local bridge SHALL reject it rather than treating its checks as
  verified evidence
