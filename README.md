# Open Institutional Compiler

- **Status:** OWNER-AUTHORIZED BOOTSTRAP - PRE-EXTERNAL-REVIEW
- **Bootstrap date:** 2026-07-29
- **Governing design:** TDD-OIC-001 v1.1

Open Institutional Compiler (OIC) is developing a reviewable path from the
human-readable sources that govern a regulated enterprise to the explicit
controls its software and authorization systems can evaluate.

The target capability is straightforward:

> A regulated enterprise should be able to automate a larger class of
> consequential actions and regulated workflows without lowering the
> evidentiary standard required to authorize, explain, audit, or correct those
> actions.

**What exists today:** a tested, non-semantic Python infrastructure package for
offline schema validation, historical bootstrap verification, current manifest
verification, environment and gate diagnostics, and reproducible CI and SBOM
checks. It is not a functioning institutional compiler.

**What is blocked:** semantic implementation remains blocked pending the corpus
provenance and ZTL/VEIP interface evidence listed in [`STATUS.md`](STATUS.md).
Nothing in this README opens that gate or promotes the repository's maturity.

## Capability being developed

Regulated enterprises govern consequential work through heterogeneous sources:
regulations, enterprise policies, procedures, approval matrices, contracts,
amendments, definitions, exceptions, and prior decisions. Runtime authorization
requires a different form: explicit actors, actions, conditions, authority
limits, evidence requirements, effective periods, exceptions, and failure
behavior.

The conversion between those forms remains substantially manual:

```text
governing sources
-> human interpretation
-> control matrix
-> developer translation
-> Rego / policy-as-code / workflow logic
-> runtime authorization
```

Teams reconcile definitions and amendments, identify applicable authority and
exceptions, specify evidence, translate the result into runtime artifacts,
create tests, and later reconstruct lineage for audit or change analysis. Each
translation can create another interpretation of the same governing source.

OIC is intended to support a different control-production path:

```text
governing sources
-> source-grounded candidate meaning
-> explicit ambiguity and missing support
-> authorized institutional admission
-> portable executable control
-> runtime authorization
-> evidence, reliance, and correction
```

The development hypothesis is that more of this transformation can be
automated without automating institutional authority itself.

## Development hypothesis

OIC is intended to produce reviewable, source-grounded candidate controls;
route unresolved meaning to authorized enterprise reviewers; compile only
institutionally admitted meaning; and retain the evidence needed to reconstruct
why a runtime action was permitted, denied, escalated, or could not be
determined.

Machine extraction may propose meaning. It does not create authority.
Confidence does not constitute institutional admission. Ambiguity,
contradiction, unsupported meaning, missing authority, unresolved exceptions,
and insufficient evidence must remain visible. They must not be coerced into an
executable `ALLOW`.

Authorized enterprise reviewers remain responsible for admitting candidate
meaning for a stated scope and use. Target code is a projection. The proposed
canonical admitted representation is Institutional IR, and the proposed
portable enforcement boundary is the Open Control Envelope.

If this approach succeeds, a larger set of consequential regulated actions may
become safely automatable without reducing the authority, evidence, review, or
correction obligations that govern them. This is a development hypothesis. It
is not an established release, benchmark, adoption, or compliance claim.

## Why now

Runtime authorization infrastructure can evaluate structured policy at high
volume. Document parsing and language models can extract, classify, anchor, and
propose candidate structures. Agentic systems can propose and execute
consequential actions faster than repeated undocumented human interpretation
can scale.

These capabilities do not remove the control-production boundary. Generated
candidate meaning is still untrusted. A regulated enterprise must determine
which source applies, what it authorizes, what evidence is required, which
exceptions govern, and who may admit the result.

The scarce artifact is not another confidence score. It is an authorized,
versioned, source-grounded control with explicit uncertainty and a correction
path.

## Runtime authorization starts downstream

OPA evaluates policy against structured data. Given a policy and facts, it can
answer whether an action is allowed. Rego is OIC's first proposed executable
target. OIC complements OPA; it does not replace it or raise OPA's enforcement
capability.

Cedar, relationship authorization, and comparable systems provide mature
runtime authorization approaches. They expect policies, models, relationships,
entities, or equivalent control inputs to be supplied. OIC addresses the
reviewable path by which heterogeneous regulated-enterprise sources could
become those institutionally admitted inputs.

Rules-as-Code and computational-law systems address important parts of the
upstream problem. Many depend on deliberate human formalization or focus on a
specific domain. Document AI and language models can assist extraction and
proposal, but generated output does not establish institutional authority.

The interface is:

```text
policy engine: execute or evaluate the control
OIC:           establish the reviewable path from governing sources to that control
```

Existing systems are not deficient for stopping at this boundary. That boundary
is the interface OIC is designed to supply. See the prior-art and build/reuse
treatment in [`TDD-OIC-001 v1.1`](docs/tdd/TDD-OIC-001-v1.1.pdf), especially
Section 3.

The differentiating hypothesis concerns the integrated transformation and its
boundary discipline, not novelty of individual components. OIC does not claim
standalone novelty for policy evaluation, Rules as Code, provenance,
delegation, semantic preservation, authority versus logical warrant, issuance
versus evaluation, counter-evidence, or the distinction between institutional
meaning and representation.

The proposed conjunction is:

```text
regulated-enterprise governing sources
-> source-grounded candidate meaning
-> explicit uncertainty
-> authorized institutional admission
-> target-independent control representation
-> runtime policy
-> evidence
-> correction
```

Whether this conjunction is useful and differentiated remains unproven until
comparative benchmarks, independent review, and external consumption establish
it. See [`CLAIMS.md`](CLAIMS.md) for the evidence required before stronger
statements are permitted.

## Current phase

This repository authorizes contract-first, non-semantic infrastructure work.
It currently implements four infrastructure CLI commands:

- `oic validate-schema`
- `oic verify-bootstrap`
- `oic verify-manifest`
- `oic doctor`

It does not implement document interpretation, candidate extraction,
institutional admission, Institutional IR production, Open Control Envelope
generation, Rego compilation, or runtime semantic decisions.

Run the safe non-semantic checks after the hash-locked installation described
in [`docs/operations/CI.md`](docs/operations/CI.md):

```bash
make verify
make falsify
```

`oic verify-manifest --all` currently reports `INCOMPLETE` and exits `3`
because the local corpus evidence is incomplete. That result is intentional. It
must not be normalized into success.

## First executable objective

The first semantic objective remains blocked. When its prerequisites are
authorized, a bounded public or synthetic procurement corpus is intended to
flow through:

```text
documents
-> source anchors
-> candidate normative units
-> review docket
-> admitted record
-> Open Control Envelope
-> Rego
-> ALLOW / DENY / CANNOT
-> lineage
```

This objective is limited to the named procurement profile. It does not imply
support for arbitrary enterprise policy, jurisdictions, or regulated workflows.

## What OIC does not do

OIC does not create institutional authority. It does not turn model confidence
into admission, eliminate authorized review, guarantee legal or regulatory
compliance, or make automation inherently safer.

The proposed design must fail closed. Missing source support, authority,
admission, evidence, current versions, or grounding facts must block, escalate,
or return `CANNOT`. Open-textured standards remain human-judgment boundaries
unless an admitted decision procedure exists.

ZTL and VEIP remain provisional project-controlled interfaces. ZTL is intended
to evaluate logical warrant from admitted grounds; it does not establish source
authority or interpret prose. VEIP is intended to preserve execution and
correction continuity; it does not create institutional meaning. Their required
evidence is listed in [`STATUS.md`](STATUS.md) and
[`LIMITATIONS.md`](LIMITATIONS.md).

## Governing invariants

The complete set is in
[`docs/requirements/INVARIANTS.md`](docs/requirements/INVARIANTS.md). Core
boundaries include:

- no executable field without a source anchor or an explicit institutionally
  admitted addition;
- no enforcement artifact from a state earlier than `admitted`;
- candidate confidence never substitutes for institutional admission;
- unknown never becomes grounded false;
- missing authority, admission, evidence, current version, or facts never
  silently yields `ALLOW`;
- every executable artifact binds its compiler, schema, source, admission, and
  test versions; and
- every published runtime verdict must be replayable to its exact control,
  admission, sources, warrant, inputs, and versions.

## Public limitations

The repository is a governance, contract, and non-semantic infrastructure
foundation. It is not a functioning institutional compiler. Current scope,
provisional interfaces, corpus restrictions, human-judgment boundaries, and
benchmark limitations are recorded in [`LIMITATIONS.md`](LIMITATIONS.md).

No license grant or SPDX identity is established. Licensing remains pending
counsel review.

## Claims discipline

Architecture statements, measured results, and release claims are different
things. Passing tests or CI does not establish semantic correctness,
institutional validity, compliance, comparative advantage, or owner acceptance.

The permitted, evidence-gated, and forbidden claims are recorded in
[`CLAIMS.md`](CLAIMS.md). Semantic implementation remains blocked by
[`STATUS.md`](STATUS.md).
