# Ontology Staged Decomposition 005 — Preregistration

Status: PREREGISTERED / NOT IMPLEMENTED / NOT EXECUTED

## Purpose

Ontology 005 is a fresh full replicate of the frozen Ontology 004 semantic
experiment after Ontology 004 became non-adjudicable because one control B2
request ended in a provider transport timeout.

Ontology 005 is not a completion of the missing Ontology 004 cell.

No semantic output from Ontology 004 will be used in the Ontology 005 analysis.

## Immediate predecessor

Ontology 004 closure commit:

`3f7d96f1c83574e002e3a1972bcca0c6597e3c19`

Ontology 004 scientific disposition:

`NOT_ADJUDICABLE_PROVIDER_OR_BOUNDARY_FAILURE`

Localized predecessor failure:

- ordinal: 45
- specimen: IIR-027
- run index: 3
- stage: B2_NONFORCE_SLOTS
- outcome: PROVIDER_ERROR
- error type: ModelProviderError
- error message: NVIDIA NIM connection timed out
- boundary rejections in the full 004 run: zero

Ontology 004 remains closed and may not be rerun.

## Frozen semantic replication

The Ontology 005 semantic experiment must preserve Ontology 004 exactly with
respect to:

- all 54 semantic request payloads;
- request ordering and interleaving;
- 18 A_COMBINED requests;
- 18 B1_FORCE requests;
- 18 B2_NONFORCE_SLOTS requests;
- all selected primary and control specimens;
- all prompts and output contracts;
- deterministic local B1+B2 merge semantics;
- primary endpoints;
- control endpoints;
- adjudicability gate;
- scientific decision rule;
- semantic claim ceiling.

The 005 instrument must prove request-object and request-SHA equality against
the frozen Ontology 004 request-materialization manifest before network access.

## Transport recovery envelope

The only planned methodological change from Ontology 004 is transport recovery.

For each of the 54 frozen semantic cells:

1. issue the exact frozen request;
2. if it is accepted, do not retry;
3. if and only if it fails with exactly
   `ModelProviderError: NVIDIA NIM connection timed out`,
   wait 4 seconds and permit one retry;
4. the retry must use the exact same ModelRequest and request-projection SHA;
5. preserve both the initial timeout and retry attempt in the receipt;
6. never retry a boundary rejection;
7. never retry another provider-error class;
8. never retry a semantic parse/boundary failure;
9. never make more than one retry for a semantic cell.

A timed-out first transport attempt carries no semantic observation because no
usable response was obtained. If the single permitted retry succeeds, its
accepted response supplies the observation for that same frozen semantic cell.

Nominal provider transport calls: 54.

Absolute transport-call ceiling: 108.

## Adjudicability

The semantic gate is unchanged from Ontology 004.

No scientific disposition may be evaluated unless:

- all 54 semantic cells have an ACCEPTED response;
- all 18 composite observations are complete;
- all 9 primary pairs are complete;
- all 9 control pairs are complete.

If the gate fails, semantic interpretation is withheld.

## Provider prerequisite

Immediately before any live Ontology 005 run, a fresh

`OIC-NVIDIA-PROVIDER-QUALIFICATION-005`

must be frozen and executed exactly once.

Only a `QUALIFIED` disposition that explicitly authorizes Ontology 005 permits
live semantic execution.

## Claim ceiling

Ontology 005 may provide bounded evidence about staged provisional semantic
proposal behavior for the same frozen model/provider and six frozen synthetic
admitted propositions.

It does not establish canonical institutional meaning, interpretation
authority, legal validity, a revised Institutional IR ontology, production
architecture, production staging, cross-model generalization, cross-provider
generalization, or independent validation.

No architectural change is authorized by preregistration or by any eventual
result.

## Current authorization

Authorized now:

- implement the 005 instrument offline;
- materialize all 54 exact semantic requests offline;
- prove exact semantic equality against 004;
- implement and test the transport recovery policy;
- statically freeze the 005 instrument.

Not authorized now:

- Provider Qualification 005 live execution;
- Ontology 005 live execution;
- production prompt changes;
- production-code changes;
- canonicalization;
- Institutional IR construction;
- architectural change.
