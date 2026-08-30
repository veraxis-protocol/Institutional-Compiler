# Interpretation Proposal Unit-Type A/B 001

Status: **OWNER-AUTHORIZED BOUNDED INTERPRETATION-PROPOSAL UNIT-TYPE HINT A/B
PREREGISTRATION — NO LIVE MODEL CALL**

## Question and arms

Does supplying the Candidate Normative Unit's provisional `unit_type` improve provisional
interpretation proposals—especially constitutive-definition recognition—without
propagating candidate-stage classification error or worsening semantic-role behavior?

- Arm A: `candidate_span` only, exactly Characterization 001 behavior.
- Arm B: `candidate_span + provisional_unit_type`, through the production seam's existing
  optional hint path.

The production system prompt is identical in both arms. Arm B's existing user-prompt hint
calls the type provisional and uncertain, says it is an earlier model's guess, says it has
no authority and may be wrong, and forbids treating it as normative force. Together with
the unchanged system prompt, the hint is explicitly untrusted, noncanonical, and
subordinate to literal source text. No examples or other semantic instructions differ.

## Frozen paired plan

The exact Characterization 001 corpus is reused byte-for-byte: 29 specimens, three run
indices, and two arms, for 174 requests. Within each `(specimen, run_index)` pair, odd runs
are A then B and even runs B then A. There are no retries. Pacing belongs to the external
client; the recommendation for a later owner-run execution is four seconds after every
request.

The primary diagnostic reports every one of the 18 arm observations for IIR-005, IIR-023,
and IIR-024 individually as `CONSTITUTIVE_DEFINITION_PROPOSED`, `FORCE_OMITTED`, or
`OTHER_FORCE_PROPOSED`. The machine-readable plan lists all 14 regression sentinels and all
17 corrected paired metrics. Where meaningful each metric reports A-only defect, B-only
defect, both defect, and neither defect. Any descriptive paired statistic is descriptive,
not an architectural decision and not a p-value decision.

The corrected Post-run Audit 001 definitions govern: a composite ambiguity string is not
separate surfacing; comparator loss broadens a threshold; grounded source text is distinct
from semantic invention; wrong-role placement is distinct from omission.

No A/B result may be inspected and used to tune the prompt in this work order. A later
owner decision may retain span-only, adopt the hint, reject both and revise the prompt, or
revise ambiguity representation. None is authorized here.

This preregistration does not establish semantic correctness, canonical institutional
meaning, model authority, production readiness, cross-model generalization,
canonicalization, Institutional IR runtime, legal interpretation, or independent
validation.

`independent_validation_claim = FALSE`

`NOT SELF-ADJUDICATED`

**NO LIVE MODEL CALL WAS MADE.**
**NO CANONICALIZATION WAS IMPLEMENTED.**
**NO INSTITUTIONAL IR RUNTIME WAS IMPLEMENTED.**
