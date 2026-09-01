# Ontology 005 — Post-Run Adjudication

**Work order:** `OIC-DEFINITION-ONTOLOGY-STAGED-DECOMPOSITION-005`

**Final scientific disposition:** `REGRESSION`

## Executive adjudication

Ontology 005 is CLOSED as an executed, fully adjudicable negative result.

All 54 frozen semantic requests produced accepted semantic observations. All 18 composite pairs completed: 9 primary and 9 control.

The staged normative-force arm remained correct on the primary population (9/9) and introduced zero B-only normative-force defects on the control population.

The frozen REGRESSION disposition is localized to the staged non-force arm. It introduced two B-only slot defects on the control specimen IIR-027: the `action` slot in runs 1 and 3.

Therefore the preregistered staged decomposition, as tested, does not establish viability under its frozen control criterion. Separation of normative-force inference removed the force-side interference signal but did not preserve the non-force control behavior.

## Regression localization

- Control normative-force B-only defects: `0`.
- Control non-force B-only slot defects: `2`.
- Defect: `IIR-027` / run `1` / slot `action`.
- Defect: `IIR-027` / run `3` / slot `action`.

## Transport event

Semantic cell 51 (`IIR-028`, run 2, `A_COMBINED`) encountered the exact preregistered `ModelProviderError: NVIDIA NIM connection timed out` condition. The one permitted retry used the same request object and identical request projection and returned an accepted semantic observation.

This event is recorded as recovered transport evidence. It is not the localized cause of the REGRESSION disposition.

## Evidence binding

- Execution commit: `713eb9a5f8cbe4b184e163573c30dd9d48cf1541`
- Ontology 005 receipt SHA256: `6ac1d6f79ba7dd10710edc380ab8780f308f335cd4658b83761e0af67557ed35`
- Qualification 005 receipt SHA256: `41ff8801c98621dc132c918c612e713afbbe2a46ffaa41e56710f6de3543d3b6`
- Ontology 005 live-log SHA256: `ed584b780969dfb4a251f18dbaf5fd8234e19a8f1d12f1b2ef9b7415a556d913`

## Claim ceiling

This result applies only to the frozen model/provider, six frozen synthetic admitted propositions, prompts, schemas, request ordering, and decision rule used by Ontology 005.

It does **not** establish:

- canonical institutional meaning;
- interpretation authority;
- legal validity;
- a revised Institutional IR ontology;
- production architecture or production staging;
- cross-model or cross-provider generalization;
- independent validation.

No architecture change is authorized.

## Closure

- Ontology 005 rerun: **NOT AUTHORIZED**.
- Provider Qualification 005 rerun: **NOT AUTHORIZED**.
- Ontology 004 remains immutable and closed.
- Ontology 005 does not retroactively complete Ontology 004.
- Further work requires a new preregistered successor work order.
