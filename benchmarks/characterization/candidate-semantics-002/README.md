# OIC-CANDIDATE-SEMANTICS-002 — source-grounded candidate contract

Successor to `../candidate-semantics-001/`, which stays in the tree unchanged. That corpus
is the evidence its own receipt refers to; rewriting it would falsify a receipt that was
true when it was issued.

## What changed and why

The 001 live characterization accepted 96/96 responses through the candidate boundary and
returned zero false positives on the negative controls — and still showed the candidate
layer doing something it is not authorized to do. It was **normalizing toward canonical
meaning** rather than **reporting what the source says**. Invented participants
(`accounts payable`, `payee`, `purchase order approver`) appeared for fragments that name
nobody. Explicit `if` and `where` clauses vanished. `$75` disappeared from two runs in
three. A trigger predicate was recorded as the operative action.

None of that is a model defect to be patched around. It is the candidate layer having no
contract that distinguishes A, source-grounded identification and segmentation, from B,
normalization toward Institutional IR. 002 moves the layer decisively to A. B belongs
after institutional admission and is not implemented.

**A candidate normative unit is source-grounded candidate material. It is not
Institutional IR.**

## The contract

The model is asked for two kinds of thing and held to two standards:

* **`unit_type` is a classification.** It proposes the candidate's *primary normative
  function* and is understood to be uncertain — OIC stamps every candidate
  `epistemic_state = uncertain` regardless.
* **Every textual role is a verbatim source span.** `actor`, `action`, `object`, `target`,
  `conditions`, `exceptions`, `evidence_requirements` must each be an exact contiguous run
  of characters from the fragment. This is checked deterministically.

The model must not invent an actor, infer one from the passive voice, supply a missing
recipient, approver, owner, payee, department or authority, drop a material qualifier,
canonicalize a paraphrase, resolve ambiguity into institutional fact, or decide authority,
admission, legal effect, enforceability, allow/deny, or any runtime result.

### The grounding rule

Every textual role value, and every entry of every array role, must satisfy:

```
collapse_whitespace(casefold(value))  ⊆  collapse_whitespace(casefold(source_text))
```

Literal containment. No stemming, no synonym table, no similarity model, and no second
model adjudicating the first — any of those would put semantic authority back inside the
candidate layer. Case and whitespace are the only tolerances, and neither can admit a
phrase the fragment does not contain, so both remove false rejections without weakening
the rule.

Requiring verbatim spans is what makes literal checking honest. The alternative — letting
the model paraphrase and then judging whether the paraphrase is supported — is the thing
that cannot be done deterministically. Where the two could conflict, 002 tightened the
contract rather than weakening the validator.

`unit_type` is deliberately exempt: it is a classification, not source text.

**Failure is explicit and fail-closed.** An ungrounded value raises
`CandidateGroundingError` (a `CandidateBoundaryError`, so every existing handler still
catches it) naming the candidate index, the field, and the offending value. Nothing is
stripped. Nothing is repaired. One bad field fails the whole response, including its
well-formed siblings.

### The `target` role

One role was added: `target` — an explicitly stated destination, recipient, beneficiary, or
counterparty the governed act is directed toward. `null` unless the fragment states one,
and grounded like every other textual role.

It was added because `to the Finance Office` and `to the Chief Operating Officer` had
nowhere to go, so they landed in `object` in some runs and vanished in others. That is a
representation gap, not a model failure. `target` participates in the deterministic
`unit_id` and in the semantic projection, exactly as the other roles do. No larger role
ontology was added, and no admission, confidence, or canonical-IR field was added.

## Corpus

40 specimens: all 32 from 001, carried over with id, source text, category, expectations
and notes unchanged, plus 8 diagnostics for the evidenced failure classes.

| ID | Diagnostic for |
|---|---|
| CSEM-033 | Fully passive fragment naming no participant |
| CSEM-034 | Explicit destination, passive actor |
| CSEM-035 | Explicit actor and explicit recipient |
| CSEM-036 | Trigger predicate vs. operative act |
| CSEM-037 | Advisory, `should` form |
| CSEM-038 | Advisory, impersonal `it is recommended` form |
| CSEM-039 | Explicit record-keeping duty with a named actor |
| CSEM-040 | Monetary threshold plus a qualifying clause |

Six source-grounding fields are pre-registered per specimen, describing the **source**, not
a required answer:

| Field | Meaning |
|---|---|
| `actor_explicitly_named` | Does the source name someone who acts? |
| `target_explicitly_named` | Does the source name a recipient or destination? |
| `expected_target_spans` | Acceptable renderings of that recipient |
| `required_condition_spans` | Acceptable renderings of an explicit qualifying clause |
| `material_qualifier_spans` | Acceptable renderings of a threshold or time limit |
| `non_operative_predicate_spans` | The trigger predicate, which is *not* the operative act |

Every `*_spans` list is **disjunctive**: one required element, several acceptable
renderings; the element counts as preserved when at least one appears. A list does not
enumerate several independent elements. Every declared span is tested to actually occur in
its own specimen's source, because a span the source does not contain would produce a
confident and meaningless metric.

Negative controls pre-register nothing: if nothing should be extracted, nothing can be
expected to be preserved.

## Measures

Primary at this stage:

| | Measure |
|---|---|
| A | Boundary acceptance, now broken down by rejection error type |
| C | Negative-control false positives |
| D | Candidate-count stability |
| E | Unit-type observation against the preregistered set |
| G | Source-standing invariance |
| K | Candidates asserting an actor where the source names none |
| L | Explicit qualifying clauses reaching `conditions` |
| M | Material thresholds and time limits surviving anywhere in the candidate |
| N | Advisory presence misses |
| O | Explicit recipients reaching `target` |
| P | How explicit record duties were actually classified |
| Q | Trigger predicates recorded as the operative action |

Secondary, reported but not what this stage asks about: B, F, H, I, J.

**F, exact semantic-hash stability, is explicitly demoted.** A source-grounded candidate
quotes its own fragment, so two defensible readings of one fragment legitimately hash
differently. Canonicalizing them is Institutional IR's job, after admission, and is not
implemented. Instability is still informative; it is not a target, and the receipt says so
in `measure_classification.demoted`.

**Paraphrase invariance is likewise relaxed.** Across materially different phrasings this
stage asks for presence agreement, count agreement, and broadly compatible unit types.
Exact semantic-hash agreement is **not required** — different wording produces different
spans by construction — and the receipt marks it `not_required_at_candidate_stage`.

Metric K deserves one note. Under the revised contract an ungrounded actor cannot survive
the boundary at all, so an entirely invented participant is counted as a grounding
rejection under A, never under K. What K counts is a *grounded* span the model chose to
read as an actor on a fragment the corpus records as naming nobody — a weaker and more
honest finding than the invention it replaces.

## Running it

```sh
export NVIDIA_API_KEY=...          # local environment only; never commit this
python scripts/characterize_candidate_semantics.py \
  --corpus benchmarks/characterization/candidate-semantics-002/CORPUS-v0.2.json \
  --freeze benchmarks/characterization/candidate-semantics-002/CORPUS-FREEZE-v0.2.json \
  --runs-per-specimen 3 \
  --model nvidia/nemotron-3.5-lightning-30b-a3b \
  --output .local/candidate-semantics-receipts/OIC-CANDIDATE-SEMANTICS-002.json
```

All flags are defaults. 40 specimens × 3 runs = 120 requests. Three runs is an initial
stability probe, not a statistically sufficient sample. The corpus digest is recomputed
before every run and drift stops the run unless `--allow-corpus-drift` is passed, which
stamps the receipt `DRIFT_ACKNOWLEDGED`. The credential is read from the environment by the
existing adapter and never printed, hashed, or written to a receipt. Unit and contract
suites need no credential and no network.

To re-run the historical corpus, pass the 001 paths explicitly. It still loads; its
grounding fields read `null`.

## Claim ceiling

`independent_validation_claim = false`.

Running this corpus characterizes candidate extraction behaviour on this corpus under one
identified implementation commit, provider, model, and run condition. It establishes no
semantic correctness, institutional admission, authority, enforceability, runtime
authorization, production readiness, regulatory compliance, superiority, or independent
validation. No admission or authority boundary is implemented anywhere in this work order.

## Known limits

* **Boundary rejections will rise.** Verbatim spans are a strict contract, and a model that
  paraphrases loses the whole response. That is the intended trade — fail-closed over
  quietly-normalized — but the acceptance rate is no longer comparable with 001's 96/96.
* Literal containment cannot tell a *legitimate* paraphrase from an invention. Both are
  refused identically.
* A grounded value in the wrong role still passes grounding. `object` holding a recipient
  is caught by metric O, not by the validator.
* Preservation metrics match literally. A model restating an element in other words reads
  as omitting it, so L and M are lower bounds on preservation.
* One `*_spans` list expresses one element. A specimen with two independent required
  conditions cannot be expressed, and none in this corpus needs to be.
* Exception preservation is not measured. Conditions and thresholds are; carve-outs are
  observed only through the semantic projection.
* The pre-registrations are one author's reading of each fragment. A wrong reading yields a
  confidently wrong count.
* `actor_explicitly_named` is a binary over fragments where agency is sometimes genuinely
  arguable — a noun modifier such as `Board approval` is recorded as naming no actor.
* No live run has been performed against this contract. Every number above is about the
  instrument, not about behaviour.
