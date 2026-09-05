# Open Institutional Compiler

- **Status:** BOUNDED_REFERENCE_IMPLEMENTATION — scoped independent Gate F repository validation passed; merge pending Gate G and owner authorization
- **Bootstrap date:** 2026-07-29
- **Governing design:** TDD-OIC-001 v1.1

[![Research Paper DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22160516.svg)](https://doi.org/10.5281/zenodo.22160516)

Open Institutional Compiler (OIC) is developing a reviewable path from the
human-readable sources that govern a regulated enterprise to the explicit
controls its software and authorization systems can evaluate.

Target capability:

> A regulated enterprise should be able to automate a larger class of
> consequential actions and regulated workflows without lowering the
> evidentiary standard required to authorize, explain, audit, or correct those
> actions.

**What exists today:** a Python infrastructure package for
offline schema validation, historical bootstrap verification, current manifest
verification, environment and gate diagnostics, and reproducible CI and SBOM
checks, plus a deterministic offline synthetic reference path: grounded candidates,
divergent review records, supplied authority-evidence admission, provisional eleven-slot
interpretation, unresolved references, and canonical evidence receipts. It is not a
production institutional compiler.

**What is blocked:** production compilation and runtime authorization remain unestablished.
The broader production semantic gate remains BLOCKED. The separately owner-admitted
synthetic slice does not qualify a model provider or broaden corpus rights.

Run `make demo` (or `python -B scripts/demo_bounded_semantic_path.py`) in the installed
environment. It emits canonical JSON, makes no network request, needs no model credentials,
and writes no repository files. Two review records remain divergent; missing/malformed
authority evidence is refused. The eleven slots are provisional, not canonical meaning.
Independent Gate F repository validation passed for candidate
`c0108a7a80585d6f5732407d4904ba815073ecd2` (tree
`1d12b17aad7977c939090909171183be166cfd50`): canonical Linux execution reported
1714 passed, 0 failed, 0 errors, 1 declared skip, 93.5% coverage, and two
byte-identical offline demo runs with SHA-256
`0f9d01bb0dfc488505e027ac7bd8aecf869578e379b5a977cd9d642f2101a39a`. This establishes reproducibility, boundary integrity, the
specified fail-closed properties, packaging, and the named adversarial checks for
that exact candidate only. It does not establish semantic correctness, model
accuracy, institutional validity, legal effect, provider qualification, rights
resolution, ontology execution, production compilation, runtime authorization,
institutional-IR closure, enterprise readiness, or benchmark superiority. It
also does not establish legal validity or production readiness. Merge remains
pending Gate G and owner authorization.
See [`CAPABILITY_MATRIX.json`](docs/capabilities/CAPABILITY_MATRIX.json) for exact provenance
and ceilings. NVIDIA is NOT_QUALIFIED; Canada redistribution is UNRESOLVED; Ontology 007R1
is unexecuted and execution-unauthorized. No model accuracy or legal validity is claimed.

## Research paper

**From Governing Source to Warranted Control: A Formal Model of Institutional Compilation**

Research preprint by Arkadiy Miteiko, Veraxis Research Group.

DOI: [10.5281/zenodo.22160516](https://doi.org/10.5281/zenodo.22160516)

The paper formalizes **institutional compilation** as the governed
transformation from governing source to admitted meaning to warranted machine
control. It defines eight jointly necessary obligations: source binding,
admission authority, semantic conservation, unknown preservation, authority
non-amplification, temporal currentness, version binding, and target-projection
fidelity.

Its bounded executable checker exhaustively evaluates all 6,561 states of the
eight-obligation aggregation rule and kills five deliberately defective
aggregators. That experiment establishes conformance of the finite aggregation
rule only. It does **not** establish natural-language semantic correctness,
benchmark superiority, legal or regulatory compliance, production readiness,
or independent validation.

The publication is a scholarly research artifact. This repository is the
evolving engineering implementation record. The paper's archived engineering
snapshot is bound to repository commit
`914830ceec70bde17004d2ccbbb13218ca44a89b`; later repository commits do not
retroactively alter the published paper. The DOI does not certify the
repository implementation, and repository CI does not validate the paper's
substantive legal or semantic claims. The paper does not establish semantic
benchmark PASS, production readiness, regulatory compliance, or independent
validation.

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

The control-production bottleneck is the creation of an authorized, versioned,
source-grounded control with explicit uncertainty and a correction path.

## Runtime authorization starts downstream

OPA evaluates policy over structured input and data and returns policy decisions
to the integrating application. Rego is OIC's first proposed executable target.
OIC operates upstream of that evaluation boundary; it does not replace OPA.

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

## How OIC will be measured

Generating syntactically valid Rego is not the OIC success criterion. OIC-Bench
is intended to test whether the source-to-control transformation preserves
source support, authority, uncertainty, exceptions, temporal and currentness
state, evidence requirements, runtime behavior, change impact, and human-review
efficiency.

The relevant question is whether OIC can automate more of regulated-enterprise
control production while preserving the evidence and authority properties that
make the resulting controls safe to rely on. OIC is successful only if increased
control-production automation does not come from converting unsupported,
ambiguous, stale, or unauthorized meaning into executable controls.

The following development gates are preregistered in TDD-OIC-001 v1.1. They are
targets, not observed results, calibrated thresholds, independent validation, or
current product claims.

| Benchmark | Target | Status |
|---|---:|---|
| Source-supported executable fields | >=99% | TARGET - NOT MEASURED |
| Unsupported executable-field rate | <=1% | TARGET - NOT MEASURED |
| Unknown-to-false conversions | 0 | TARGET - NOT MEASURED |
| Authority Reconstruction F1 | >=0.80 | TARGET - NOT MEASURED |
| Ambiguity recall | >=0.85 | TARGET - NOT MEASURED |
| False-resolution rate | <=0.05 | TARGET - NOT MEASURED |
| Behavioral conformance | >=0.95 | TARGET - NOT MEASURED |
| Change-impact recall | >=0.95 | TARGET - NOT MEASURED |

### Provisional comparative target

Separately, TDD-OIC-001 v1.1 preregisters a provisional comparative-claim
threshold: at least 40% reduction in active human time to first admitted
envelope versus the manual baseline, with no more than 2 percentage-point loss
in adjudicated behavioral quality.

**Status: PROVISIONAL TARGET - NOT MEASURED - NOT CALIBRATED.**

This threshold is subject to calibration, retention, amendment, or withdrawal
under the benchmark governance process before it can support a public
comparative claim. It is not an absolute safety or release gate.

Full OIC-Bench v0.1 is designed around public, frozen-test, private held-out,
adversarial, change-impact, runtime, and practitioner-review partitions. Its
proposed aggregate scope includes 21 governing documents, approximately 140
pages, at least 260 adjudicated normative clauses, at least 85 candidate
controls, at least 34 known ambiguities or conflicts, at least 160 runtime
cases, and at least 18 source-version pairs. **PROPOSED BENCHMARK SCOPE - NOT A
MEASURED SUFFICIENCY CLAIM.**

### Comparative baselines

OIC-Bench is designed to compare OIC with named control-production paths, not
only with earlier OIC versions:

- **Direct LLM-to-Rego:** the same source inputs and, where architectural
  comparison requires it, the same declared model.
- **Modular document-to-policy pipeline:** extraction, validation, and target
  compilation without OIC's admission and authority representation.
- **Human policy engineer:** an experienced practitioner using ordinary policy
  and control-production tools.
- **Source-grounded knowledge graph:** source entities and relations without a
  formal admission or control envelope.
- **RAG plus rule generation:** retrieved source passages followed by
  target-policy generation.
- **Commercial capability review:** public documentation and controlled trials
  where evidence is available. Unknown capabilities remain `UNKNOWN`; they are
  not assumed absent.

No comparative outperformance claim is permitted until the full benchmark,
baseline implementations, annotation protocol, and held-out evaluation are
frozen and independently reviewed.

### Proposed future metric: Safe Automation Coverage

**PROPOSED - NOT YET PART OF THE FROZEN OIC-BENCH SPECIFICATION.**

Safe Automation Coverage would measure the percentage of in-scope,
gold-adjudicated regulated-control cases that reach an admitted executable state
while satisfying all applicable source-support, authority, evidence, ambiguity,
currentness, and behavioral gates.

`CANNOT`, escalation, or human judgment may be the correct outcome. The metric
must not reward falsely converting ambiguous or unsupported work into executable
controls. Safe Automation Coverage is not equivalent to `ALLOW` rate. No
numerical target is authorized.

A related operational measure is **admitted automation yield under fixed
expert-review budget**: the number of valid admitted executable controls
produced under a fixed amount of qualified reviewer time, compared with the
manual baseline. This measure is also **PROPOSED - NOT YET PART OF THE FROZEN
OIC-BENCH SPECIFICATION.** Formal adoption of either measure requires benchmark
governance, an ADR, and a traceability update.

## Current measured evidence

`TARGET` identifies a preregistered or proposed benchmark threshold, not an
observed result. `MEASURED` identifies an observed result tied to a reproducible
repository or benchmark composition. `BLOCKED` or `NOT YET RUN` identifies an
evaluation that cannot proceed because semantic implementation or evidence
prerequisites remain incomplete.

Exact repository composition, CI execution composition, and run provenance for
these measurements are recorded in the corresponding pull-request and CI
evidence record. The measurements below are infrastructure evidence, not
semantic OIC-Bench results.

| Evidence class | Current state |
|---|---|
| Non-semantic infrastructure verification | MEASURED |
| Schema validation | MEASURED - 9/9 |
| Bootstrap integrity | MEASURED - 52/52 |
| Infrastructure falsification harness | MEASURED - 4/4 |
| Prior main Linux baseline | MEASURED - 1255 passed, 1 intentional skip; not candidate acceptance |
| Manifest | MEASURED - INCOMPLETE, required exit 3 |
| Bounded synthetic path / production semantic gate | BOUNDED_REFERENCE_IMPLEMENTATION / BLOCKED |
| OIC-Bench preflight design | PREREGISTERED |
| Semantic OIC-Bench preflight | NOT YET RUN |
| Full OIC-Bench v0.1 | NOT YET RUN |
| Comparative outperformance | NOT ESTABLISHED |
| Practitioner usability benchmark | NOT YET RUN |
| Regulated-enterprise pilot evidence | NOT ESTABLISHED |

These results verify repository infrastructure. They are not semantic OIC-Bench
results. The benchmark preflight metrics remain proposed or preregistered and
not measured. Experimental branch results are not accepted benchmark evidence.

## Development roadmap

The roadmap is evidence-gated, not schedule-driven. No stage is complete
because its features exist. Advancement requires the named benchmark,
verification, operational, and independent-review evidence.

### Stage 0 - Infrastructure and benchmark readiness

**STATUS: CURRENT**

Current capabilities include non-semantic schemas and contracts,
manifest/integrity verification, the falsification harness, supply-chain
controls, and the benchmark preflight specification.

Exit requires complete governing-source rights and provenance plus sufficient
ZTL and VEIP provisional-interface evidence to open the semantic code-start
gate.

### Stage 1 - Source-to-control reference

**STATUS: BOUNDED SYNTHETIC SUBSET IMPLEMENTED; full source-to-control path BLOCKED**

Target path:

```text
governing sources
-> source anchors
-> candidate normative meaning
-> ambiguity and review docket
-> authorized admission
-> Institutional IR / Open Control Envelope
-> Rego
-> runtime result
-> lineage
```

Advancement requires a reproducible semantic preflight, passing critical
invariants, published raw benchmark outputs, and visible failures and
limitations.

### Stage 2 - Evidence release

Target evidence includes a frozen OIC-Bench v0.1; public, frozen, held-out, and
adversarial partitions; named comparative baselines; a human policy-engineer
baseline; change-impact evaluation; a practitioner usability study; and
independent technical and security review.

Exit permits only bounded benchmark claims for the tested scope.

### Stage 3 - Regulated-enterprise pilot

Target capabilities include real regulated-enterprise governing sources,
SSO and identity, tenancy, evidence-system integration, an on-premises or
offline profile, change propagation, rollback, and operational monitoring.

Advancement requires a controlled design-partner pilot, security evidence,
runtime and reliability evidence, and scoped pilot-readiness claims.

### Stage 4 - Continuous regulated control compilation

Target capabilities include governing-source monitoring, amendment and
supersession detection, control-dependency impact, invalidation, re-admission,
controlled publication, CI/CD integration, and historical replay.

Advancement requires change-impact benchmarks, currentness and revocation
tests, operational incident exercises, and replay and correction evidence.

### Stage 5 - Dependable regulated agents

Target capabilities include agent identity and mandate, dynamic grounding, ZTL
warrant, VEIP execution continuity, delegation and revocation, reliance and
correction, and multi-agent consequential-action chains.

Advancement requires a real consequential-runtime pilot, measured
consequence-control behavior, and independent audit.

### Later - Open infrastructure

Target capabilities include interoperable control-envelope profiles,
independent compiler and adapter implementations, domain packs, conformance
suites, and federated authority and control ecosystems.

Evidence requires independent implementations or consuming projects, external
conformance, and community governance.

## Current phase

OIC-SEMANTIC-PROMOTION-001 admits the bounded offline synthetic reference path only.
It currently implements four infrastructure CLI commands:

- `oic validate-schema`
- `oic verify-bootstrap`
- `oic verify-manifest`
- `oic doctor`

The separate demo exercises candidate extraction, supplied synthetic admission evidence,
and provisional interpretation. It does not implement Institutional IR production,
Open Control Envelope generation, Rego compilation, or runtime semantic decisions.

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

The full production source-to-control objective remains blocked. When its prerequisites are
authorized, a bounded set of public or synthetic procurement governing sources
is intended to flow through:

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

The repository is an infrastructure foundation with a bounded synthetic reference path.
It is not a production institutional compiler. Current scope,
provisional interfaces, corpus restrictions, human-judgment boundaries, and
benchmark limitations are recorded in [`LIMITATIONS.md`](LIMITATIONS.md).

Licensed under the PolyForm Noncommercial License 1.0.0.
Noncommercial use, modification, testing, and distribution are permitted
subject to the license terms. Commercial use requires a separate written
license from Veraxis.

## Claims discipline

Architecture statements, measured results, and release claims are different
things. Passing tests or CI does not establish semantic correctness,
institutional validity, compliance, comparative advantage, or owner acceptance.

The permitted, evidence-gated, and forbidden claims are recorded in
[`CLAIMS.md`](CLAIMS.md). The broader production semantic gate remains blocked by
[`STATUS.md`](STATUS.md).

## Citation

Miteiko, A. (2026). *From Governing Source to Warranted Control: A Formal Model
of Institutional Compilation*. Zenodo.
https://doi.org/10.5281/zenodo.22160516
