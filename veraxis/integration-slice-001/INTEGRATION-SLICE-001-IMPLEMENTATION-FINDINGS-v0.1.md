# INTEGRATION SLICE 001 — IMPLEMENTATION FINDINGS v0.1

```
classification                        IMPLEMENTATION_OBSERVATION_ONLY
SEMANTIC_CONTROL                      FALSE
SEMANTIC_DESIGN_MODIFIED              FALSE
RESULT_BEARING_CRITERION              FALSE
AUTHORITY_PROCEDURE_FULL_BRANCH_COVERAGE  NOT_ESTABLISHED
A2_RESULT_BEARING_SUCCESS             FALSE
author                                CLAUDE (implementation)
controlling semantic design           CURRENTNESS-TO-RELIANCE-INTEGRATION-SLICE-001-SEMANTIC-DESIGN-v0.4.md
                                      sha256 03ca22e960fa677af0328d2c9595c7842015cf68ca525f8e94c2564dc4afc173
                                      — unchanged by this document
```

This artifact records an implementation observation. It does not reinterpret,
amend, extend or supersede semantic design v0.4, and it confers no semantic
control. Where this document and the semantic design could be read as differing,
the semantic design governs.

## A2 — from declared uncovered to structurally unreachable

A2 was declared uncovered in the semantic design.

Implementation analysis established the stronger observation:

**A2 is structurally unreachable under the frozen procedure because the authority
basis lookup resolves by `(principal_id, scope)`; a principal/scope mismatch
therefore terminates earlier as A11 before the procedure can reach the A2 check.**

### What was observed

Step 3 of the frozen thirteen-step procedure resolves candidate authority bases
by exactly the pair `(principal_id, scope)`. Step 7 then asks whether the
principal is bound to the scope. Any basis that survives step 3 has already
matched both halves of that question, so step 7 cannot fail for a basis that
reached it. A basis naming another scope, or another principal, is not resolvable
at step 3 and the procedure terminates there with A11.

Both mismatch routes were exercised and both returned A11; the matching case
returned A1. No input was found that reaches step 7 in a failing state.

### Disposition

The frozen procedure remains controlling. No authority lookup, step ordering,
A2 binding or A11 binding was changed, no result-bearing case was added, and no
A2 execution path was contrived.

A2 is not counted as an exercised result-bearing branch, and no report of this
slice may state that the authority procedure was exercised across all thirteen
steps. Three of the four declared-uncovered codes — A3, A4, A5 — are reachable
and are exercised by development-only tests. A7 is reached through the frozen
escalation case T-CASE-B. A2 is not reached at all.

Whether the resolution key, the step ordering or the A2 code binding should
change is a semantic question for the designer. It is deliberately not answered
here.
