# OIC-CANDIDATE-SEMANTICS-001 — candidate semantic characterization

A frozen synthetic corpus and an offline-testable harness for measuring how OIC candidate
extraction behaves *before* any admission layer exists. This directory produces evidence.
It decides nothing.

## What this is not

Running this corpus does not establish semantic correctness, institutional admission,
authority, enforceability, runtime authorization, production readiness, regulatory
compliance, superiority, or independent validation. `independent_validation_claim` is
`false` in the corpus and in every receipt the harness writes.

The strongest statement a completed run supports is:

> Candidate extraction behavior has been characterized on the frozen
> OIC-CANDIDATE-SEMANTICS-001 synthetic corpus under the identified implementation commit,
> model, provider, and run conditions.

Every specimen is invented for testing. None describes a real institution, policy, or
obligation, and no specimen is authoritative for anything.

## Characterization, not correction

If a run exposes a missed norm, a false positive, an unstable decomposition, an unexpected
unit type, or a threshold in a surprising field, that observation is the deliverable.
Nothing here repairs it:

* the harness never reaches around `propose_candidate_units`, so the unit of measurement
  is the candidate that survived the existing boundary;
* a response the boundary refuses is recorded with its error, never retried or patched;
* `mandate` is never mapped onto `obligation`, and two different decompositions are never
  canonicalized into agreement;
* the harness never prescribes where a numeric threshold belongs — it only records where
  the threshold text was found.

Correcting anything the evidence reveals requires a separate owner-authorized work order.

## Files

| Path | What it is |
|---|---|
| `CORPUS-v0.1.json` | The 32 frozen specimens. Immutable input. |
| `CORPUS-FREEZE-v0.1.json` | Digest, specimen count, ids, and per-specimen source digests. |
| `../../../scripts/characterize_candidate_semantics.py` | The harness and its CLI. |
| `../../../tests/unit/test_characterize_candidate_semantics.py` | Offline harness tests, fake providers only. |
| `../../../tests/contract/test_candidate_semantics_corpus.py` | Corpus freeze and coverage contracts. |

Receipts are written outside the tree by default, under `.local/`, so a live run never
commits its own results by accident.

## Corpus coverage

32 specimens across 30 required categories: one specimen for each normative form
(obligation, prohibition, permission, delegation, mandate, definition, power, condition,
threshold, exception, evidence duty, review duty, escalation, remedy, temporal trigger,
discretion, advisory), five negative controls carrying no normative proposition, a
multi-norm fragment, a condition-plus-exception fragment, an ambiguous `may`, and two
families:

* **`CFO-10K-STANDING`** — the same norm under five standing conditions: undisclaimed,
  `DRAFT`, `NOT AN AUTHORITATIVE POLICY`, hypothetical, and provenance-unverified. This is
  the direct test of the architectural requirement that candidate extraction not depend on
  whether a source is authoritative. `CSEM-022` is the exact fragment the work order
  recorded a live result for.
* **`CFO-10K-PARAPHRASE`** — the same norm in three materially different phrasings. The
  fixture states an *intent* that these are equivalent; it does not establish that they
  are, and agreement between them is not correctness.

`CSEM-027` is the baseline of both families.

## Running it

Live runs need an NVIDIA credential. It is read from the environment by the existing
adapter and is never read, printed, hashed, or written into a receipt by this harness.

```sh
export NVIDIA_API_KEY=...          # local environment only; never commit this
python scripts/characterize_candidate_semantics.py \
  --corpus benchmarks/characterization/candidate-semantics-001/CORPUS-v0.1.json \
  --freeze benchmarks/characterization/candidate-semantics-001/CORPUS-FREEZE-v0.1.json \
  --runs-per-specimen 3 \
  --model nvidia/nemotron-3.5-lightning-30b-a3b \
  --output .local/candidate-semantics-receipts/OIC-CANDIDATE-SEMANTICS-001.json
```

That is 32 specimens x 3 runs = 96 requests. Three runs per specimen is an initial
stability probe, not a statistically sufficient sample, and the receipt says so.

The harness recomputes the corpus digest before every run and **refuses to start** if it
disagrees with `CORPUS-FREEZE-v0.1.json`. `--allow-corpus-drift` proceeds anyway, stamps
the receipt `DRIFT_ACKNOWLEDGED`, and records every finding. Re-freezing is a deliberate
act, not something a run does to itself.

The unit and contract suites need no credential and no network.

## Metrics

| | Metric | What it counts |
|---|---|---|
| A | Boundary acceptance | Responses that survived the existing candidate boundary. Provider transport errors are counted separately and are not boundary rejections. |
| B | Normative presence | For positive specimens, accepted runs returning at least the declared minimum. An engineering presence count, not normative correctness. |
| C | Negative controls | For negative specimens, accepted runs returning any candidate at all. |
| D | Candidate count stability | Per-specimen count distribution across repeated runs. |
| E | Unit-type observation | Observed types and whether they fall inside the preregistered set. Nothing is remapped. |
| F | Semantic decomposition stability | Exact repeat stability of the canonical semantic projection. |
| G | Source-standing invariance | Whether standing language alone changed presence, count, type, or decomposition. |
| H | Paraphrase families | Agreement across phrasings the fixture intends as equivalent. |
| I | Threshold placement | Where threshold text actually appeared: object, conditions, both, another field, or nowhere. |
| J | Multi-unit behaviour | Whether independent norms came back separated or collapsed. |

The **semantic projection** is exactly `unit_type`, `actor`, `action`, `object`,
`conditions`, `exceptions`, `evidence_requirements`. It excludes `unit_id`,
`interpretation_state`, `epistemic_state`, and `source_anchors`, because those are set
deterministically by OIC: including them would measure OIC's determinism rather than the
model's stability. The projection hash is order-sensitive, so a reordered set of units
counts as a variant rather than a match.

## Result vocabulary

`STRUCTURAL_PASS`, `BOUNDARY_REJECTED`, `PROVIDER_ERROR`, `EXPECTED_PRESENCE_OBSERVED`,
`PRESENCE_MISS`, `EXPECTED_ABSENCE_OBSERVED`, `FALSE_POSITIVE_OBSERVED`,
`TYPE_WITHIN_PREREGISTERED_SET`, `TYPE_OUTSIDE_PREREGISTERED_SET`, `REPEAT_STABLE`,
`REPEAT_VARIANT`, `NOT_OBSERVED`.

The vocabulary deliberately excludes `ADMITTED`, `AUTHORIZED`, `COMPLIANT`,
`LEGALLY_VALID`, `CORRECT_POLICY`, `ALLOW`, and `DENY`. None of those is a thing this
stage is entitled to say.

The receipt keeps its mechanical `engineering_gates` — corpus integrity and whether every
planned request ran — structurally separate from every semantic observation. A green gate
means the instrument ran, not that extraction was good.

## Known limits of the design

* Presence is measured as a count threshold. A run that returns one candidate for a
  one-norm specimen scores the same whether the candidate is apt or nonsense.
* Negative controls test five hand-written fragments. They bound nothing about prose the
  corpus does not contain.
* Paraphrase and standing families rest on the fixture author's judgement that the members
  state the same norm. That judgement is not independently established.
* Threshold detection is literal substring matching against declared markers. A model that
  restates `$10,000` as `ten thousand dollars` reads as absent.
* Semantic stability is exact-match. A trivially reworded `object` counts as a full
  variant, so the metric is a lower bound on agreement.
* Three runs cannot separate a stable answer from a lucky one.
* One corpus, one provider, one model, one prompt revision. Nothing here generalizes past
  those four.
