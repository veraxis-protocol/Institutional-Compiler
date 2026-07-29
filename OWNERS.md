# Engineering Ownership

| Area | Owner | Authority / responsibility |
|---|---|---|
| Product and design authority | Arkadiy Miteiko / Veraxis | Scope, claims, release status, final design decisions |
| Technical program and architecture lead | GPT-5.6 Thinking | Work decomposition, contracts, acceptance gates, integration review, defect adjudication |
| Reference implementation lead | Claude Fable 5 | Repository scaffold, modular-monolith implementation, CI, schemas, API/UI vertical slice |
| ZTL semantic boundary and adapter | Vitaliy Reznik | ZTL interface, truth-state semantics, fixtures, conformance evidence, limitations |
| VEIP adapter and continuity boundary | Veraxis technical lead, designated by Arkadiy | Lifecycle/evidence interface and conformance |
| Benchmark approval | Unassigned external/independent reviewer required before evidence release | Corpus, annotations, baseline and claim-gate review |
| Security approval | Unassigned | Threat model and hosted/on-prem profile review |
| Licensing review | Unassigned counsel | Apache-2.0 / CC BY 4.0 proposal and dependency compatibility |

No module may be represented as independently reviewed until the named external role is filled and the review record is checked in.
