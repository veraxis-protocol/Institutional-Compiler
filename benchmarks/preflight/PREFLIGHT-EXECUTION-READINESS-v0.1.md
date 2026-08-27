# OIC-Bench Preflight Execution Readiness v0.1

Status: preparation only. Semantic OIC-Bench has not been run. This document
does not authorize source interpretation, admission, OCE generation, Rego
generation, or runtime semantic evaluation.

| Readiness area | Current state | Required before execution | Expected evidence/failure behavior |
|---|---|---|---|
| Frozen governing-source inventory | INCOMPLETE | Owner-selected minimum source roles; complete manifest and freeze | Missing source evidence blocks ingestion |
| Manifest completeness | INCOMPLETE / exit 3 | Every selected source has rights, provenance, hash, dates and authority status | Exit 3 remains missing evidence, never pass |
| Annotation/gold prerequisites | NOT STARTED | Schema, annotator roles, adjudication procedure, disagreements and immutable gold version | No fake labels or model-generated gold |
| Metric implementation | PROPOSED / NOT MEASURED | Freeze metric definitions and deterministic calculators | Invalid/undefined denominators fail closed |
| Benchmark lineage | PARTIAL | Bind source, annotation, compiler, schema, model, admission and test versions | Every raw result traces to exact inputs |
| Baseline harness | NOT STARTED | Direct LLM-to-Rego and other selected baselines use same inputs/model where required | No comparative claim from missing baseline |
| Environment capture | INFRASTRUCTURE READY | Lock files, tool versions, offline/network declaration, seeds and hardware/runtime metadata | Environment drift is reported |
| Raw-result destinations | NOT ESTABLISHED | Versioned machine-readable raw outputs, logs, hashes and failure inventory | Never publish only summaries |
| Reproducibility commands | PARTIAL | One clean command per stage plus expected exit codes | Non-zero/INCOMPLETE states retained |
| Source-version/change-impact cases | NOT STARTED | At least three authorized version/amendment pairs for preflight | Missing affected-control evidence is visible |
| Runtime transaction cases | NOT STARTED | At least 20 adjudicated positive, negative, boundary and unknown cases | `CANNOT`/escalation can be correct |
| Ambiguity/conflict cases | NOT STARTED | At least six gold blocking ambiguity/conflict/missing-authority cases | False resolution is a failure |
| Malicious/adversarial sources | NOT STARTED | At least one malicious instruction plus negation, threshold, time, actor and exception mutations | Source instructions cannot alter authority |
| Claim ceiling | ESTABLISHED | Preserve preflight ≠ full OIC-Bench | No generalization, enterprise proof, superiority or maturity claim |

## Immediate post-gate sequence

1. Verify the selected frozen-source manifest; stop on `INCOMPLETE`.
2. Freeze annotation protocol and gold roles before semantic output is scored.
3. Capture the exact environment and all dependency/model versions.
4. Run semantic stages only under the separately authorized bounded profile.
5. Store raw outputs, refusals, errors, lineage and hashes.
6. Run preregistered preflight metrics and named baselines without changing
   thresholds after observing results.
7. Publish failures and limitations with any bounded experimental result.

Preflight evidence is not full OIC-Bench v0.1 and cannot establish statistical
generalization, enterprise suitability, comparative superiority, or product
maturity.
