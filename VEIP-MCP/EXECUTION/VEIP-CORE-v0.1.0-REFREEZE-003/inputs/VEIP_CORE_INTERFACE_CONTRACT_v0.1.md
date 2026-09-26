# VEIP Core Interface Contract v0.1

Date: 2026-09-21
Program: VEIP-MCP
Status: FROZEN INTERFACE CANDIDATE — MUST PRECEDE CONFORMANCE RUNNER
Supersedes as semantic authority: provisional interface choices embedded in `/VEIP-MCP/EXECUTION/WO-001..003`
Does not supersede: VEIP research claim ceiling or frozen VEIP-MCP v0.3 package

## 0. Governing rule

> **Same normalized semantic input + same evidence set + same engine version = same dimension states, reason codes, and canonical output bytes.**

The core is a deterministic semantic engine. MCP, CLI, host adapters, middleware, and future transports are callers. None may redefine core semantics.

## 1. Pure operations

The v0.1 public semantic interface consists of exactly three operations:

```text
evaluate_claim(request, evidence_resolver) -> AdjudicationResult
evaluate_completion(request, evidence_resolver) -> AdjudicationResult
explain_boundary(adjudication_result, presentation_profile?) -> BoundaryExplanation
```

### `evaluate_claim`
Evaluates what resolved evidence supports about one declared proposition within one declared scope and requested reliance context.

It MUST NOT create evidence, infer missing evidence from prose, convert host declarations into witnessed facts, determine universal truth, or mutate external systems.

### `evaluate_completion`
Evaluates whether the requested outcome and task-completion boundary are established, separately from execution success.

It MUST preserve distinct dimensions for execution, outcome, currentness, provenance binding, channel independence, task completion, and reliance.

### `explain_boundary`
Consumes an existing `AdjudicationResult`, not raw evidence.

Hard invariant:

```text
EXPLANATION_CANNOT_STRENGTHEN_ADJUDICATION
```

It MUST NOT resolve new evidence, re-run adjudication, add a positive dimension, remove a material negative dimension, reinterpret `NOT_ESTABLISHED` as `FALSE`, or reinterpret `UNAVAILABLE` as `NOT_ESTABLISHED`.

## 2. Architectural boundaries

```text
Untrusted source data
      ↓
Observation adapter / channel
      ↓
Evidence records + identities
      ↓
EvidenceResolver
      ↓
veip-core
      ↓
AdjudicationResult
      ↓
MCP / CLI / host / middleware presentation
```

Core invariants:

```text
HOST_SUPPLIED_FACT != ESTABLISHED_FACT
LLM_PARSED_EVIDENCE != WITNESSED_EVIDENCE
VALID_SCHEMA != VALID_EVIDENCE
VALID_HASH != TRUE_OR_RELEVANT_EVIDENCE
```

## 3. Evidence resolver interface

The core MUST consume evidence through a resolver abstraction rather than accepting caller-created booleans such as `receipt_present=true`, `signature_valid=true`, `subject_match=true`, or `outcome_observed=true`.

Reference interface:

```python
class EvidenceResolver(Protocol):
    def resolve_evidence(self, evidence_id: str) -> EvidenceRecord | ResolutionFailure: ...
    def resolve_subject(self, subject_ref: str) -> SubjectRecord | ResolutionFailure: ...
    def resolve_extent(self, extent_ref: str) -> ExtentRecord | ResolutionFailure: ...
    def resolve_channel(self, channel_ref: str) -> ChannelRecord | ResolutionFailure: ...
    def resolve_run(self, run_id: str) -> RunRecord | ResolutionFailure: ...
```

The resolver may be backed by a local fixture store, receipt registry, deterministic adapter, signed artifact store, or production evidence service. Semantically identical resolved records MUST produce identical core results regardless of backend.

## 4. Canonical request types

### `ClaimEvaluationRequest`
Required:
- `request_id`
- `proposition`
- `subject_ref`
- `extent_ref`
- `evidence_refs`
- `requested_reliance`
- `contract_version`

Optional:
- `run_ref`
- `validity_requirements`
- `declared_relation_ref`
- `output_interpretation_ref`
- `metadata` (non-authoritative)

### `CompletionEvaluationRequest`
Required:
- `request_id`
- `requested_outcome`
- `subject_ref`
- `extent_ref`
- `execution_evidence_refs`
- `outcome_evidence_refs`
- `completion_boundary`
- `requested_reliance`
- `contract_version`

Optional:
- `run_ref`
- `validity_requirements`
- `metadata` (non-authoritative)

### Prohibited caller-supplied adjudication flags

These must not be accepted as authoritative request facts:

```text
reported_success
signature_valid
subject_match
extent_match
current
outcome_observed
channel_independent
established_outcomes
```

If needed, such facts must exist inside attributable evidence and be independently adjudicated.

## 5. Canonical evidence record

Required:
- `evidence_id`
- `evidence_type`
- `subject_ref`
- `extent_ref`
- `run_ref` or explicit null
- `observed_at`
- `payload_identity`
- `observation`
- `channel_ref`
- `receipt_ref` or explicit null
- `record_version`

`payload_identity` binds bytes or canonical form only. A valid digest does not establish truth, relevance, or independence.

A generic free-text evidence summary MUST NOT be the sole fact-bearing representation for a positive adjudication.

## 6. Disposition dimensions

Canonical v0.1 dimensions:

```text
claim_support
execution
outcome
currentness
provenance_binding
channel_authentication
channel_independence
task_completion
reliance
```

Common state vocabulary:

```text
ESTABLISHED_WITHIN_SCOPE
NOT_ESTABLISHED
UNAVAILABLE
HELD
HUMAN_JUDGMENT_REQUIRED
NOT_APPLICABLE
```

Public states such as `STALE`, `CURRENT`, `INVALID`, `PASS`, or `FAIL` are prohibited as dimension states. Specific conditions belong in reason codes.

Example:

```text
currentness = NOT_ESTABLISHED
reason = NOT_ESTABLISHED_STALE
```

Positive state in one dimension never implies another.

## 7. Reason-code contract

Reason codes are stable machine semantics: uppercase, versioned, deterministic, and core-generated.

Initial registry classes:

### Evidence availability
- `EVIDENCE_NOT_FOUND`
- `MISSING_OBSERVATION_IDENTITY`
- `CURRENT_IDENTITY_UNAVAILABLE`
- `MISSING_OBSERVATION_RECEIPT`
- `EXTENT_MATCHES_NOTHING`

### Binding/provenance
- `CHANNEL_NOT_AUTHORIZED`
- `RECEIPT_AUTHENTICATION_FAILED`
- `RECEIPT_REPLAYED`
- `RECEIPT_WRONG_SUBJECT_OR_EXTENT`
- `RUN_BINDING_NOT_ESTABLISHED`
- `EVIDENCE_PAYLOAD_IDENTITY_MISMATCH`
- `EVIDENCE_BINDING_NOT_ESTABLISHED`

### Currentness
- `NOT_ESTABLISHED_STALE`

### Measurement/semantics
- `CAUSAL_DEPENDENCE_NOT_ESTABLISHED`
- `DECLARED_RELATION_NOT_PRESERVED`
- `NUISANCE_DEPENDENCY_DETECTED`
- `OUTPUT_INTERPRETATION_NOT_PINNED`
- `OUTPUT_INTERPRETATION_MISMATCH`
- `PROPOSITION_EVIDENCE_RELATION_NOT_ESTABLISHED`

### Completion/reliance
- `OUTCOME_NOT_OBSERVED`
- `COMPLETION_BOUNDARY_NOT_SATISFIED`
- `ADVERSE_SELF_DECLARATION_HELD`
- `HUMAN_JUDGMENT_REQUIRED`

### Host/ingress
- `UNTRUSTED_HOST_DERIVED_FACT`
- `UNBOUND_EVIDENCE_REFERENCE`
- `SCHEMA_CONTRACT_MISMATCH`

The registry will be frozen as its own artifact before fixtures are executable.

## 8. Result type

Canonical result fields:

```json
{
  "contract_version": "veip-core-interface-0.1",
  "engine": {
    "name": "veip-core",
    "version": "0.1.0",
    "build_id": "...",
    "semantic_profile": "veip-mcp-v1"
  },
  "request_id": "...",
  "operation": "evaluate_claim|evaluate_completion",
  "normalized_input_digest": "...",
  "evidence_set_digest": "...",
  "dimensions": {},
  "reason_codes": [],
  "limits": [],
  "next_useful_checks": [],
  "canonical_output_digest": "..."
}
```

Human-readable prose must not alter semantic identity.

## 9. Engine identity

Every adjudication MUST include:
- interface contract version;
- engine semantic version;
- build identifier/digest;
- semantic profile.

Different engine versions are not assumed semantically equivalent merely because shape matches.

## 10. Normalization

Before adjudication:
1. validate canonical schema;
2. normalize Unicode where defined;
3. reject ambiguity-causing duplicates;
4. sort unordered sets canonically;
5. preserve semantically meaningful order;
6. normalize timestamps to RFC3339 UTC;
7. reject undeclared normative properties;
8. never synthesize omitted evidence fields.

Normalization must not invent semantic facts.

## 11. Deterministic serialization

v0.1 semantic serialization is:

```text
UTF-8 JSON
RFC 8785 JSON Canonicalization Scheme (JCS)
no insignificant whitespace
```

`canonical_output_digest = sha256(JCS(result_without_canonical_output_digest))`.

Conformance compares semantic object equality, canonical byte equality, and digest equality.

## 12. Error vs semantic-state behavior

### Interface/programmer errors
These prevent evaluation:
- malformed JSON;
- schema-invalid request;
- unsupported contract version;
- unsupported operation;
- internal invariant violation.

They return `InterfaceError`, not an adjudication.

### Semantic non-positive states
These are valid adjudications:
- missing evidence;
- missing observation identity;
- replay;
- wrong subject;
- stale evidence;
- unobserved outcome;
- channel independence not established.

Rule:

> **Expected evidence failure is data, not an exception.**

## 13. Interface error type

```json
{
  "error_type": "INTERFACE_ERROR",
  "error_code": "SCHEMA_VALIDATION_FAILED",
  "contract_version": "veip-core-interface-0.1",
  "request_id": null,
  "details": []
}
```

Minimum error codes:
- `MALFORMED_REQUEST`
- `SCHEMA_VALIDATION_FAILED`
- `UNSUPPORTED_CONTRACT_VERSION`
- `UNSUPPORTED_OPERATION`
- `INTERNAL_INVARIANT_VIOLATION`

No interface error may map to a positive semantic state.

## 14. Evidence-set identity

The core MUST compute an `evidence_set_digest` from exact resolved evidence identities actually considered.

```text
same request + different evidence set -> different semantic identity
same request + same evidence set + same engine -> deterministic same result
```

Selective omission remains a residual risk unless completeness is separately established; limits must state that.

## 15. Limits

Machine-readable limits are part of the semantic result, not prose disclaimers.

Examples:
- `EVIDENCE_SET_COMPLETENESS_NOT_ESTABLISHED`
- `CHANNEL_INDEPENDENCE_NOT_ESTABLISHED`

## 16. `evaluate_claim` transition order

At minimum:
1. resolve subject and extent;
2. resolve evidence refs;
3. validate evidence identity/provenance;
4. establish subject/extent/run applicability;
5. evaluate currentness if required;
6. evaluate declared proposition/evidence relation;
7. evaluate measurement-assurance conditions if applicable;
8. produce `claim_support`;
9. produce reliance only for the requested target.

## 17. `evaluate_completion` transition order

At minimum:
1. resolve execution evidence;
2. resolve outcome evidence;
3. adjudicate execution independently;
4. adjudicate outcome independently;
5. adjudicate currentness independently;
6. apply completion boundary;
7. produce task-completion state;
8. produce reliance state.

Core law:

```text
PROTOCOL_RECEIPT != EXECUTION
EXECUTION != OUTCOME
OUTCOME != CURRENT_OUTCOME
CURRENT_OUTCOME != TASK_COMPLETION
```

## 18. `explain_boundary`

Input is a canonical adjudication plus optional presentation profile.

Output MUST preserve every material dimension, blocking reason code, and semantic limit. It may simplify wording and suggest next checks. It may not change adjudication.

## 19. Purity

Core semantic operations are pure.

Allowed:
- deterministic resolver reads;
- normalization;
- canonicalization;
- result construction.

Not allowed:
- network mutation;
- external action;
- credential release;
- evidence creation;
- consequence-sink writes.

## 20. Current WO-003 compatibility findings

`/VEIP-MCP/EXECUTION/WO-003/veip_mcp_core.py` is a prototype, not the controlling specification.

Required changes:
1. generic `evaluate()` -> three-operation contract;
2. caller booleans -> resolver-backed evidence;
3. `STALE/CURRENT/INVALID` -> canonical state vocabulary + reason codes;
4. add engine identity;
5. add canonical input/evidence/output digests;
6. add resolver abstraction;
7. schema-control requests;
8. make explanation consume adjudication only.

Earlier tests remain useful prototype evidence but must be remapped to this contract.

## 21. Interface acceptance criteria

Freeze only when:
- request types are schema-defined;
- resolver semantics defined;
- dimensions fixed;
- state vocabulary fixed;
- reason-code namespace fixed;
- engine identity fixed;
- normalization fixed;
- serialization fixed;
- error-vs-semantic-state behavior fixed;
- explanation non-strengthening testable.

## 22. Determinism invariant

For valid semantic input `I`, resolved evidence set `E`, and engine identity `V`:

```text
normalize(I, E, V) = N
evaluate(N) = R
canonicalize(R) = B
```

Repeated execution must satisfy:

```text
N1 == N2
R1 == R2
B1 == B2
sha256(B1) == sha256(B2)
```

unless the evidence resolver returns a different evidence set or engine identity changes.
