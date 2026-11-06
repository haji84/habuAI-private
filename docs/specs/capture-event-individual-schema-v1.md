# Capture event and individual schema v1

## Purpose

Represent simultaneous multi-snake captures without turning one place/time observation into multiple independent capture events.

## Two-layer model

### Capture event layer

One real-world capture occurrence at one observed time and location is one event.

Required fields:

- `event_id`: stable unique capture-event identifier.
- `observed_at`: original observed timestamp.
- `operational_night`: Asia/Tokyo night key using the repository 07:00 boundary.
- `latitude`, `longitude`: original observed coordinates.
- `event_count`: number of individual habu captured in this event.

Event-level context such as road/place, weather, surface condition, and source reference belongs here when available.

### Individual layer

Every captured habu is one individual record, including animals captured simultaneously.

Required fields:

- `individual_id`: stable unique individual identifier.
- `event_id`: foreign key to the capture event.
- `individual_index`: 1-based index within the event.

Individual-level attributes such as size, sex, posture, movement, and exact discovery position belong here when available. Unknown values remain unknown and must not be inferred.

## Invariants

1. `event_count` equals the number of individual records linked to the event.
2. One event with two captured habu is counted as 1 capture event and 2 captured individuals.
3. Do not duplicate coordinates or timestamps into separate pseudo-events solely because multiple individuals were captured.
4. Preserve source/raw records byte-for-byte. This schema is a normalized/processed representation and never rewrites `data/raw/`.
5. Sightings, roadkill, and captures by other people are not owner-capture individuals. Keep their existing observation semantics separate.
6. Historical data may be migrated only from evidence supported by source records. Ambiguous historical rows remain unresolved rather than guessed.
7. Walk-forward and model features must choose the appropriate unit explicitly. Event-count and individual-count targets are not interchangeable.

## Identifier convention

Recommended deterministic human-readable form:

- Event: `CAP-YYYYMMDD-HHMM-NNN`
- Individual: `<event_id>-II`, where `II` is a zero-padded individual index.

If an existing canonical identifier system later supersedes this convention, preserve referential integrity and record the migration.

## Known normalization example

Source observation: 2026-09-29 00:00, coordinates 28.16750618464175, 129.2997244659382, two juvenile habu captured at the same place/time.

Normalized semantics:

- one capture event
- `event_count = 2`
- two individual records linked by the same `event_id`

This document defines semantics only. Canonical data rows must be produced through the repository ingestion/audit pipeline with source evidence and must not be invented from this specification.
