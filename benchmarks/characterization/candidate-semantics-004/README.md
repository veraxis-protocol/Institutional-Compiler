# OIC-CANDIDATE-SEMANTICS-004 — framing separation

A focused regression corpus for one remaining candidate-span precision defect. Not another
broad semantic suite: 14 specimens, nine carried verbatim from
`../candidate-semantics-003/` so before and after are comparable, and five new diagnostics
for framing structures the predecessor did not cover.

`independent_validation_claim = false`. **NOT SELF-ADJUDICATED.**

## The defect

The paced 003 live characterization came back clean on almost everything: 77 of 78 requests
accepted, zero boundary rejections, zero presence misses, zero false positives, 65 of 65
candidate spans literally source-grounded, 60 of 60 measured runs materially complete, and
the multi-unit specimen separated in all three runs. One measurement did not:
`candidate_spans_outside_bounds = 4 / 18`.

CSEM-021 returned, in all three runs, the whole fragment including `DRAFT — NOT YET
ADOPTED.` rather than the proposition alone. CSEM-023 did the same in one run of three,
carrying `For the sake of illustration, suppose a rule stated that` into the span.

That is a quoting defect, not a discovery defect. The proposition was found every time.

## The correction

**A candidate span should quote the normative proposition, not the source's separable
commentary about that proposition's own status.**

Draft status, hypothetical framing, illustrative framing, attribution and unverified
provenance are all real and are all kept — in the source anchor, where they belong. They
simply should not contaminate the proposition span when they are grammatically separable
from it.

Four rules, added to the prompt contract:

1. find literal normative propositions;
2. preserve all material proposition language;
3. exclude separable metalinguistic and source-standing framing;
4. decide nothing about whether the proposition is authoritative, adopted, valid, admitted,
   enforceable, or legally operative.

Rule 4 is why rule 3 is safe. Leaving framing outside a span is a **quoting decision, not a
finding**. Candidate discovery remains independent of standing: draft, hypothetical,
synthetic, unverified and non-authoritative framing still never suppress a candidate.

### What did not change

| | |
|---|---|
| Model-proposed fields | `candidate_span`, `unit_type` — unchanged |
| OIC-controlled fields | `unit_id`, `interpretation_state`, `epistemic_state`, `source_anchors` — unchanged |
| Semantic roles | still absent, still fail closed |
| Authority fields | still absent, still fail closed |
| Grounding rule | unchanged and still fail-closed |
| Identity material | unchanged, still tagged `candidate_schema: "003"` |
| Parser | unchanged |
| `src/oic/nvidia_nim.py` | byte-identical |
| `src/oic/review_docket.py` | byte-identical |

No `context`, `framing`, or `standing` field was added anywhere. 004 is a prompt change and
a measurement change.

### Framing is never stripped by OIC

There is no phrase list, no regex, no post-generation trimming, and no repair anywhere in
production code. An overreaching span is accepted exactly as returned and recorded as an
observation.

This is deliberate. Stripping recognized prefixes would make OIC the author of the span it
then reports as source-grounded — the literal-containment grounding rule would still pass,
because it would be checking OIC's own edit against the source. The provider must propose
the correct boundary itself, and where it does not, the receipt says so.

The grounding rule is unchanged:

```
collapse_whitespace(casefold(candidate_span))  ⊆  collapse_whitespace(casefold(source_text))
```

Failure raises `CandidateGroundingError` and fails the whole response. No fuzzy matching, no
embeddings, no second model, no semantic similarity, no substitution.

## Source context

Nothing was added to preserve it, because nothing needed to be. The caller-supplied source
anchor already carries the whole fragment as `quote`, and the review docket already exposes
`source_anchor` as a top-level key structurally separate from `candidates_by_id`.

So a reviewer looking at one docket sees both:

* `source_anchor.quote` — `DRAFT — NOT YET ADOPTED. A payment above $10,000 requires
  approval by the Chief Financial Officer.`
* the candidate's `candidate_span` — `A payment above $10,000 requires approval by the
  Chief Financial Officer.`

Draft status appears as source context and nowhere else. It is **not** candidate authority
metadata, and no candidate field records it.

## Identity

Unchanged, deliberately. Candidate identity stays source-instance-aware because the
deterministic material includes the source anchor. The same proposition appearing under a
draft prefix at one anchor and undisclaimed at another gets **two different `unit_id`s**,
and 004 does not merge them. Canonical equivalence across source instances is a future
Institutional IR problem and is not implemented here.

The identity tag stays `candidate_schema: "003"` because the *schema* did not change — 004
changed the prompt. Bumping it would move every `unit_id` for no structural reason.

## Corpus

| ID | Carried | Framing structure |
|---|---|---|
| CSEM-017 | 003 | none present (advisory baseline) |
| CSEM-018 | 003 | negative control |
| CSEM-021 | 003 | draft prefix |
| CSEM-022 | 003 | non-authoritative prefix |
| CSEM-023 | 003 | hypothetical wrapper |
| CSEM-024 | 003 | unverified prefix |
| CSEM-025 | 003 | none present (multi-unit baseline) |
| CSEM-027 | 003 | none present (undisclaimed baseline) |
| CSEM-031 | 003 | negative control |
| CSEM-041 | new | illustrative wrapper |
| CSEM-042 | new | source attribution |
| CSEM-043 | new | **draft word inside the proposition — must NOT be stripped** |
| CSEM-044 | new | draft prefix over advisory material |
| CSEM-045 | new | one framing prefix over two propositions |

CSEM-043 is the control against over-correction. `Where a contract is still in draft, the
sponsoring unit must record the reason for the delay.` says something *about a draft*,
not *as a draft*: the clause governs conduct and is material proposition content. A span
that sheds it is underreach, not framing separation.

### Pre-registration

Per specimen, describing the **source** rather than a required answer:

| Field | Meaning |
|---|---|
| `separable_framing_spans` | Literal spans stating the source's own status; `null` when none |
| `framing_expected_excluded` | Whether that framing should sit outside the span |
| `framing_structure` | Which framing construction this specimen exercises |
| `candidate_span_bounds` | One or more acceptable proposition boundaries |
| `material_span_groups` | Content that must survive, conjunctive across groups, disjunctive within |
| `diagnostic_tags` | What the specimen is for |

Several literal boundaries are defensible for one proposition, so bounds are a set and no
specimen preregisters a single exact expected string. Stylistic preference is not a
correctness gate.

## Metrics

Version-specific: 001, 002 and 003 keep their own metric contracts and are never
reinterpreted under this one.

| | Measure |
|---|---|
| A | Boundary acceptance |
| B | Provider errors, separate from boundary refusals |
| C | Positive candidate presence |
| D | Negative-control false positives |
| E | Candidate-count stability |
| F | Literal source grounding |
| G | Material-span completeness |
| H | Candidate-span repeat stability |
| I | Source-standing presence/count/type invariance |
| **J** | **Framing separation** — per specimen: accepted runs, spans examined, spans inside acceptable bounds, spans containing separable framing, runs dropping material content, result |
| J2 | Framing that must **not** be stripped (the CSEM-043 control) |
| K | Multi-unit separation |
| L | Advisory presence |
| **M** | **Candidate-span underreach** — material content lost, with the missing groups named |
| M′ | Candidate-span overreach — spans beyond a registered bound |

**Overreach and underreach are opposite defects and are counted separately.** A span that
sheds a draft prefix but also sheds `$10,000` or `Chief Financial Officer` is recorded as
`MATERIAL_CONTENT_LOST` and is **never** scored as a framing-separation success. A single
run can exhibit both, and each is booked where it belongs.

## Running it

No live call was made in this work order, and none is claimed. The owner runs the live
regression separately.

```sh
export NVIDIA_API_KEY=...          # local environment only; never commit this
python scripts/characterize_candidate_semantics.py \
  --corpus benchmarks/characterization/candidate-semantics-004/CORPUS-v0.4.json \
  --freeze benchmarks/characterization/candidate-semantics-004/CORPUS-FREEZE-v0.4.json \
  --runs-per-specimen 3 \
  --model nvidia/nemotron-3.5-lightning-30b-a3b \
  --output .local/candidate-semantics-receipts/OIC-CANDIDATE-SEMANTICS-004.json
```

All flags are defaults. 14 × 3 = 42 requests. The corpus digest is recomputed before every
run and drift stops the run unless `--allow-corpus-drift` is passed, which stamps the
receipt `DRIFT_ACKNOWLEDGED`. The credential is read from the environment by the existing
adapter and is never printed, hashed, or written into a receipt. Unit and contract suites
need no credential and no network.

Predecessor corpora remain runnable at their own paths and still receive their own metric
contracts.

## Claim ceiling

This experiment characterizes candidate-span framing separation under one frozen synthetic
corpus, implementation commit, provider/model when later run live, and bounded run
conditions. It does **not** establish semantic correctness, institutional admission,
authority, enforceability, legal interpretation, production readiness, runtime readiness,
cross-model generalization, or independent validation.

No admission or authority boundary is implemented. No Institutional IR is implemented.

## Known limits

* **Nothing here measures a model.** These are offline tests of the instrument and of what
  OIC asks for. Whether any provider complies is what the live regression measures.
* Framing separation is unenforced by construction. The prompt asks; only the receipt
  reports. Overreach cannot fail closed without OIC authoring spans, which is worse.
* "Separable" is a judgement, and the corpus encodes one author's reading of 14 fragments.
  CSEM-043 exists because that judgement can go wrong in the stripping direction too, but
  one control does not bound the class.
* Registered bounds are literal. A model that picks a defensible boundary the corpus did
  not anticipate reads as overreach, so M′ is an upper bound on the real defect rate.
* Material completeness matches literally, so a restatement in other words reads as loss.
  G and M are lower bounds on preservation.
* Nine of 14 specimens are carried, and five of those nine already behaved correctly in
  003. The corpus is deliberately small and is a regression probe, not a survey.
* Three runs per specimen cannot separate a stable answer from a lucky one, and
  `temperature=0.0` means observed variation is a floor.
* One corpus, one prompt revision, one implementation commit, one model when run.
