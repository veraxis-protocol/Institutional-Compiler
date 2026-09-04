"""Mutation tests: each named weakening of the evaluator must be caught by the corpus.

A test suite that still passes against a broken evaluator is not evidence. Each case
here rewrites one exact line of `src/oic/admission.py`, loads the result as a separate
module, and requires the frozen 38-vector corpus to reject it. A mutation that survives
names a property nothing actually checks.

The mutations are applied to a copy in memory. The real module is never modified.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

# The probe bank is a test-only sibling module and tests/ is not a package, so it is
# loaded from its own directory rather than by package name.
sys.path.insert(0, str(Path(__file__).parent))
try:
    from admission_probes import PROBES, run_probes
finally:
    sys.path.pop(0)

pytestmark = pytest.mark.contract

_ROOT = Path(__file__).resolve().parents[2]
_MODULE_PATH = _ROOT / "src/oic/admission.py"
_VECTORS = json.loads(
    (_ROOT / "design/admission-boundary-001/TEST-VECTORS-v0.2.json").read_text(encoding="utf-8")
)["vectors"]


def _mutate(source: str, old: str, new: str) -> str:
    """Replace exactly one occurrence, refusing a mutation that would silently no-op."""
    count = source.count(old)
    if count != 1:
        raise AssertionError(f"mutation target appears {count} times, expected exactly 1: {old!r}")
    return source.replace(old, new, 1)


def _load_mutant(name: str, old: str, new: str) -> ModuleType:
    source = _mutate(_MODULE_PATH.read_text(encoding="utf-8"), old, new)
    module_name = f"_oic_admission_mutant_{name}"
    spec = importlib.util.spec_from_loader(module_name, loader=None)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    module.__file__ = str(_MODULE_PATH)
    sys.modules[module_name] = module
    try:
        exec(compile(source, str(_MODULE_PATH), "exec"), module.__dict__)  # noqa: S102
    finally:
        sys.modules.pop(module_name, None)
    return module


def _corpus_rejects(module: ModuleType) -> bool:
    """True when the mutant fails at least one frozen vector, exception included."""
    canonical_json: Callable[[Any], bytes] = module.canonical_json
    evaluate: Callable[[bytes], Any] = module.evaluate_admission_bytes
    for vector in _VECTORS:
        try:
            receipt = evaluate(canonical_json(vector["executable_input"]))
        except Exception:  # any failure at all is a rejection of the mutant
            return True
        if receipt.to_json() != vector["expected_receipt"]:
            return True
    return False


def _rejects(module: ModuleType) -> bool:
    """True when the frozen corpus or the probe bank catches this mutant.

    The corpus alone is a design corpus: it has no non-canonical byte vector and no
    interval-boundary vector, so several real weakenings are invisible to it. The probe
    bank states those properties explicitly. Both are part of the contract; a mutation
    either is caught, or it names something nothing checks.
    """
    return _corpus_rejects(module) or bool(run_probes(module))


# One (name, exact original line, mutated line) per weakening the corpus must catch.
MUTATIONS: tuple[tuple[str, str, str], ...] = (
    (
        "m01_accept_a_candidate_with_no_source_anchor",
        "    if not anchors:\n        return AdmissionState.CANDIDATE_INPUT_INVALID\n",
        "    if False:\n        return AdmissionState.CANDIDATE_INPUT_INVALID\n",
    ),
    (
        "m02_accept_an_anchor_naming_a_different_source",
        '    if any(anchor["source_id"] != source_id for anchor in anchors):\n',
        "    if False:\n",
    ),
    (
        "m03_check_freshness_before_availability",
        '    if observation["availability"] == "UNAVAILABLE":\n',
        '    if observation["freshness"] == "STALE":\n'
        "        return AdmissionState.AUTHORITY_EVIDENCE_STALE\n"
        '    if observation["availability"] == "UNAVAILABLE":\n',
    ),
    (
        "m04_never_emit_source_not_registered",
        '    if registration["registered"] is False:\n',
        "    if False:\n",
    ),
    (
        "m05_treat_an_unregistered_source_as_registered_when_evidence_exists",
        '    if registration["registered"] is False:\n'
        "        return AdmissionState.SOURCE_NOT_REGISTERED\n",
        '    if registration["registered"] is False and not raw_evidence:\n'
        "        return AdmissionState.SOURCE_NOT_REGISTERED\n",
    ),
    (
        "m06_fire_version_mismatch_on_any_differing_evidence",
        "    if raw_evidence and not version_bound:\n"
        "        return AdmissionState.SOURCE_VERSION_MISMATCH\n",
        "    if len(version_bound) != len(relevant):\n"
        "        return AdmissionState.SOURCE_VERSION_MISMATCH\n",
    ),
    (
        "m07_ignore_the_candidate_anchor_content_hash",
        '    if any(anchor["content_hash"] != source_digest for anchor in anchors):\n',
        "    if False:\n",
    ),
    (
        "m08_accept_evidence_that_binds_no_registered_digest",
        "    bound = tuple(item for item in version_bound if item.binds_digest(source_digest))\n"
        "    if raw_evidence and not bound:\n"
        "        return AdmissionState.SOURCE_DIGEST_MISMATCH\n",
        "    bound = version_bound\n"
        "    if False:\n"
        "        return AdmissionState.SOURCE_DIGEST_MISMATCH\n",
    ),
    (
        "m09_collapse_missing_authority_into_the_generic_state",
        "    if not bound:\n        return AdmissionState.MISSING_AUTHORITY_EVIDENCE\n",
        "    if not bound:\n        return AdmissionState.ADMISSION_NOT_ESTABLISHED\n",
    ),
    (
        "m10_ignore_the_source_registration_scope",
        "    if not _covers(registration, jurisdiction, applicability):\n",
        "    if False:\n",
    ),
    (
        "m11_treat_every_scope_as_covering",
        '    return record["jurisdiction"] == jurisdiction and applicability in scope\n',
        "    return True\n",
    ),
    (
        "m12_admit_at_the_instant_effectiveness_begins_minus_nothing",
        "    def not_yet_effective(self, at: datetime) -> bool:\n"
        "        return at < self.effective_from\n",
        "    def not_yet_effective(self, at: datetime) -> bool:\n"
        "        return at <= self.effective_from\n",
    ),
    (
        "m13_close_the_effective_interval_at_its_end",
        "        return self.effective_until is not None and at >= self.effective_until\n",
        "        return self.effective_until is not None and at > self.effective_until\n",
    ),
    (
        "m14_delay_supersession_by_one_instant",
        "        return self.superseded_at is not None and at >= self.superseded_at\n",
        "        return self.superseded_at is not None and at > self.superseded_at\n",
    ),
    (
        "m15_delay_revocation_by_one_instant",
        "        return self.revoked_at is not None and at >= self.revoked_at\n",
        "        return self.revoked_at is not None and at > self.revoked_at\n",
    ),
    (
        "m16_ignore_a_revoked_warrant_status",
        '            or self.warrant["status"] == "REVOKED"\n',
        "            or False\n",
    ),
    (
        "m17_never_find_a_conflict",
        "    if len({item.authority_basis_ref for item in operative}) >= _CONFLICT_THRESHOLD:\n",
        "    if False:\n",
    ),
    (
        "m18_resolve_a_conflict_by_picking_a_winner",
        "        return AdmissionState.CONFLICTING_AUTHORITY\n",
        "        return AdmissionState.ADMITTED\n",
    ),
    (
        "m19_fail_open_instead_of_admission_not_established",
        "    if not qualifying:\n        return AdmissionState.ADMISSION_NOT_ESTABLISHED\n",
        "    if not qualifying:\n        return AdmissionState.ADMITTED\n",
    ),
    (
        "m20_accept_non_canonical_bytes",
        "    if canonical_json(document) != payload:\n",
        "    if False:\n",
    ),
    (
        "m21_skip_the_evidence_digest_recomputation",
        "        if computed != recorded:\n",
        "        if False:\n",
    ),
    (
        "m22_accept_a_caller_supplied_ruleset_digest",
        '    if ruleset["ruleset_digest"] != RULESET_DIGEST:\n',
        "    if False:\n",
    ),
    (
        "m23_hash_the_receipt_without_omitting_only_the_receipt_id",
        '    receipt_id = f"{_RECEIPT_ID_PREFIX}{_digest_of_projection(projection)}"\n',
        '    receipt_id = f"{_RECEIPT_ID_PREFIX}{_digest_of_projection(sorted(projection))}"\n',
    ),
    (
        "m24_aggregate_the_evidence_digest_without_the_individual_digests",
        '        "evidence_digest": _digest_of_projection(list(evidence)),\n',
        '        "evidence_digest": _digest_of_projection(\n'
        '            [_without(item, "evidence_digest") for item in evidence]\n'
        "        ),\n",
    ),
)


MINIMUM_MUTATIONS = 17


def test_the_mutation_set_is_at_least_the_required_size() -> None:
    assert len(MUTATIONS) >= MINIMUM_MUTATIONS
    assert len({name for name, _, _ in MUTATIONS}) == len(MUTATIONS)


def test_the_probe_bank_is_satisfied_by_the_real_evaluator() -> None:
    """Without this, a probe bank that rejects everything would kill every mutant."""
    from oic import admission

    assert run_probes(admission) == []
    assert len(PROBES) > len(MUTATIONS)


@pytest.mark.parametrize(("name", "old", "new"), MUTATIONS, ids=[m[0] for m in MUTATIONS])
def test_the_corpus_kills_the_mutant(name: str, old: str, new: str) -> None:
    module = _load_mutant(name, old, new)
    assert _rejects(module), (
        f"mutation {name} survived: nothing in the corpus or the probe bank checks this"
    )


def test_the_unmutated_module_is_not_rejected() -> None:
    """The control. Without it, a harness that rejects everything would look perfect."""
    module = _load_mutant("control", "    # 15. Eligible", "    # 15. (control) Eligible")
    assert not _corpus_rejects(module)
    assert run_probes(module) == []
