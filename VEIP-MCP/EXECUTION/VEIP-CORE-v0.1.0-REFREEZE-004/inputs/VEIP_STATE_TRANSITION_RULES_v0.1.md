# VEIP State Transition Rules v0.1 (`VEIP_STATE_TRANSITION_RULES_v0.1_draft.md`)

*Normative Executable Semantics Layer for `veip-core` v0.1.0 (Revision 6 - Final Freeze Candidate)*

---

## 1. Normative Scope & Frozen Inputs

This document defines the deterministic state-transition rules, evaluation pipeline, and state-combination laws for the Veraxis Execution Integrity Protocol (VEIP) reference engine implementation (`veip-core` version `0.1.0`).

### 1.1 Normative Dependencies
This specification strictly depends upon and complies with the following frozen v0.1 artifacts:
1. **`VEIP_CORE_INTERFACE_CONTRACT_v0.1`**: Core API surface, type definitions, and structural invariants.
2. **`VEIP_CORE_SCHEMA_v0.1.json`**: Structural JSON schema validation for requests, evidence packs, evaluation contexts, and responses.
3. **`VEIP_REASON_CODE_REGISTRY_v0.1.json`**: Registry of all 13 core reason codes, phase assignments, and parameter bindings.
4. **Engine Version**: `0.1.0` (Strict match enforced).

### 1.2 Non-Interference Invariant
This document introduces **zero** new reason codes, product features, schema properties, or evidence primitives. It governs *only* the deterministic evaluation of schema-valid inputs against the frozen registry.

### 1.3 Structural Error Separation
Any structural or cryptographic invariant violation occurring prior to or during input ingestion causes the engine to throw an **`EngineError`** immediately. Structural invalidity **must never** result in semantic adjudication (e.g., setting a dimension to `NOT_ESTABLISHED`). Adjudication occurs strictly on valid input structures.

### 1.4 Normative Registry Errata
- **0.1-E1 (Target Path Alignment)**: The parameter bindings in `VEIP_REASON_CODE_REGISTRY_v0.1.json` for reason code `RECEIPT_WRONG_SUBJECT_OR_EXTENT` reference `request.target.subject_ref` and `request.target.extent_ref`. Because the root request schemas expose targets as `assertion` (for Claims) or `requested_outcome` (for Completions), engine implementations MUST resolve `request.target` against the internal `evaluation_target` projection defined in Section 2.2.
- **0.1-E2 (Active Code Profile Reachability)**: Reason code `EVIDENCE_STALE` retains `emission_status = ACTIVE` in `VEIP_REASON_CODE_REGISTRY_v0.1.json`. However, generic pure core v0.1 contains no typed `CurrentnessRule` applicability relation. Therefore `EVIDENCE_STALE` is conditionally unreachable in the generic profile and MUST NOT be emitted unless a future compatible profile supplies an externally declared typed applicability relation.
*(These errata clarify semantic execution without mutating frozen registry JSON bytes).*

---

## 2. Ingestion, Topology & Manifest Verification Pipeline

Prior to executing evaluation phases, the engine executes five sequential, non-adjudicative validation steps on a single root request object matching strictly either `$defs/ClaimEvaluationRequest` or `$defs/CompletionEvaluationRequest`.

```
+-----------------------------------------------------------------------+
|                         Root Input Processing                         |
|      (Single ClaimEvaluationRequest or CompletionEvaluationRequest)    |
+-----------------------------------------------------------------------+
                                    |
                                    v
+-----------------------------------------------------------------------+
| 1. Schema Ingestion Validation                                        |
|    Verify Root Request against VEIP_CORE_SCHEMA_v0.1.json             |
|    Require ClaimEvaluationRequest or CompletionEvaluationRequest      |
|    Failure -> EngineError.SCHEMA_INVALID                              |
+-----------------------------------------------------------------------+
                                    |
                                    v
+-----------------------------------------------------------------------+
| 2. Expected Engine Version Match                                      |
|    If expected_engine_version present, verify == "0.1.0"              |
|    Failure -> EngineError.ENGINE_VERSION_MISMATCH                     |
+-----------------------------------------------------------------------+
                                    |
                                    v
+-----------------------------------------------------------------------+
| 3. Evidence ID Uniqueness Check                                       |
|    Verify all evidence_id values in request.evidence_pack are unique  |
|    Failure -> EngineError.DUPLICATE_EVIDENCE_ID                       |
+-----------------------------------------------------------------------+
                                    |
                                    v
+-----------------------------------------------------------------------+
| 4. Deterministic Manifest Verification                                |
|    Verify manifest_sha256 against JCS-canonicalized reference vector  |
|    Failure -> EngineError.MANIFEST_HASH_MISMATCH                      |
+-----------------------------------------------------------------------+
                                    |
                                    v
+-----------------------------------------------------------------------+
| 5. Internal Projections & Relevant Evidence Set Construction          |
|    Construct evaluation_target & filter relevant evidence refs         |
+-----------------------------------------------------------------------+
                                    |
                                    v
+-----------------------------------------------------------------------+
|                     Evaluation Engine Phase 10                        |
+-----------------------------------------------------------------------+
```

### 2.1 Schema Ingestion & Entry-Point Restriction
- **Schema Validation**: Verify root `request` object against `VEIP_CORE_SCHEMA_v0.1.json`.
- **Entry-Point Enforcement**: The `adjudicate()` entry point accepts strictly `$defs/ClaimEvaluationRequest` or `$defs/CompletionEvaluationRequest`. Passing any other schema-valid root structure (such as `ExplanationRequest` or `ClaimEvaluationResult`) throws `EngineError.SCHEMA_INVALID`.
- **Expected Version Verification**: If `request.expected_engine_version` is present, verify `request.expected_engine_version == "0.1.0"`. On failure, throw `EngineError.ENGINE_VERSION_MISMATCH`. The engine always emits `"0.1.0"` in output result objects.

### 2.2 Internal Evaluation Target Projection
To harmonize target scope evaluation across request types without schema mutation, the engine constructs an internal `evaluation_target` object:
- **For `ClaimEvaluationRequest`**:
  `evaluation_target = { subject_ref: request.assertion.subject_ref, extent_ref: request.assertion.extent_ref }`
- **For `CompletionEvaluationRequest`**:
  `evaluation_target = { subject_ref: request.requested_outcome.subject_ref, extent_ref: request.requested_outcome.extent_ref }`

### 2.3 Evidence ID Uniqueness
Iterate over `request.evidence_pack.references`. If any `evidence_id` occurs more than once within the pack, throw `EngineError.DUPLICATE_EVIDENCE_ID`.

### 2.4 Deterministic Manifest Hash Verification
To verify `request.evidence_pack.manifest_sha256`, the engine executes the following algorithm:

1. Project each `EvidenceReference` item into a Canonical Manifest Item Object containing **only** these 9 schema fields (preserving original JSON types; omitting optional fields when absent):
   - `evidence_id` (string)
   - `payload_sha256` (string)
   - `source_type` (string)
   - `channel_ref` (string, optional)
   - `receipt` (object, optional)
   - `observed_at` (string, optional)
   - `subject_ref` (string, optional)
   - `extent_ref` (string, optional)
   - `run_id` (string, optional)
   *(Note: `payload` is explicitly excluded from the manifest object projection).*
2. Sort the list of projected objects in **lexicographically ascending order** by the `evidence_id` UTF-8 byte representation.
3. Serialize the sorted list using **RFC 8785 JSON Canonicalization Scheme (JCS)**.
4. Calculate the SHA-256 digest of the JCS byte array and encode as a lower-case hexadecimal string.
5. Compare with `request.evidence_pack.manifest_sha256`. If digests do not match byte-for-byte, throw `EngineError.MANIFEST_HASH_MISMATCH`.

### 2.5 Relevant Evidence Set & Role Mapping Construction
To prevent unreferenced evidence from improperly poisoning unrelated evaluation dimensions:
- **For `CompletionEvaluationRequest`**:
  - `ExecutionEvidenceSet` $E_{exec} = \{ e \in \text{references} \mid e.\text{evidence\_id} \in \text{request.execution\_evidence\_refs} \}$
  - `OutcomeEvidenceSet` $E_{out} = \{ e \in \text{references} \mid e.\text{evidence\_id} \in \text{request.outcome\_evidence\_refs} \}$
  - `RelevantEvidenceSet` $E_{rel} = E_{exec} \cup E_{out}$
  - Each item $e \in E_{rel}$ is assigned a role `evidence_role`:
    - `BOTH` if $e.\text{evidence\_id} \in \text{execution\_evidence\_refs}$ AND $e.\text{evidence\_id} \in \text{outcome\_evidence\_refs}$.
    - `EXECUTION` if $e.\text{evidence\_id} \in \text{execution\_evidence\_refs}$ only.
    - `OUTCOME` if $e.\text{evidence\_id} \in \text{outcome\_evidence\_refs}$ only.
- **For `ClaimEvaluationRequest`**:
  - Because v0.1 lacks a typed evidence-reference array for claims, $E_{rel} = \emptyset$. All evidence items in `evidence_pack` are unbound to the claim.

---

## 3. Evaluative Phase Pipeline & Structured Internal Records

The engine evaluates active rules across eight strictly ordered phases. Reason codes are **accumulated as structured internal evaluation records**:

$$\text{EvaluationRecord} = \{\text{code}, \text{evidence\_id} \mid \text{null}, \text{evidence\_role}: \text{EXECUTION} \mid \text{OUTCOME} \mid \text{BOTH} \mid \text{GLOBAL}\}$$

Processing does **not** short-circuit on code emission; all active checks in all phases run to completion.

### Phase 10: Evidence Identity & Digest
- **Prerequisites**: Ingestion and Manifest verification completed.
- **Active Checks**:
  1. *Subject/Extent Requirement Check*: For each evidence reference $e \in E_{rel}$, if `evaluation_target.subject_ref` is present and $e.\text{subject\_ref}$ is absent, OR if `evaluation_target.extent_ref` is present and $e.\text{extent\_ref}$ is absent: emit `MISSING_OBSERVATION_SUBJECT_OR_EXTENT` with `evidence_id = e.evidence_id` and `evidence_role = e.evidence_role`.
  2. *Payload Digest Check*: For each evidence reference $e \in E_{rel}$ where $e.\text{payload}$ is present: compute `calculated_hash = SHA-256(RFC8785_JCS(e.payload))`. If `calculated_hash != e.payload_sha256`: emit `EVIDENCE_DIGEST_MISMATCH` with `evidence_id = e.evidence_id` and `evidence_role = e.evidence_role`.
- **Digest Isolation Invariant**: Evidence items outside $E_{rel}$ are ignored during payload digest verification to prevent decoy evidence poisoning. If $e.\text{payload}$ is absent, digest verification is `UNAVAILABLE` for that item; `EVIDENCE_DIGEST_MISMATCH` **must not** be emitted.

### Phase 20: Replay & Reference Resolution
- **Prerequisites**: Phase 10 complete.
- **Active Checks**:
  1. *Replay Check*: If `request.evaluation_context.replay_snapshot` is present, for each evidence reference $e \in E_{rel}$ with $e.\text{receipt.nonce}$ present: if `nonce` exists in `replay_snapshot.observed_receipt_nonces`: emit `RECEIPT_REPLAYED` with `evidence_id = e.evidence_id` and `evidence_role = e.evidence_role`.
  2. *Reference Resolution Check* (Completion Requests Only): Collect all unresolved IDs:
     - $U_{exec} = \text{execution\_evidence\_refs} \setminus \text{pack.evidence\_ids}$
     - $U_{out} = \text{outcome\_evidence\_refs} \setminus \text{pack.evidence\_ids}$
     - For $id \in U_{exec} \cap U_{out}$: emit `EVIDENCE_REF_UNRESOLVED` with `evidence_id = id`, `evidence_role = BOTH`.
     - For $id \in U_{exec} \setminus U_{out}$: emit `EVIDENCE_REF_UNRESOLVED` with `evidence_id = id`, `evidence_role = EXECUTION`.
     - For $id \in U_{out} \setminus U_{exec}$: emit `EVIDENCE_REF_UNRESOLVED` with `evidence_id = id`, `evidence_role = OUTCOME`.
- **Replay Snapshot Absence**: If `replay_snapshot` is absent, replay verification is `UNAVAILABLE`. Do not emit `RECEIPT_REPLAYED`.

### Phase 30: Binding Mechanics
- **Prerequisites**: Phase 20 complete.
- **Active Checks**:
  1. *Scope Match Check*: For each $e \in E_{rel}$: if $e.\text{subject\_ref}$ is present and $e.\text{subject\_ref} \neq \text{evaluation\_target.subject\_ref}$, OR if $e.\text{extent\_ref}$ is present and $e.\text{extent\_ref} \neq \text{evaluation\_target.extent\_ref}$: emit `RECEIPT_WRONG_SUBJECT_OR_EXTENT` with `evidence_id = e.evidence_id` and `evidence_role = e.evidence_role`.
  2. *Receipt Run Identity Check*: `RECEIPT_RUN_MISMATCH` is `RESERVED_NOT_EMITTED` in pure core v0.1. Skip.

### Phase 40: Scope Registration
- **Prerequisites**: Phase 30 complete.
- **Active Checks**:
  1. *Extent Registration Check*: If `evaluation_target.extent_ref` is present AND `request.evaluation_context.scope_registry_snapshot` is present: if `evaluation_target.extent_ref` is not in `scope_registry_snapshot.active_extents`: emit `EXTENT_MATCHES_NOTHING` with `evidence_role = GLOBAL`.
- **Snapshot Absence**: If `scope_registry_snapshot` is absent, scope registration verification is `UNAVAILABLE`. Do not emit `EXTENT_MATCHES_NOTHING`.

### Phase 50: Currentness Validation
- **Prerequisites**: Phase 40 complete.
- **Active Checks**:
  1. Currentness rule applicability lacks a typed binding relation in core v0.1 schema. Skip active currentness checks; dimension evaluates strictly to `UNAVAILABLE` (per Erratum 0.1-E2).

### Phase 60: Provenance & Channels
- **Prerequisites**: Phase 50 complete.
- **Active Checks**:
  1. *Channel Bound Check*: For each $e \in E_{rel}$, if $e.\text{channel\_ref}$ is absent OR `request.evaluation_context.channel_warrant_snapshot` is absent: emit `CHANNEL_BINDING_NOT_ESTABLISHED` with `evidence_id = e.evidence_id` and `evidence_role = e.evidence_role`.
  2. *Warrant Listing Check*: For each $e \in E_{rel}$ where $e.\text{channel\_ref}$ is present AND `channel_warrant_snapshot` is present: if $e.\text{channel\_ref}$ is not found in `channel_warrant_snapshot.bound_channels`: emit `CHANNEL_NOT_LISTED_IN_WARRANT` with `evidence_id = e.evidence_id` and `evidence_role = e.evidence_role`.
  3. *Host Summary Check*: `HOST_SUMMARY_NOT_PROVENANCE_BOUND` is `RESERVED_NOT_EMITTED` in pure core v0.1. Skip.

### Phase 70: Outcome Verification
- **Prerequisites**: Phase 60 complete.
- **Active Checks**:
  1. `OUTCOME_NOT_OBSERVED` is `RESERVED_NOT_EMITTED` in pure core v0.1. Skip.

### Phase 100: Claim Ceiling & Channel Independence
- **Prerequisites**: Phase 70 complete.
- **Active Checks**:
  1. *Independence Ceiling*: Always emit `CHANNEL_INDEPENDENCE_NOT_ESTABLISHED` with `evidence_role = GLOBAL`. Pure core v0.1 does not evaluate institutional cross-channel independence.

---

## 4. Fundamental Dimension State Semantics

The engine derives seven dimension states using three mutually exclusive, non-overlapping evaluation outcomes.

### 4.1 Tri-State Definitions
1. **`UNAVAILABLE`**: The evaluator lacks the required input, snapshot, typed relation, or positive state ceiling to evaluate the dimension. Absence of evaluator context **must never** be coerced into a negative finding (`NOT_ESTABLISHED`).
2. **`NOT_ESTABLISHED`**: The required evaluative basis was present, but one or more active reason records bound to the relevant role prohibited establishing the dimension within declared scope.
3. **`ESTABLISHED_WITHIN_SCOPE`**: All required evaluative inputs were present, all active checks passed, no prohibiting reason code was emitted for that dimension, and the positive state ceiling permits promotion.

---

## 5. Explicit Role-Aware Dimension State Derivation Algorithm

To evaluate dimension states, the engine evaluates $R\_records$ against the specific prohibition sets and applicable roles for each primary dimension, and then applies dependency propagation for composite dimensions:

```python
def derive_dimensions_role_aware(R_records) -> dict:
    dimensions = {}
    
    # 1. claim_support
    R_claim = {"MISSING_OBSERVATION_SUBJECT_OR_EXTENT", "EVIDENCE_DIGEST_MISMATCH", "RECEIPT_WRONG_SUBJECT_OR_EXTENT", "EXTENT_MATCHES_NOTHING"}
    has_claim_prohibition = any(
        rec["code"] in R_claim and rec["evidence_role"] == "GLOBAL"
        for rec in R_records
    )
    dimensions["claim_support"] = "NOT_ESTABLISHED" if has_claim_prohibition else "UNAVAILABLE"
    
    # 2. execution
    R_exec = {"EVIDENCE_DIGEST_MISMATCH", "RECEIPT_REPLAYED", "EVIDENCE_REF_UNRESOLVED", "RECEIPT_WRONG_SUBJECT_OR_EXTENT"}
    has_exec_prohibition = any(
        rec["code"] in R_exec and rec["evidence_role"] in ("EXECUTION", "BOTH", "GLOBAL")
        for rec in R_records
    )
    dimensions["execution"] = "NOT_ESTABLISHED" if has_exec_prohibition else "UNAVAILABLE"
    
    # 3. outcome
    R_out = {"MISSING_OBSERVATION_SUBJECT_OR_EXTENT", "EVIDENCE_DIGEST_MISMATCH", "RECEIPT_REPLAYED", "EVIDENCE_REF_UNRESOLVED", "RECEIPT_WRONG_SUBJECT_OR_EXTENT", "EXTENT_MATCHES_NOTHING"}
    has_out_prohibition = any(
        rec["code"] in R_out and rec["evidence_role"] in ("OUTCOME", "BOTH", "GLOBAL")
        for rec in R_records
    )
    dimensions["outcome"] = "NOT_ESTABLISHED" if has_out_prohibition else "UNAVAILABLE"
    
    # 4. currentness
    R_curr = {"EVIDENCE_STALE"}
    has_curr_prohibition = any(
        rec["code"] in R_curr and rec["evidence_role"] in ("EXECUTION", "OUTCOME", "BOTH", "GLOBAL")
        for rec in R_records
    )
    dimensions["currentness"] = "NOT_ESTABLISHED" if has_curr_prohibition else "UNAVAILABLE"
    
    # 5. provenance_binding
    R_prov = {"EVIDENCE_DIGEST_MISMATCH", "CHANNEL_NOT_LISTED_IN_WARRANT", "CHANNEL_BINDING_NOT_ESTABLISHED"}
    has_prov_prohibition = any(
        rec["code"] in R_prov and rec["evidence_role"] in ("EXECUTION", "OUTCOME", "BOTH", "GLOBAL")
        for rec in R_records
    )
    dimensions["provenance_binding"] = "NOT_ESTABLISHED" if has_prov_prohibition else "UNAVAILABLE"
    
    # 6. channel_independence
    R_indep = {"CHANNEL_INDEPENDENCE_NOT_ESTABLISHED"}
    has_indep_prohibition = any(
        rec["code"] in R_indep and rec["evidence_role"] == "GLOBAL"
        for rec in R_records
    )
    dimensions["channel_independence"] = "NOT_ESTABLISHED" if has_indep_prohibition else "UNAVAILABLE"
    
    # 7. task_completion (Strict Dependency State Propagation Law)
    required_completion_dimensions = ("execution", "outcome", "currentness", "provenance_binding")
    has_completion_dependency_failure = any(
        dimensions[d] == "NOT_ESTABLISHED" for d in required_completion_dimensions
    )
    dimensions["task_completion"] = "NOT_ESTABLISHED" if has_completion_dependency_failure else "UNAVAILABLE"
    
    return dimensions
```

### 5.1 Dimension State Transition Matrix & Absolute Positive Ceilings

In generic pure core v0.1, because typed relations for evidence binding, claim predicates, outcomes, channel attestations, and currentness rule applicability are absent from the schema, **all positive dimension state ceilings are capped at `UNAVAILABLE`** (or `NOT_ESTABLISHED` when active prohibiting codes exist).

| Dimension | Prohibiting Reason Codes $R(D)$ | `ESTABLISHED_WITHIN_SCOPE` Condition | Core v0.1 Positive Ceiling |
| :--- | :--- | :--- | :--- |
| **`claim_support`** | `MISSING_OBSERVATION_SUBJECT_OR_EXTENT`, `EVIDENCE_DIGEST_MISMATCH`, `RECEIPT_WRONG_SUBJECT_OR_EXTENT`, `EXTENT_MATCHES_NOTHING` | Typed claim-predicate relation present AND no prohibiting code emitted. | **`UNAVAILABLE`** |
| **`execution`** | `EVIDENCE_DIGEST_MISMATCH`, `RECEIPT_REPLAYED`, `EVIDENCE_REF_UNRESOLVED`, `RECEIPT_WRONG_SUBJECT_OR_EXTENT` | Receipt identity does not attest execution occurred. | **`UNAVAILABLE`** or **`NOT_ESTABLISHED`** |
| **`outcome`** | `MISSING_OBSERVATION_SUBJECT_OR_EXTENT`, `EVIDENCE_DIGEST_MISMATCH`, `RECEIPT_REPLAYED`, `EVIDENCE_REF_UNRESOLVED`, `RECEIPT_WRONG_SUBJECT_OR_EXTENT`, `EXTENT_MATCHES_NOTHING` | Typed proposition relation present AND all outcome evidence verified. | **`UNAVAILABLE`** |
| **`currentness`** | `EVIDENCE_STALE` | Currentness applicability lacks typed binding schema in core v0.1. | **`UNAVAILABLE`** |
| **`provenance_binding`** | `EVIDENCE_DIGEST_MISMATCH`, `CHANNEL_NOT_LISTED_IN_WARRANT`, `CHANNEL_BINDING_NOT_ESTABLISHED` | Warrant listing does not equal cryptographic attestation. | **`UNAVAILABLE`** or **`NOT_ESTABLISHED`** |
| **`channel_independence`**| `CHANNEL_INDEPENDENCE_NOT_ESTABLISHED` | Institutional cross-channel warrants unintegrated in v0.1. | **`NOT_ESTABLISHED`** |
| **`task_completion`** | Inherited dependency failure from `execution`, `outcome`, `currentness`, or `provenance_binding`. | Requires `execution`, `outcome`, `currentness`, & `provenance_binding` == `ESTABLISHED`. | **`UNAVAILABLE`** |

---

## 6. Operational Mechanics: Resolution, Matching & Scope

### 6.1 Reference Resolution Semantics
- Both `request.execution_evidence_refs` and `request.outcome_evidence_refs` are resolved against `request.evidence_pack.references` by exact string match on `evidence_id`.
- Duplicate string IDs in request arrays trigger `EngineError.SCHEMA_INVALID` during schema validation (`uniqueItems: true`).
- Order of references is irrelevant.
- An `evidence_id` may safely appear in both execution and outcome reference lists.

### 6.2 Subject & Extent Exact-String Matching
All subject and extent comparisons (`evaluation_target`, `evidence`, `scope_registry_snapshot`) use exact UTF-8 byte string equality.
- No normalization, case-folding, wildcards, regex, or semantic expansion is performed in core v0.1.
- `evaluation_target.extent_ref` being absent is semantically distinct from `evidence.extent_ref` being absent. An extent check is enforced **only** if the evaluation target explicitly declares an `extent_ref`.

---

## 7. Explicit Non-Capabilities & Disambiguation

To preserve audit integrity, `veip-core` v0.1 explicitly excludes the following capabilities:

1. **No Truth Discovery**: Core v0.1 evaluates structural and cryptographic integrity. It does not determine real-world factual truth.
2. **No Heuristic Inference**: Core v0.1 never inspects unformatted text in `payload` to infer outcome or claim success.
3. **Execution $\neq$ Outcome $\neq$ Completion**: Verification of execution receipts **never** automatically promotes `outcome` or `task_completion` to `ESTABLISHED_WITHIN_SCOPE`.
4. **No Snapshot Mutation**: Core v0.1 is a pure function. It never mutates replay snapshots, registries, or warrants.
5. **No Network/I/O**: Core v0.1 operates strictly on in-memory serialized structures.

---

## 8. Reserved Reason Codes

The following reason codes are defined in `VEIP_REASON_CODE_REGISTRY_v0.1.json` with status `RESERVED_NOT_EMITTED`. They **must never** be emitted by `veip-core` v0.1 under any input conditions:

1. `RECEIPT_RUN_MISMATCH`
2. `HOST_SUMMARY_NOT_PROVENANCE_BOUND`
3. `OUTCOME_NOT_OBSERVED`

If an engine execution emits any of these three codes, the implementation is non-compliant.

---

## 9. Reliance Projection & Result Output Construction

### 9.1 Requested Dimension Key Mapping Table (`REQUESTED_DIMENSION_MAP`)
The upper-case `RequestedDimension` enum values in `reliance_context.requested_dimension` map strictly to lower-case `DimensionsMap` keys via the normative lookup table:

```
REQUESTED_DIMENSION_MAP = {
  "CLAIM_SUPPORT":   "claim_support",
  "OUTCOME":         "outcome",
  "CURRENTNESS":     "currentness",
  "TASK_COMPLETION": "task_completion"
}
```

Attempting to request `EXECUTION`, `PROVENANCE_BINDING`, or `CHANNEL_INDEPENDENCE` is rejected at schema ingestion (`EngineError.SCHEMA_INVALID`).

### 9.2 Reliance Projection Mapping
The `RelianceProjection` is derived mechanically from the calculated dimension map:

```
dimension_key = REQUESTED_DIMENSION_MAP[request.reliance_context.requested_dimension]

RelianceProjection = {
  "requested_dimension": request.reliance_context.requested_dimension,
  "state": dimensions[dimension_key]
}
```

No full dimension map belongs inside `reliance_projection`. No scalar score aggregation or business logic is performed.

### 9.3 Result Object Construction
Depending on the root request schema type, the engine constructs the corresponding result object:
- **For `ClaimEvaluationRequest`**: Constructs `ClaimEvaluationResult` containing `engine_version = "0.1.0"`, `claim_id = request.claim_id`, `reliance_projection`, `dimensions`, `reason_codes`, and `canonical_hash`.
- **For `CompletionEvaluationRequest`**: Constructs `CompletionEvaluationResult` containing `engine_version = "0.1.0"`, `request_id = request.request_id`, `reliance_projection`, `dimensions`, `reason_codes`, and `canonical_hash`.

### 9.4 Canonical Hash Calculation
The `canonical_hash` field for both result objects is calculated as:
$$\text{canonical\_hash} = \text{SHA-256}\Big(\text{RFC8785\_JCS}\big(\text{Result Object sans } \texttt{canonical\_hash}\big)\Big)$$

### 9.5 Reason Code Array Flattening & Sorting
Strictly *after* dimension states are computed using structured `EvaluationRecord` objects:
1. Extract unique reason code string names from $R\_records$.
2. Sort the unique array in **lexicographically ascending ASCII order**.

---

## 10. Deterministic Explanation Function (`explain_boundary`)

The `explain_boundary()` entry point accepts strictly `$defs/ExplanationRequest` and produces a deterministic `BoundaryExplanationResult`:

1. **Input & Version Validation**: Validate `request_json` against `$defs/ExplanationRequest`. If `request.expected_engine_version` is present and `!= "0.1.0"`, throw `EngineError.ENGINE_VERSION_MISMATCH`.
2. **Verbosity Compatibility Semantics**: All enum values for `verbosity_level` (`SUMMARY`, `DETAILED`, `FULL_AUDIT`) are accepted and valid. In pure core v0.1, the `verbosity_level` parameter is a reserved compatibility field and MUST NOT alter semantic content, reason code selection, breakdown formatting, or adjudication results.
3. **Canonical Hash & Ordering Verification**:
   - Verify `adjudication_target.canonical_hash` by independently recomputing:
     $$\text{computed\_hash} = \text{SHA-256}\Big(\text{RFC8785\_JCS}\big(\text{adjudication\_target sans canonical\_hash}\big)\Big)$$
     If `computed_hash != adjudication_target.canonical_hash`, throw `EngineError.SCHEMA_INVALID`.
   - Verify that `adjudication_target.reason_codes` matches its lexicographically sorted vector (`adjudication_target.reason_codes == sorted(adjudication_target.reason_codes)`). If reason codes are unsorted, throw `EngineError.SCHEMA_INVALID`.
4. **Code Breakdown Generation**: For each code $c$ in `adjudication_target.reason_codes` (in sorted order):
   - `description` = `registry[c].summary`
   - `dimension_impact` = `registry[c].affected_dimensions` sorted lexicographically and joined with `","` (e.g., `"execution,outcome,task_completion"`).
   - Construct `CodeBreakdownItem = { code: c, description: description, dimension_impact: dimension_impact }`.
5. **Top-Level Summary Construction**:
   - If `reason_codes` is empty: `summary = "No reason codes emitted."`
   - Else: `summary` = array of `description` strings joined by a single space `" "`.
6. **Result Emission**:
   ```
   BoundaryExplanationResult = {
     "engine_version": "0.1.0",
     "target_canonical_hash": adjudication_target.canonical_hash,
     "summary": summary,
     "code_breakdown": code_breakdown_list
   }
   ```

---

## 11. Determinism Invariant & Executable Pseudocode

### 11.1 Determinism Invariant
> **Invariant**: Given byte-identical schema-valid input (`ClaimEvaluationRequest` or `CompletionEvaluationRequest`), identical engine version (`0.1.0`), and frozen registry files, `veip-core` v0.1 **MUST** produce byte-identical JSON outputs, identical reason code arrays, and identical `canonical_hash` digests across all runtime platforms and implementations.

### 11.2 Executable Pipeline Pseudocode

```python
REQUESTED_DIMENSION_MAP = {
    "CLAIM_SUPPORT":   "claim_support",
    "OUTCOME":         "outcome",
    "CURRENTNESS":     "currentness",
    "TASK_COMPLETION": "task_completion"
}

def adjudicate(request_json) -> dict:
    # Step 1: Ingestion & Strict Entry-Point Validation
    request, schema_type = validate_schema(request_json, "VEIP_CORE_SCHEMA_v0.1.json")
    if schema_type not in ("ClaimEvaluationRequest", "CompletionEvaluationRequest"):
        raise EngineError.SCHEMA_INVALID("Entry point accepts only Claim or Completion evaluation requests")
        
    if request.get("expected_engine_version") and request["expected_engine_version"] != "0.1.0":
        raise EngineError.ENGINE_VERSION_MISMATCH("Expected engine version must be 0.1.0")
        
    pack = request["evidence_pack"]
    context = request["evaluation_context"]
    
    # Step 2: Uniqueness & Manifest Verification
    evidence_ids = [ref["evidence_id"] for ref in pack["references"]]
    if len(evidence_ids) != len(set(evidence_ids)):
        raise EngineError.DUPLICATE_EVIDENCE_ID("Duplicate evidence_id detected")
        
    verify_manifest_hash(pack) # Throws EngineError.MANIFEST_HASH_MISMATCH on failure
    
    # Step 3: Target Projection & Relevant Evidence Roles
    is_completion = (schema_type == "CompletionEvaluationRequest")
    if is_completion:
        target = {
            "subject_ref": request["requested_outcome"]["subject_ref"],
            "extent_ref": request["requested_outcome"].get("extent_ref")
        }
        exec_refs = set(request["execution_evidence_refs"])
        out_refs = set(request["outcome_evidence_refs"])
        rel_ids = exec_refs | out_refs
        
        E_rel_map = {}
        for ref in pack["references"]:
            eid = ref["evidence_id"]
            if eid in rel_ids:
                in_exec = eid in exec_refs
                in_out = eid in out_refs
                role = "BOTH" if (in_exec and in_out) else ("EXECUTION" if in_exec else "OUTCOME")
                E_rel_map[eid] = (ref, role)
    else:
        target = {
            "subject_ref": request["assertion"]["subject_ref"],
            "extent_ref": request["assertion"].get("extent_ref")
        }
        E_rel_map = {} # No typed evidence binding for claims in v0.1
        
    # Step 4: Phase Evaluation Pipeline (Role-Aware Records)
    R_records = [] # List of dicts: { "code": str, "evidence_id": str|None, "evidence_role": str }
    
    # Phase 10: Identity & Digest (Strictly on E_rel)
    for eid, (ref, role) in E_rel_map.items():
        if target["subject_ref"] and not ref.get("subject_ref"):
            R_records.append({"code": "MISSING_OBSERVATION_SUBJECT_OR_EXTENT", "evidence_id": eid, "evidence_role": role})
        if target["extent_ref"] and not ref.get("extent_ref"):
            R_records.append({"code": "MISSING_OBSERVATION_SUBJECT_OR_EXTENT", "evidence_id": eid, "evidence_role": role})
        if ref.get("payload") is not None:
            computed_sha = sha256(rfc8785_jcs(ref["payload"]))
            if computed_sha != ref["payload_sha256"]:
                R_records.append({"code": "EVIDENCE_DIGEST_MISMATCH", "evidence_id": eid, "evidence_role": role})
                
    # Phase 20: Replay & Reference Resolution
    if context.get("replay_snapshot") is not None:
        observed_nonces = set(context["replay_snapshot"]["observed_receipt_nonces"])
        for eid, (ref, role) in E_rel_map.items():
            if ref.get("receipt") and ref["receipt"]["nonce"] in observed_nonces:
                R_records.append({"code": "RECEIPT_REPLAYED", "evidence_id": eid, "evidence_role": role})
                
    if is_completion:
        pack_ref_ids = set(evidence_ids)
        u_exec = exec_refs - pack_ref_ids
        u_out = out_refs - pack_ref_ids
        for uid in (u_exec | u_out):
            in_exec = uid in u_exec
            in_out = uid in u_out
            role = "BOTH" if (in_exec and in_out) else ("EXECUTION" if in_exec else "OUTCOME")
            R_records.append({"code": "EVIDENCE_REF_UNRESOLVED", "evidence_id": uid, "evidence_role": role})
                
    # Phase 30: Binding Mechanics
    for eid, (ref, role) in E_rel_map.items():
        if ref.get("subject_ref") and ref["subject_ref"] != target["subject_ref"]:
            R_records.append({"code": "RECEIPT_WRONG_SUBJECT_OR_EXTENT", "evidence_id": eid, "evidence_role": role})
        if ref.get("extent_ref") and ref["extent_ref"] != target["extent_ref"]:
            R_records.append({"code": "RECEIPT_WRONG_SUBJECT_OR_EXTENT", "evidence_id": eid, "evidence_role": role})
            
    # Phase 40: Scope Registration
    if target["extent_ref"] and context.get("scope_registry_snapshot") is not None:
        if target["extent_ref"] not in context["scope_registry_snapshot"]["active_extents"]:
            R_records.append({"code": "EXTENT_MATCHES_NOTHING", "evidence_id": None, "evidence_role": "GLOBAL"})
            
    # Phase 60: Provenance & Channels
    warrant_snap = context.get("channel_warrant_snapshot")
    for eid, (ref, role) in E_rel_map.items():
        if not ref.get("channel_ref") or warrant_snap is None:
            R_records.append({"code": "CHANNEL_BINDING_NOT_ESTABLISHED", "evidence_id": eid, "evidence_role": role})
        elif ref["channel_ref"] not in warrant_snap["bound_channels"]:
            R_records.append({"code": "CHANNEL_NOT_LISTED_IN_WARRANT", "evidence_id": eid, "evidence_role": role})
            
    # Phase 100: Claim Ceiling & Channel Independence
    R_records.append({"code": "CHANNEL_INDEPENDENCE_NOT_ESTABLISHED", "evidence_id": None, "evidence_role": "GLOBAL"})
    
    # Step 5: Explicit Role-Aware Dimension Derivation
    dimensions = derive_dimensions_role_aware(R_records)
    
    req_dim = request["reliance_context"]["requested_dimension"]
    dim_key = REQUESTED_DIMENSION_MAP[req_dim]
    reliance_projection = {
        "requested_dimension": req_dim,
        "state": dimensions[dim_key]
    }
    
    # Step 6: Flatten Reason Codes & Construct Result
    relevant_codes = {rec["code"] for rec in R_records}
    sorted_reason_codes = sorted(list(relevant_codes))
    
    result = {
        "engine_version": "0.1.0",
        "reliance_projection": reliance_projection,
        "dimensions": dimensions,
        "reason_codes": sorted_reason_codes
    }
    if is_completion:
        result["request_id"] = request["request_id"]
    else:
        result["claim_id"] = request["claim_id"]
        
    result["canonical_hash"] = sha256(rfc8785_jcs(result))
    return result

def explain_boundary(request_json) -> dict:
    request, schema_type = validate_schema(request_json, "VEIP_CORE_SCHEMA_v0.1.json")
    if schema_type != "ExplanationRequest":
        raise EngineError.SCHEMA_INVALID("Entry point accepts only ExplanationRequest")
        
    if request.get("expected_engine_version") and request["expected_engine_version"] != "0.1.0":
        raise EngineError.ENGINE_VERSION_MISMATCH("Expected engine version must be 0.1.0")
        
    target = request["adjudication_target"]
    
    # Canonical Hash Verification
    computed_hash = sha256(rfc8785_jcs(target_sans_hash(target)))
    if computed_hash != target["canonical_hash"]:
        raise EngineError.SCHEMA_INVALID("Target canonical_hash mismatch")
        
    # Sorted Reason Codes Verification
    if target["reason_codes"] != sorted(target["reason_codes"]):
        raise EngineError.SCHEMA_INVALID("Target reason_codes are not canonically sorted")
        
    registry = load_registry("VEIP_REASON_CODE_REGISTRY_v0.1.json")
    
    code_breakdown = []
    descriptions = []
    for code in target["reason_codes"]:
        desc = registry[code]["summary"]
        impact = ",".join(sorted(registry[code]["affected_dimensions"]))
        code_breakdown.append({
            "code": code,
            "description": desc,
            "dimension_impact": impact
        })
        descriptions.append(desc)
        
    summary = " ".join(descriptions) if descriptions else "No reason codes emitted."
    
    return {
        "engine_version": "0.1.0",
        "target_canonical_hash": target["canonical_hash"],
        "summary": summary,
        "code_breakdown": code_breakdown
    }
```
