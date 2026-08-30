# Institutional IR 001 — design and preregistration

Status: **OWNER-AUTHORIZED INSTITUTIONAL IR ARCHITECTURE DESIGN AND PREREGISTRATION — NO
IR IMPLEMENTATION**

Starts from Admission Runtime Freeze 001. Admission answered whether the institution may
interpret a source. This package designs what it means for the institution to have
actually established what that source says — and keeps a model from becoming the
institution by writing the answer itself.

## Contents

| File | What it is |
| --- | --- |
| `IR-CONTRACT-v0.1.md` | The normative design: five acts, the eleven-slot vocabulary, interpretation authority tiers, identity, temporality, and the minimum downstream compiler interface. |
| `SEMANTIC-INVARIANTS-v0.1.md` | The twelve frozen invariants, each stated so a violation is observable in a unit. |
| `AMBIGUITY-AND-UNKNOWN-v0.1.md` | Why the status vocabulary has four values and not three, and how each of the ten ambiguity situations is represented. |
| `IR-LINEAGE-v0.1.md` | The reconstruction chain and the minimum lineage projection. |
| `THREAT-MODEL-v0.1.md` | Threats, the structural feature that blocks each, and the vector that would expose its absence. |
| `INTERPRETATION-RULESET-v0.1.json` | The frozen slot vocabulary with per-slot justification, the excluded dimensions with reasons, the status and basis vocabularies, conservative normalizations, and forbidden transitions. |
| `INTERPRETATION-PROPOSAL-v0.1.schema.json` | Provider-neutral provisional proposal. No confidence, authority or canonical-status field exists. |
| `INTERPRETATION-EVIDENCE-v0.1.schema.json` | Registered interpretation rules and institutional interpretation warrants. |
| `INSTITUTIONAL-IR-v0.1.schema.json` | The canonical unit. |
| `TEST-VECTORS-v0.1.json` | 40 frozen vectors, each carrying a real admission receipt from the frozen evaluator. |
| `TEST-VECTORS-FREEZE-v0.1.json` | Corpus digest, counts and threat tags. |
| `PREREGISTRATION-v0.1.md` | Hypothesis, method, twelve falsifiers, acceptance criteria, limitations. |

## The shape of it

```
source grounding  →  ADMISSION  →  interpretation proposal  →  canonicalization  →  IR unit
   (frozen)          (frozen)        PROVISIONAL, untrusted     institution-owned    canonical
```

Three separate artifacts sit between an admitted candidate and canonical meaning, because
collapsing them is the failure this design exists to prevent.

## Relation to the historical schema

`schemas/draft/institutional-ir.schema.json` is historical, generic and provisional. It
remains byte-identical and is not overwritten or redefined. `INSTITUTIONAL-IR-v0.1` is a
design-namespace successor. **No migration between the two is claimed.**

## What is not here

No `src/oic/institutional_ir.py`. No IR evaluator or compiler. No model call. No OCE, no
Rego, no runtime decision, no ZTL, OAM or VEIP integration. No `ALLOW` and no `DENY`.

`independent_validation_claim = FALSE`

`NOT SELF-ADJUDICATED`

**NO INSTITUTIONAL IR RUNTIME WAS IMPLEMENTED.**
