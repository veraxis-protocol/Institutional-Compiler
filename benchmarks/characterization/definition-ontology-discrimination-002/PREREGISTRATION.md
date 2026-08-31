# OIC Definition Ontology Discrimination 002 — Preregistration

Status: FROZEN / PRE-LIVE / NOT AUTHORIZED TO EXECUTE UNTIL PROVIDER QUALIFICATION 002 = QUALIFIED

Starting repository SHA: `c4a87eb8483c3bd965612b601399463e005bd73e`

## Purpose

Successor to `OIC-DEFINITION-ONTOLOGY-DISCRIMINATION-001`.

The semantic experiment is intentionally unchanged from 001: same six specimens, same two arms, same ontology clarification, same three runs per specimen, same deterministic paired interleaving, same 36 planned calls, same zero-retry rule, and the same semantic decision thresholds.

002 exists solely to repair the scientific adjudication boundary exposed by 001.

## Provider prerequisite

Live semantic execution is forbidden unless the local receipt:

`.local/provider-qualification-receipts/OIC-NVIDIA-PROVIDER-QUALIFICATION-002.json`

exists and records both:

- `disposition = QUALIFIED`
- `semantic_successor_authorized = true`

Qualification 001 cannot satisfy this prerequisite and must never be reused.

## Scientific adjudicability gate

Semantic adjudication is permitted only if:

- 36/36 planned observations are `ACCEPTED`;
- all 18 A/B specimen-run pairs contain both accepted observations;
- all 9 primary-definition A/B pairs are complete;
- all 9 control A/B pairs are complete.

If any condition fails, the mandatory scientific disposition is:

`NOT_ADJUDICABLE_PROVIDER_FAILURE`

No semantic decision rule may be evaluated in that state.

## Semantic decision rules

If and only if the adjudicability gate passes, reuse the 001 semantic rules byte-for-meaning:

- `REGRESSION`
- `SUPPORTS_ONTOLOGY_CLARIFICATION`
- `PARTIAL_SUPPORT`
- `INCONCLUSIVE_EFFECT`
- `REFUTES_SIMPLE_ONTOLOGY_CLARIFICATION`

## Boundaries

No production prompt change.
No schema split.
No canonicalization.
No Institutional IR runtime.
No authority/admission inference.
No independent validation claim.
No rerun of Ontology 001.
