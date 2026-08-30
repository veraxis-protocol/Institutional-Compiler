# Admission Runtime Freeze 001

**Authorization:** OWNER-AUTHORIZED BOUNDED ADMISSION RUNTIME FREEZE — PRE-INSTITUTIONAL-IR

**Freeze state:** `FROZEN FOR INSTITUTIONAL-IR SUCCESSOR WORK`

**Frozen final state:** `ae6021496e5f87e5aaf7a6a52514dc86538987e9`

This freeze sits beside `candidate-layer-freeze-001/` so the repository's freeze records
are discoverable in one place. Like that one, it is a receipt about a past state, not a
characterization run: no model was called and no live evidence was collected.

## Chronology

| SHA | What it is |
| --- | --- |
| `9fa2c684841ea89632bfe0129f98177761d85d12` | Starting state. Admission Boundary 001 executable input contract closure — design only, no runtime. |
| `ddc8c7ddee72cd0b3fc2ffe5c878ab7e550630ca` | **Admission Runtime 001 evaluator implementation.** |
| `ae6021496e5f87e5aaf7a6a52514dc86538987e9` | Subsequent historical scope-binding test repair, and the branch tip. **The complete final state frozen here.** |

The second commit is the evaluator. The third is the later scope-binding test repair that
followed it; the freeze covers the state as it stands at that tip.

## What was frozen

The Admission Runtime 001 artifacts, and only those:

* `src/oic/admission.py`
* `src/oic/admission_specs/` — byte-identical runtime copies of the four governing
  frozen specifications, plus the package marker
* the `pyproject.toml` package-data declaration that puts those resources in the wheel
* the governing runtime tests, referenced as evidence by digest

This freeze is **not** an assertion that unrelated future OIC modules under `src/` may
never change. Candidate Layer Freeze 001 originally carried an assertion of that shape,
read against `HEAD`; that was corrected before this freeze was written, and the mistake is
deliberately not repeated here.

## The seam

```
evaluate_admission_bytes(input_bytes: bytes) -> AdmissionReceipt
```

The parameter is bytes and not a parsed object on purpose. Encoding, duplicate keys,
canonical form, schema conformance, evidence ordering, evidence integrity and the ruleset
binding are all properties of the bytes. A caller handed an object entry point could skip
every one of them, so no object entry point is exported.

Two failure classes stay apart:

* **Input-boundary failure** → `AdmissionInputBoundaryError`. Nothing was evaluated, so
  there is no terminal state and no receipt. It is never converted into
  `ADMISSION_NOT_ESTABLISHED`: turning a parse failure into an admission outcome would
  manufacture institutional evidence out of it.
* **Admissible input** → exactly one terminal state and one immutable receipt.

An unexpected internal defect raises `AdmissionEvaluationError` and never becomes a valid
institutional receipt either.

## Frozen identity

| | |
| --- | --- |
| `evaluator_id` | `oic-admission-reference-evaluator` |
| `evaluator_version` | `0.1-preregistered` |
| `ruleset_id` | `OIC-ADMISSION-BOUNDARY-001` |
| ruleset canonical digest | `sha256:794ff36a702964ef32b3bc7b68cc9286e06665e20744975db5f4ef692e685b6c` |
| canonicalization | `OIC-ADMISSION-CANONICAL-JSON-v0.1` |
| receipt id prefix | `admrec-sha256:` |

The ruleset digest is taken over **Canonical JSON of the parsed mapping**, not over the
file. The raw file digest is `9ed244f0…` and is not the attested value. Confusing the two
is the single easiest way to build an evaluator that looks right and attests the wrong
ruleset, so both are recorded.

## Evidence

| Property | Result |
| --- | --- |
| Frozen executable vectors, through the public byte boundary | **38/38 exact** |
| Exactness | state, reason code, every digest projection, and receipt ID |
| Terminal states exercised | **15/15** |
| Precedence diagnostics | **8/8**, first-terminal-state-wins |
| Byte-boundary rejection cases | **36** |
| Named implementation mutations killed | **24/24**, with a control proving the killer is not vacuous |
| Behavioral probe bank | 33 cases, all satisfied |
| Deterministic receipt construction | yes; idempotent over repeated identical bytes |
| Wall clock | none — the module imports no clock, asserted structurally over the parsed AST |
| Model | none |
| Network schema resolution | none — local registry, no retrieve callback |
| Runtime configuration able to reorder states or change the ruleset | none |
| Installed-wheel execution with no `design/` tree | proven, on one ADMITTED and one fail-closed vector |
| Dependency added | none |

## Frozen invariants

The complete list is in `FREEZE.json`. The load-bearing ones:

1. The public entry point consumes bytes, so the byte seam cannot be bypassed.
2. An input-boundary failure is never a terminal state.
3. Precedence is read from the packaged ruleset; the module refuses to load if its own
   declared state order disagrees with it.
4. No caller-selected ruleset is accepted.
5. Time enters only through `evaluation_time`. Intervals are half-open.
6. Evidence order is verified, never imposed.
7. `CONFLICTING_AUTHORITY` is emitted whenever two or more operative authority bases
   cover one evaluation, because the frozen ruleset carries no institutional precedence
   rule. Recency, order, rank and version never pick a winner.
8. No authority arises from candidate text, `unit_type`, model output, source metadata,
   defaults, environment or configuration. **No default authority exists.**
9. The vocabulary contains no runtime permission state. `ADMITTED` means eligible for
   Institutional IR interpretation, and nothing else.

## Successor boundary

Only an `AdmissionReceipt` whose `admission_state` is `ADMITTED` may cross into
Institutional IR construction, carrying the unchanged Candidate Normative Unit, its source
anchors, and the authority-evidence references and digests needed for reconstruction.

**Admission established eligibility for interpretation. It did not establish the
interpretation.**

## SBOM environment note

`scripts/generate_sbom.sh` could not be run locally because `cyclonedx-py` was absent from
the local environment.

**ENVIRONMENTAL / NONBLOCKING / NO DEPENDENCY CHANGE.** No SBOM was generated under this
freeze, and none is claimed. No dependency was installed or modified to close the note.

## Future change rule

Any change to Admission Runtime 001 behavior requires a demonstrated defect, a bounded
successor work order, explicit owner authorization, preservation of this freeze record,
and a versioned successor rather than silent mutation.

## Known limitations

See `FREEZE.json`. In short: the evidence is bounded to 38 synthetic executable vectors,
33 probes and 24 mutations; it is not a population error rate. The evaluator performs no
PKI, issuer authentication, or institutional mandate validation. Issuer authentication,
freshness duration, authority hierarchy and conflict-resolution governance remain
unresolved and require separate owner authorization.

## Claim ceiling

This bounded freeze records the first deterministic Admission Boundary 001 reference
evaluator and the identified executable evidence. It does not establish legal validity,
universal authority semantics, production authority validation, issuer authentication,
semantic correctness, institutional meaning, Institutional IR, successful IR compilation,
execution authorization, runtime safety, compliance, production readiness, or independent
validation.

`independent_validation_claim = FALSE`

`NOT SELF-ADJUDICATED`

**NO INSTITUTIONAL IR WAS IMPLEMENTED.**
