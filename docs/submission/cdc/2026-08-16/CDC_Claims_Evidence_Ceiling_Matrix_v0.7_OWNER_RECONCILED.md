# CDC Claims → Evidence → Ceiling Matrix — Owner-Reconciled Successor v0.7

**Date:** 2026-08-16  
**Governing baseline:** TDD-OAM-001 v1.1 bounded by SAR-OAM-001 v1.0.  
**Historical input preserved:** `04-CDC-CLAIMS-EVIDENCE-CEILING-MATRIX(6).md` remains the contributor-frozen A–E artifact. This successor does not rewrite that historical state; it applies later frozen execution/adjudication evidence at the owner claim layer.

**Discipline:** design remains design; measured carries its denominator and assurance; a historical block is not rewritten by later successor evidence; internal technical demonstration is not independent validation.

| Claim | Owner-reconciled status | Current evidence class / denominator | Maximum permitted wording now | Remaining limitation |
|---|---|---|---|---|
| CDC-CLAIM-01 Institutional authority | UNCHANGED | DESIGN + challenge boundary | Architecture separates source authority from mission authority; machine output does not acquire either by being produced. | Real CDC authority configuration requires institutional inputs. |
| CDC-CLAIM-02 OIC admitted-meaning boundary | UNCHANGED | DESIGN_BASELINE + OIC artifacts | OIC records/binds/version-controls admitted meaning; OAM must not silently reinterpret it. | Full policy-to-meaning compiler correctness is not established by RUN-003. |
| CDC-CLAIM-03 OAM mission logic | UNCHANGED | DESIGN_BASELINE | OAM executes bounded mission logic and evidence continuity; it does not create institutional meaning. | Not a claim of institutional deployment. |
| CDC-CLAIM-04 Evidence-bound candidate | UNCHANGED | DESIGN + PARTIAL_ARTIFACT | The candidate model requires the enumerated evidence and identity bindings; partial supporting artifacts exist. | RUN-003 criterion evidence does not by itself establish full OAM material-candidate EBAWU binding. |
| CDC-CLAIM-05 ZTL logical warrant | UNCHANGED | MACHINE_CHECKED_FORMAL + historical measured mutation evidence + architectural boundary | ZTL establishes logical warrant under represented logic, not institutional authority. | Internal technical adjudicator authored controlling semantics; no independent assurance. |
| CDC-CLAIM-06 Human standing | UNCHANGED | DESIGN | Standing is bounded and externally grounded; role/login alone is insufficient. | Executable real CDC standing is not established. |
| CDC-CLAIM-07 Machine candidate ≠ official finding | UNCHANGED AT INSTITUTIONAL LEVEL; MECHANICS PARTIALLY SUPPORTED | DESIGN + operating rule; synthetic reliance mechanics measured | Machine output does not become official merely by being produced; bounded synthetic consequential transitions are separately gated. | No real CDC officialization path measured. |
| CDC-CLAIM-08 Artifact-bound disposition | UNCHANGED | DESIGN + BASELINE_REFLECTED_CLARIFICATION | Approval/disposition must remain connected to candidate, evidence, rule/version, reviewer and consequence. | Original applicant clarification provenance caveat remains. |
| **CDC-CLAIM-09 Correction preserves history** | **UPGRADED** | FUNCTIONAL + `MEASURED_INTERNAL_TECHNICAL_DEMONSTRATION`; correction successor + currentness slice + RUN-003 T-K/T-L | Correction can preserve predecessor history while changing current eligibility; post-evaluation correction prevented stale bounded reliance; historical reliance record remained byte-identical. | Synthetic bounded reliance only; no automatic institutional propagation or real CDC reliance. |
| CDC-CLAIM-10 OPEN supplier replacement | UNCHANGED | DESIGN / OPEN-EXIT TARGET | OPEN defines cross-supplier preservation and semantic-conservation requirements for institution-controlled artifacts. | No executed supplier-replacement release test. |
| CDC-CLAIM-11 Local / sovereign deployment | UNCHANGED FROM LAST FROZEN RECONCILIATION | DESIGN + PREREGISTERED_RELEASE_TARGET; denominator 0 frozen R-CDC-04 release runs in last supplied reconciliation | Architecture and release plan target CDC-controlled infrastructure and bounded offline/no-egress operation. | Do not say offline/no-egress release gate passed unless a newer frozen release run is separately supplied. |
| CDC-CLAIM-12 Phase-A empirical evidence | UNCHANGED HISTORICAL | MEASURED historical: 6 classes, 50/50 detected, 2 unmeasured, §24.5 FAIL | Phase-A measured detection on six classes; `FAIL_AND_INCOMPLETE` remains historical truth. | Not a passed benchmark; raw reproduction traceability remains bounded by prior records. |
| **CDC-CLAIM-13 Currentness / reliance-time revalidation** | **UPGRADED BY SUCCESSOR EVIDENCE; HISTORICAL PHASE-A BLOCK PRESERVED** | Currentness Slice `MEASURED_INTERNAL_TECHNICAL_DEMONSTRATION` (44/44 internal criteria) + RUN-003 41 observations / adjudication 40 satisfied, 1 insufficient | Executable currentness resolution, currentness→authority separation, reliance-time correction refusal, authority-revocation refusal and synthetic reliance gating are measured internal technical demonstrations. Governed propagation is partially supported. | The earlier Phase-A substrate remains historically blocked. Real CDC authority/reliance, distributed propagation, external bypass resistance, production and legal effect remain not established. |

## New owner-frozen integration properties mapped into the claim register

| Property | Status | Primary claim-register home |
|---|---|---|
| CURRENTNESS_TO_AUTHORITY_INTEGRATION | `MEASURED_INTERNAL_TECHNICAL_DEMONSTRATION` | CDC-CLAIM-13; supports CDC-CLAIM-07 mechanics only within synthetic scope |
| GOVERNED_STATE_PROPAGATION_TO_RELIANCE_BOUNDARY | `PARTIALLY_SUPPORTED_INTERNAL_TECHNICAL_DEMONSTRATION` | CDC-CLAIM-13; does not upgrade institutional propagation |
| RELIANCE_ISSUANCE_GATED_BY_CURRENTNESS_AND_AUTHORITY | `MEASURED_INTERNAL_TECHNICAL_DEMONSTRATION` | CDC-CLAIM-13; synthetic bounded reliance only |
| POST_EVALUATION_CORRECTION_PREVENTS_STALE_RELIANCE | `MEASURED_INTERNAL_TECHNICAL_DEMONSTRATION` | CDC-CLAIM-09 + CDC-CLAIM-13 |
| POST_EVALUATION_AUTHORITY_REVOCATION_PREVENTS_RELIANCE | `MEASURED_INTERNAL_TECHNICAL_DEMONSTRATION` | CDC-CLAIM-13 |
| HISTORICAL_RELIANCE_RECORD_PRESERVATION | `MEASURED_INTERNAL_TECHNICAL_DEMONSTRATION` | CDC-CLAIM-09 |

## Non-negotiable claim ceiling

Do not state or imply that RUN-003 established:
- real CDC institutional authority;
- real CDC institutional reliance;
- official CDC issuance or official record formation;
- CDC acceptance;
- production enforcement/conformance;
- legal effect;
- external consumer bypass resistance;
- distributed reliance consistency;
- cross-institution propagation;
- full authority-procedure branch coverage;
- independent validation;
- measured CDC productivity uplift.
