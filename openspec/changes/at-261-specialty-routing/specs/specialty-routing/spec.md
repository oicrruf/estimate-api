# Specialty routing

## ADDED Requirements

### Requirement: Evidence routing does not purchase items

The coordinator SHALL deduplicate Cameras, Networks, and Raceway assignments and SHALL return no material or purchase lines.

#### Scenario: Unknown PoE switch

- **WHEN** PoE cameras use an existing switch with unconfirmed model, power, or ports
- **THEN** the coordinator asks for those facts without proposing a switch

#### Scenario: Analog coax with adequate uplink

- **WHEN** an analog coax DVR has a confirmed adequate existing uplink
- **THEN** the coordinator does not assign PoE camera Ethernet work

#### Scenario: Raceway evidence edit

- **WHEN** a route outer diameter or linked camera count changes
- **THEN** only the affected route or link evidence is marked stale
