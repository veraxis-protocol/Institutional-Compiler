# OIC-CANDIDATE-NEGATIVE-STABILITY-001 — A/B falsification

One anomalous observation started this. Nothing here fixes it.

`independent_validation_claim = false`. **NOT SELF-ADJUDICATED.**

## The question

The live OIC-CANDIDATE-SEMANTICS-004 characterization was clean on almost everything —
42/42 accepted, zero rejections, zero provider errors, zero presence misses, 43/43 spans
grounded, 33/33 materially complete, 0/27 framing-carrying spans, zero overreach — with one
exception. `CSEM-031`, a negative control, returned one candidate typed `advisory` in run 2
of 3:

> This section explains the governance framework, the delegation register, and the
> compliance calendar maintained by the Secretariat.

003 had returned zero candidates on that specimen in every observed run.

So: **did 004 materially weaken negative-control discrimination relative to 003, or is one
event in fifteen negative runs ordinary provider variance?** One observation cannot tell
those apart, and an anomaly should not be "fixed" before it is known to be reproducible.

This directory is the instrument that asks. It changes no prompt, no parser, and no
production file.

## Arms

| Arm | Commit | Work order |
|---|---|---|
| A — `003` | `db95d8fdf52b5ffb546b2ebd84bb9e035629c46f` | minimal source-grounded candidate spans |
| B — `004` | `11acd84b97bbdb3910c208e63b69b4fbb10be179` | framing separation |

These two commits differ in exactly one file, `src/oic/candidate_extraction.py`, and within
it only the prompt. `nvidia_nim.py` and `model_provider.py` are byte-identical across both,
so the adapter, endpoint, temperature, response format, and credential mechanism are held
constant by construction rather than by assertion. A contract test pins that.

### Each arm runs its own real code

Both commits are checked out into isolated **detached git worktrees**, and every request
executes in a subprocess whose `PYTHONPATH` points at that worktree's `src`. No prompt is
copied, reconstructed, or approximated by the harness. Neither historical commit is
mutated, and worktrees are removed on completion.

**The binding is proven, not assumed.** During development a mistyped `PYTHONPATH` made
both arms resolve to the source repository's editable install — an A/B that would have
compared 004 against 004 and reported a confident null for entirely the wrong reason. The
harness now, before the first live request, asks each arm what it actually imported and
refuses to proceed unless:

* each resolved module path lies inside its own worktree; and
* the two arms differ by `candidate_extraction.py` file digest; and
* the two arms differ by system-prompt digest.

Every individual request re-checks its own binding and fails closed otherwise. The verified
bindings are recorded in the receipt.

## Corpus

Seven specimens, every source text carried **byte-identical** from the frozen 003 corpus and
verified against the blob at commit `db95d8f` rather than a working-tree copy. The question
is whether behaviour changed against an already frozen set, so the set must not move — and
no new negative control was invented for this experiment.

| ID | Role | Repetitions/arm |
|---|---|---|
| CSEM-018 | negative control — descriptive prose | 10 |
| CSEM-019 | negative control — operational fact | 10 |
| CSEM-020 | negative control — promotional prose | 10 |
| **CSEM-031** | **negative control — the trigger** | 10 |
| CSEM-032 | negative control — operational event | 10 |
| CSEM-017 | positive sentinel — advisory | 3 |
| CSEM-027 | positive sentinel — threshold plus approval | 3 |

The sentinels are **not** the primary test. They exist only to detect an accidental broad
suppression of candidate discovery in either arm.

## Run plan

```
negatives   5 specimens × 10 repetitions × 2 arms = 100
positives   2 specimens ×  3 repetitions × 2 arms =  12
                                            total = 112 live requests
```

**Interleaving.** Running all of one arm and then all of the other would confound a prompt
difference with provider drift over the wall-clock hour the run takes. For each
`(specimen_id, run_index)`: odd run index runs 003 then 004, even run index runs 004 then
003. Adjacent requests always share a specimen and run and always cover both arms, and
neither arm ever runs more than twice consecutively. The realized order is recorded in the
receipt.

**Pacing.** ~4 seconds of client-side delay after every request. This belongs to experiment
orchestration only. It is not retry logic, and no production file carries it.

**No retries.** A transport failure is one observation and is recorded as itself.

**Anchors.** Deterministic and identical across arms for the same `(specimen, run_index)`,
carrying the full source quote. The arm label appears nowhere in an anchor: an anchor that
differed between arms would make the comparison meaningless.

## What counts as what

| Outcome | Meaning |
|---|---|
| `STRUCTURAL_PASS` | The response survived the existing candidate boundary |
| `BOUNDARY_REJECTED` | The response was refused by the boundary — **not** a false positive |
| `PROVIDER_ERROR` | No response was observed — **not** a false positive |

**False positive** = `normative_expected` is false **AND** the response survived the
boundary **AND** `candidate_count > 0`.

The existing fail-closed grounding rule remains authoritative and neither arm is repaired.

## Measures

**Primary.** Per arm, `false_positive_runs / provider-successful negative runs`, and the
same per specimen. Every false-positive observation retains its specimen ID, run index,
arm, candidate count, literal candidate span, provisional unit type, request ID,
raw-content SHA-256 and source SHA-256. Individual failures are never summarized away.

**Secondary.** Boundary accepted, boundary rejected, provider errors, grounding failures,
positive-sentinel presence misses, candidate-count distributions, provisional unit-type
distributions, CSEM-031 rate by arm, and all false-positive spans and types by arm.

**Paired comparison.** Because each `(specimen, run_index)` runs in both arms, outcomes are
classified as both-correctly-absent, 003-only, 004-only, or both. A pair missing one side
is `unusable` and is listed, not silently counted. The discordant split gets a two-sided
exact binomial (McNemar-style) p-value computed with the standard library only — no scipy,
no new dependency. **It is descriptive evidence and is near-uninformative at these counts.**

## Preregistered interpretation bands

Fixed before any data existed. The harness reports which band the observations fall into and
prints the raw numbers beside it. Bands are engineering thresholds, not statistical proof,
and they decide no architecture.

**`NO_MATERIAL_REGRESSION_SIGNAL`** — all three must hold:
* 004 exceeds 003 by no more than 2 false-positive events across the 50 negative trials;
* no individual negative specimen shows 004 ≥ 3/10 while 003 ≤ 1/10;
* both positive sentinels present in every provider-successful run.

**`REGRESSION_SIGNAL`** — either:
* 004 exceeds 003 by at least 5 false-positive events across the 50 negative trials; or
* any individual negative specimen shows 004 ≥ 4/10 while 003 ≤ 1/10.

**`INCONCLUSIVE`** — otherwise.

## CSEM-031

The receipt gives the trigger specimen its own section listing **all 20 attempts** — 10 per
arm — individually. Repeated identical outputs are not collapsed. Any false positive shows
its exact returned span and provisional type.

## Running it

```sh
export NVIDIA_API_KEY=...          # local environment only; never commit this
git checkout oic-candidate-negative-stability-001
python scripts/characterize_candidate_negative_stability.py
```

All flags default: corpus and freeze paths above, model
`nvidia/nemotron-3.5-lightning-30b-a3b`, 4 s pacing, receipt to
`.local/candidate-semantics-receipts/OIC-CANDIDATE-NEGATIVE-STABILITY-001.json`
(gitignored). 112 requests at ~4 s pacing is roughly 10–15 minutes plus provider latency.

The harness refuses to start unless the source repository is clean, both commits exist, the
corpus matches its freeze record, and the arms are provably distinguishable. **There is no
drift-acknowledgement flag**: the authorized run needs none, and re-freezing is a deliberate
act. The credential is read from the environment by each arm's own adapter and is never
printed, logged, or written to the receipt.

## Claim ceiling

This experiment measures comparative negative-control discovery behavior between two exact
frozen candidate prompts under one provider/model and one small frozen synthetic corpus. It
does **not** establish semantic correctness, zero false-positive probability, production
readiness, institutional admission, authority, enforceability, legal interpretation,
cross-model generalization, statistical equivalence, or independent validation.

**No change is authorized by this work order.** Only the owner-run live receipt can inform
whether the 004 prompt should change, and even a regression signal is an input to that
decision rather than the decision itself.

## Known limits

* Five negative controls, ten repetitions each per arm. A rate of 1-in-50 is barely
  distinguishable from 1-in-500 at this sample size.
* `temperature` is whatever each frozen commit specifies (0.0), so observed variation is a
  floor rather than the model's full spread.
* The arms differ by one commit. A difference is attributable to that diff as a whole, not
  to any prompt feature isolated in the abstract.
* Interleaving reduces but does not eliminate provider-time drift. A provider-side model
  update mid-run would affect both arms and is not detectable here.
* The bands were chosen by judgement, not derived from a power calculation.
* **Absence of a regression signal is not evidence of equivalence.** With 50 negative trials
  per arm, a real but modest increase in false-positive rate would very likely land in
  `NO_MATERIAL_REGRESSION_SIGNAL`.
* One provider, one model, one endpoint. Nothing generalizes past them.
