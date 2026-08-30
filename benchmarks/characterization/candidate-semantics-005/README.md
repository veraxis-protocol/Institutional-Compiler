# OIC-CANDIDATE-SEMANTICS-005 — the normative-discovery boundary

`independent_validation_claim = false`. **NOT SELF-ADJUDICATED.**

## The defect

The frozen A/B experiment `OIC-CANDIDATE-NEGATIVE-STABILITY-001` compared commits
`db95d8fdf52b5ffb546b2ebd84bb9e035629c46f` (003) and
`11acd84b97bbdb3910c208e63b69b4fbb10be179` (004) over 112 requests.

Its **preregistered band returned `INCONCLUSIVE`, and that historical result is not
rewritten here.** No statistical-significance claim is made or implied.

What it observed was localized and reproducible. Three false positives, all in the 004 arm,
all on one specimen, against zero in the 003 arm:

| | 003 | 004 |
|---|---|---|
| provider-successful negative runs | 46 | 49 |
| false positives | 0 | 3 |
| CSEM-031 | 0 / 10 | 3 / 9 |

All three returned the **entire fragment** as the candidate span and typed it `advisory`,
with the same raw-content digest each time:

> This section explains the governance framework, the delegation register, and the
> compliance calendar maintained by the Secretariat.

That sentence carries governance, delegation, compliance and an institutional actor. It
expresses no normative proposition. It says what a section explains and what artifacts a
Secretariat maintains.

004 successfully taught the model to quote an embedded proposition without carrying
source-standing framing. In doing so it appears to have loosened what counts as a
proposition at all: **institutional subject matter had become sufficient for discovery.**

The architecture owner authorized a narrow correction on that observed defect. This is an
engineering decision about a reproducible localized failure, not a claim of significance.

## The correction

**Candidate discovery requires a proposition that itself appears to perform a provisional
normative or constitutive function. Institutional vocabulary is never sufficient on its
own, and no particular modal verb is required.**

Added to the prompt contract:

> Institutional subject matter is not by itself normative. A fragment that only says
> something exists, sits somewhere, happened, contains something, explains or describes
> something, maintains an artifact, summarizes a structure, reports past activity, or
> advertises a capability is not candidate material, however much governance, compliance,
> policy, delegation, oversight, register, framework, committee, procedure or office
> vocabulary it carries. Institutional nouns do not create normativity. If nothing in the
> fragment performs an apparent normative or constitutive function, return no candidates.
>
> Do not look for particular words either. Normative function needs no must, shall, may or
> should: a proposition can require, prohibit, permit, authorize, delegate, fix what a term
> means, set a condition or exception, impose an evidence or review duty, prescribe
> escalation or remedy, establish a temporal trigger, confer discretion, or genuinely
> recommend, without any of those modals. Ask what the proposition does, not which words it
> uses.
>
> Two distinctions this turns on. A definition is candidate material when it is constitutive
> or operative, fixing what a term means for some stated purpose, and not when it merely
> explains what a concept is about. Advisory is candidate material when the fragment
> actually recommends or encourages a course of action, and not when it merely discusses
> guidance, standards, or good practice.

Plus three short contrasts (a description → no candidates; a genuine recommendation → a
candidate; a constitutive definition → a candidate), worded to collide with no corpus
specimen, and one sentence repeating the rule in the user prompt.

The second paragraph is the guard against over-correction. The obvious cheap fix — demand
`must`, `shall`, `may` or `should` — would suppress genuine advisory, definitional and
constitutive material, which is a worse failure than the one being corrected.

### What did not change

| | |
|---|---|
| Model-proposed fields | `candidate_span`, `unit_type` — unchanged |
| OIC-controlled fields | `unit_id`, `interpretation_state`, `epistemic_state`, `source_anchors` — unchanged |
| Semantic roles | still absent, still fail closed |
| Authority fields | still absent, still fail closed |
| Parser | unchanged |
| Grounding rule | unchanged, fail-closed |
| Identity | unchanged, still tagged `candidate_schema: "003"` |
| Framing separation | every 004 rule retained verbatim |
| Material completeness | every 004 rule retained verbatim |
| `src/oic/nvidia_nim.py` | byte-identical |
| `src/oic/review_docket.py` | byte-identical |
| `schemas/draft/…` | byte-identical |

No `confidence`, `normative_score`, `advisory_score`, `standing`, `authority`, `admission`,
`legal_effect` or context-classification field was added.

### No filter, and why

There is **no keyword list, no institutional-vocabulary blacklist, no deterministic negative
filter, no secondary classifier, no second model, and no post-generation removal of
candidates** anywhere in production code. A descriptive fragment the provider still reports
is recorded exactly as returned and measured.

That is not squeamishness. A filter would put the normative/non-normative judgement inside
the candidate layer — precisely the judgement this layer is not entitled to make — and it
would make the measurement circular, since metric N would then be scoring OIC's own filter
rather than the provider's discovery.

Contract tests enforce this structurally via AST: every module-level collection constant is
enumerated, the only compiled regular expression is the source-anchor digest pattern, the
normalized-candidate comprehension carries no condition, and the module contains no `del`,
`continue`, `filter()` or `.pop()`.

## Corpus

21 specimens. Fourteen carried verbatim from the frozen 003 and 004 corpora — verified
against the blobs at their own commits — so no 004 property can regress unobserved.

**Negative controls (8, expect exactly zero candidates):**

| ID | Why |
|---|---|
| CSEM-018 | descriptive prose |
| CSEM-019 | quantitative operational fact |
| CSEM-020 | promotional prose |
| **CSEM-031** | **the motivating specimen** |
| CSEM-032 | operational event report |
| CSEM-046 | institutional vocabulary, description only *(new)* |
| CSEM-047 | institutional vocabulary plus historical fact *(new)* |
| CSEM-048 | explanatory section body, no norm *(new)* |

CSEM-046 through CSEM-048 exist so the correction is not tuned to one sentence.

**Positive sentinels and over-correction controls:**

| ID | Why |
|---|---|
| CSEM-017 | genuine advisory guidance |
| CSEM-027 | genuine mandate with threshold and recipient |
| CSEM-049 | constitutive definition *(new)* |
| CSEM-050 | explicit advisory, no modal verb *(new)* |
| CSEM-051 | constitutive delegation *(new)* |
| CSEM-052 | **mixed fragment** *(new)* |

**Framing and material sentinels:** CSEM-021 (draft prefix), CSEM-023 (hypothetical),
CSEM-024 (unverified), CSEM-044 (advisory under a draft prefix), CSEM-045 (one prefix, two
propositions), CSEM-025 (multi-unit), CSEM-043 (`still in draft` inside the proposition —
the control against stripping too much).

**CSEM-052 is the discriminating specimen.** Descriptive institutional prose immediately
followed by a real norm. Exactly one candidate is expected, and the registered bound covers
the normative sentence only, so returning the descriptive lead-in as well reads as
overreach under metric M′.

## Metrics

Version-specific — 001 through 004 keep their own metric contracts and are not
reinterpreted.

A boundary acceptance · B provider errors · C positive candidate presence · D
negative-control false positives · E candidate-count stability · F literal source grounding
· G material-span completeness · H candidate-span repeat stability · I source-standing
invariance · J framing separation (+ J2, framing that must not be stripped) · K multi-unit
separation · L advisory presence · M candidate-span underreach · M′ candidate-span
overreach · **N normative-discovery discrimination**.

**Metric N** reports, for every negative control: accepted runs, zero-candidate runs,
false-positive runs, the literal false-positive spans with their raw-content digests, and
the provisional types assigned. For every positive boundary sentinel: presence, candidate
counts and provisional types.

**No scalar accuracy score is computed.** A false positive on a descriptive source and a
presence miss on a normative one are different failures with different causes, and a single
number would let one pay for the other — which is exactly how an over-correction would hide.

## Running it

No live call was made in this work order and none is claimed.

```sh
export NVIDIA_API_KEY=...          # local environment only; never commit this
python scripts/characterize_candidate_semantics.py
```

All flags default to the 005 corpus, freeze record, model
`nvidia/nemotron-3.5-lightning-30b-a3b`, 3 runs per specimen, and a gitignored receipt
path. 21 × 3 = 63 requests. The corpus digest is recomputed before every run and drift stops
the run. The credential is read from the environment by the existing adapter and never
printed, hashed, or written to a receipt.

## Claim ceiling

This corpus characterizes one bounded candidate-discovery prompt contract under one frozen
synthetic corpus, implementation commit, provider/model when later run live, and bounded run
conditions. It does **not** establish semantic correctness, zero false-positive probability,
institutional admission, authority, enforceability, legal interpretation, production
readiness, cross-model generalization, statistical superiority, or independent validation.

No admission or authority boundary is implemented. No Institutional IR is implemented.

## Known limits

* **Nothing here measures a model.** These are offline tests of what OIC asks for. Whether
  the correction works is what the owner-run 004-vs-005 regression measures.
* The correction is prompt guidance and is unenforced by construction. Only the receipt
  reports; nothing fails closed on a descriptive candidate, and that is deliberate.
* **The over-correction risk is real and is the reason CSEM-049 to CSEM-051 exist.** A prompt
  that suppresses institutional description could also suppress definitions, delegations and
  advisory material, all of which are expressed in institutional vocabulary.
* Eight negative controls and four new positives cannot bound either failure class. Three of
  the negatives are new and untested against any model.
* The motivating evidence is 3 events in 49 runs on one specimen, from an experiment whose
  own band read `INCONCLUSIVE`. The correction is a judgement about a reproducible localized
  failure, not a statistically established one.
* "Performs a normative function" is a judgement encoded by one author over 21 fragments.
  CSEM-052 in particular assumes one reading of where the description ends.
* Three runs per specimen cannot separate a stable answer from a lucky one, and
  `temperature=0.0` makes observed variation a floor.
* One corpus, one prompt revision, one implementation commit, one model when run.
