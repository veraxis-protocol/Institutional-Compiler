# Interpretation Proposal Characterization 001

Status: **OWNER-AUTHORIZED BOUNDED MODEL-ASSISTED INTERPRETATION-PROPOSAL
CHARACTERIZATION — PRE-CANONICALIZATION**

The question:

> Can a model propose useful semantic structure from an admitted candidate without being
> allowed to establish canonical institutional meaning?

This is **act 3 only** — admitted candidate → provisional interpretation proposal. It does
not implement act 4 canonicalization and constructs no Institutional IR.

## Corpus

29 specimens, carried unchanged from the frozen Institutional IR 001 design corpus
(`design/institutional-ir-001/TEST-VECTORS-v0.1.json`,
sha256 `5761b82c…`). Every one carries a real `ADMITTED` receipt produced by the frozen
Admission Runtime 001 evaluator. The five non-`ADMITTED` IR input-boundary vectors are
deliberately excluded: they test the IR seam, not proposal quality.

`IIR-009` appears in the design corpus under the title *temporal trigger*; the work order
names it *vague temporal qualifier*. Same vector, same ID, and it carries the
`vague_temporal_phrase` threat tag — the description differs, the specimen does not.

| Files | |
| --- | --- |
| `CORPUS-v0.1.json` | specimens, admission bindings, and evaluator-only gold |
| `CORPUS-FREEZE-v0.1.json` | corpus digest, counts, selected vector IDs, governing digests |

Planned live run: **29 specimens × 3 runs = 87 provider requests**, no retries.

## The gold is never sent

Each specimen carries the preregistered expected interpretation — expected force, expected
per-slot status and value, expected unresolved references. That is **evaluator-only
metadata**. The request body is built by `oic.interpretation_proposal` from the candidate
span alone; a contract test renders the real prompt for every specimen and asserts that no
gold value, no expected status, no authority evidence, no admission warrant, no reason
code and no interpretation warrant appears anywhere in it.

An experiment where the model can see the answer key measures nothing.

## The unit_type arm

Characterization 001 preregisters **candidate span only**. The provisional `unit_type` is
an earlier model's uncertain classification; passing it would let the interpretation stage
inherit and reinforce a prior model's error before there is any evidence the hint helps.
The production seam takes the hint as an optional parameter and the harness pins it off, so
a later A/B can run both arms. That A/B is **not run here**.

## What the boundary refuses, and what it does not

Refused (structural / provider-response contract): invalid JSON, wrong root shape,
forbidden keys at any depth, an unknown slot, a malformed assertion, an invalid reference
kind, an invented normative force, an interpretation-status token as a value.

**Not refused** — measured instead: an invented actor, a dropped exception, a dropped
threshold, a wrong force, an ungrounded quote, a missed reference, a duplicate slot. Those
are the defects the instrument exists to observe. Rejecting them here would launder model
failure into a clean boundary count.

## No live run has been performed

`live_run_executed: false`. The instrument was implemented, frozen and validated offline.
The owner runs the 87 requests locally.

`independent_validation_claim = FALSE`

`NOT SELF-ADJUDICATED`

**NO LIVE MODEL CHARACTERIZATION WAS CLAIMED.**
**NO CANONICALIZATION WAS IMPLEMENTED.**
**NO INSTITUTIONAL IR RUNTIME WAS IMPLEMENTED.**
