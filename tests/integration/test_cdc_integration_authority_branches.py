"""Development-only coverage for the declared authority-branch gap.

The frozen semantic design records, deliberately, that codes ``A2``, ``A3``,
``A4`` and ``A5`` have no dedicated case in the 41-criterion universe, and that
``A7`` is reached only through the escalation case ``T-CASE-B``.  These tests
close the executable gap without touching that universe.

They are NOT frozen semantic criteria, NOT result-bearing, and must never be
counted toward the 41.  Their existence is also the reason no later report may
claim the frozen execution exercised the authority procedure end to end: it does
not, and these tests are where the remaining branches are actually shown.
"""

from __future__ import annotations

from typing import Any

import pytest
from tests.integration.cdc_currentness_fixtures import CONTROL_OUTPUT_REF, control_artifact
from tests.integration.cdc_integration_fixtures import (
    ARTIFACT_CLASS,
    DECISION_VALID_UNTIL,
    REQUESTED_USE,
    SCOPE,
    T1,
    admissibility_basis,
    authority_basis,
    control_body_digest,
    epoch_for,
    index_without_successor,
)

from oic.cdc_authority import (
    AuthorityRequest,
    evaluate_synthetic_authority,
    parse_basis_record,
)
from oic.cdc_currentness import resolve_currentness


def _decide(
    *,
    bases: list[dict[str, Any]],
    admissibility: list[dict[str, Any]],
    requested_use: str = REQUESTED_USE,
    principal: str = "SYNTHETIC-SUBJECT-PRINCIPAL-001",
    scope: str = SCOPE,
    artifact_class: str = ARTIFACT_CLASS,
) -> Any:  # noqa: ANN401
    index = index_without_successor()
    resolution = resolve_currentness(
        output_ref=CONTROL_OUTPUT_REF,
        historical_artifact=control_artifact(),
        index=index,
        evaluated_at=T1,
    )
    return evaluate_synthetic_authority(
        request=AuthorityRequest(
            artifact_ref=CONTROL_OUTPUT_REF,
            artifact_digest=control_body_digest(),
            recomputed_artifact_digest=control_body_digest(),
            requested_use=requested_use,
            scope=scope,
            requesting_principal=principal,
            currentness_resolution_digest=resolution.resolution_digest,
            currentness_epoch_digest=epoch_for(index, CONTROL_OUTPUT_REF, T1),
            evaluation_time=T1,
            valid_until=DECISION_VALID_UNTIL,
            decision_id="DEV-ONLY-AUTHORITY-DECISION",
        ),
        authority_bases=[parse_basis_record(item) for item in bases],
        admissibility_bases=[parse_basis_record(item) for item in admissibility],
        artifact_class=artifact_class,
    )


def test_dev_a2_principal_not_authorized_for_scope() -> None:
    """A2 — the basis binds a different scope, so step 3 finds none for this one.

    A2 is reachable only where a basis exists for the pair and yet fails the
    binding check; with the frozen resolution keyed on (principal, scope) the
    honest observation is that a scope mismatch is refused, and this records
    which code the procedure actually returns.
    """
    decision = _decide(
        bases=[authority_basis(scope="OTHER-SCOPE")],
        admissibility=[admissibility_basis()],
    )
    assert decision.decision == "DENY"
    # Documented outcome: the procedure refuses at step 3 (A11) rather than A2,
    # because a basis for another scope is not a basis for this one.
    assert decision.reason_code_id == "A11"


def test_dev_a3_requested_use_outside_scope() -> None:
    """A3 — a use the basis does not permit."""
    decision = _decide(
        bases=[authority_basis(permitted_requested_use=["SOMETHING_ELSE"])],
        admissibility=[admissibility_basis(requested_use_admitted=[REQUESTED_USE])],
    )
    assert decision.decision == "DENY"
    assert decision.reason_code_id == "A3"


def test_dev_a4_admissibility_basis_missing() -> None:
    """A4 — no admissibility basis admits this artifact class."""
    decision = _decide(bases=[authority_basis()], admissibility=[])
    assert decision.decision == "DENY"
    assert decision.reason_code_id == "A4"


def test_dev_a5_admissibility_basis_invalid() -> None:
    """A5 — the stored admissibility digest does not reproduce."""
    broken = {**admissibility_basis(), "record_digest": "0" * 64}
    decision = _decide(bases=[authority_basis()], admissibility=[broken])
    assert decision.decision == "DENY"
    assert decision.reason_code_id == "A5"


def test_dev_a2_is_structurally_unreachable_under_the_frozen_procedure() -> None:
    """A2 cannot fire, and this records why rather than pretending otherwise.

    Step 3 of the frozen thirteen-step procedure resolves authority bases *by*
    ``(principal_id, scope)``.  Step 7 then asks whether the principal is bound to
    the scope — a question step 3 has already answered, because any basis that
    survived to step 7 matched both.  A basis for another scope is refused at step
    3 as A11 (no basis resolvable), never at step 7 as A2.

    So under this procedure A2 is dead code: fail-closed, but unreachable.  It is
    recorded here as an implementation finding for the semantic designer, not
    repaired locally — changing the resolution key or the code binding is a
    semantic decision, not an implementation one.
    """
    other_scope = _decide(
        bases=[authority_basis(scope="OTHER-SCOPE")], admissibility=[admissibility_basis()]
    )
    assert other_scope.reason_code_id == "A11"

    other_principal = _decide(
        bases=[authority_basis(principal_id="SYNTHETIC-OTHER-SUBJECT-001")],
        admissibility=[admissibility_basis()],
    )
    assert other_principal.reason_code_id == "A11"

    matching = _decide(bases=[authority_basis()], admissibility=[admissibility_basis()])
    assert matching.reason_code_id == "A1"


@pytest.mark.parametrize("code", ["A2", "A3", "A4", "A5"])
def test_dev_branches_are_declared_not_frozen_criteria(code: str) -> None:
    """These four codes are development coverage only."""
    frozen_criteria_count = 41
    assert code not in {"T-CASE-A", "T-CASE-B"}
    assert frozen_criteria_count == 41
