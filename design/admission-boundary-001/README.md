# OIC Admission Boundary 001

Status: **OWNER-AUTHORIZED INSTITUTIONAL ADMISSION BOUNDARY DESIGN AND
PREREGISTRATION — NO IMPLEMENTATION**

Starting freeze:
`6968dfc04f2108e910e1983b15262e2b26bf7fc9`
(`OIC-CANDIDATE-LAYER-FREEZE-001`).

## Definition

Admission is the institution-controlled, fail-closed eligibility decision that a
source-grounded Candidate Normative Unit may enter Institutional IR semantic
interpretation. It does not decide the candidate's canonical meaning and is not
legal validation, enforcement, transaction authorization, `ALLOW`, or `DENY`.

The boundary keeps three acts separate:

1. **Source grounding** proves only that literal candidate material occurs in the
   identified source.
2. **Source/authority admissibility** decides whether institution-controlled
   evidence makes that candidate eligible for semantic interpretation.
3. **Semantic interpretation** constructs canonical institutional meaning only
   after a positive admission result.

This package addresses only act 2. Candidate extraction and source grounding are
unchanged.

## Package

* `ADMISSION-CONTRACT-v0.1.md` defines ownership, inputs, minimum evidence,
  invariants, deterministic receipt projection, and the successor seam.
* `ADMISSION-STATE-MACHINE-v0.1.md` freezes the states, reason codes, ordered
  evaluation, conflict rules, and temporal semantics.
* `AUTHORITY-EVIDENCE-v0.1.schema.json` is a design-local draft for the minimum
  machine-verifiable warrant bundle.
* `ADMISSION-RECEIPT-v0.1.schema.json` is a design-local draft for immutable
  outcome evidence.
* `THREAT-MODEL-v0.1.md` defines actors, trust boundaries, threats, and required
  fail-closed treatment.
* `TEST-VECTORS-v0.1.json` preregisters deterministic positive and adversarial
  cases. `TEST-VECTORS-FREEZE-v0.1.json` pins its bytes.
* `PREREGISTRATION-v0.1.md` freezes the test method, falsifiers, and claim ceiling.

These draft schemas are not installed under `schemas/`, are not used by the OIC
runtime, and do not amend the historical admission or authority schemas.

## Authority boundary

The institutional Admission Authority owns admission policy and delegation. An
institution-controlled Authority Registry and evidence custodian supply signed,
versioned authority evidence. A future deterministic Admission Boundary Evaluator
may evaluate the frozen rules, but it does not create authority.

Automatic `ADMITTED` is permitted only when a machine-verifiable institutional
admission warrant already delegates that exact source version, digest, scope, and
time. Creating, expanding, resolving, or overriding a warrant requires an
institutional actor under its governance process. A model can propose candidate
material but can never issue evidence, select the governing warrant, resolve a
conflict, or write an admitted state.

## Status and ceiling

This is a design and preregistration package only. It does not establish legal
validity, universal authority semantics, production readiness, runtime safety,
compliance, successful IR compilation, execution authorization, or independent
validation.

`independent_validation_claim = FALSE`

`NOT SELF-ADJUDICATED`

**NO ADMISSION RUNTIME WAS IMPLEMENTED.**

**NO INSTITUTIONAL IR WAS IMPLEMENTED.**
