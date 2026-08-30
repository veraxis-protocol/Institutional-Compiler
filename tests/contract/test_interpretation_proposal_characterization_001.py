"""Contract tests for Interpretation Proposal Characterization 001.

Three things are proved here. That the instrument runs against the frozen artifacts and
nothing else. That the answer key never reaches the provider — the real prompt is rendered
for every specimen and searched for gold, authority evidence, warrants and reason codes.
And that the metrics detect the defects they exist to detect, demonstrated on synthetic
proposals and then re-demonstrated by mutating the instrument and requiring the tests to
notice.
"""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from jsonschema.validators import Draft202012Validator

from oic.interpretation_proposal import (
    FORCE_VALUES,
    SLOT_VOCABULARY,
    AdmittedCandidateBinding,
    propose_interpretation,
)
from oic.model_provider import ModelRequest, ModelResponse

pytestmark = pytest.mark.contract

STARTING_SHA = "3194ef0fbe465a583f797aa52a35131f50b18aa0"
CORPUS_DIR = Path("benchmarks/characterization/interpretation-proposal-001")
CORPUS_RELPATH = CORPUS_DIR / "CORPUS-v0.1.json"
FREEZE_RELPATH = CORPUS_DIR / "CORPUS-FREEZE-v0.1.json"
DESIGN = Path("design/institutional-ir-001")
HARNESS_RELPATH = Path("scripts/characterize_interpretation_proposal.py")

PROPOSAL_SCHEMA_SHA256 = "0e71dc3fbd20d2b025549df565314c0f90f69d36ec2eb874915a865731c437df"
RULESET_SHA256 = "8ba398eb20d346d66ce49c0f638babe2167930a07c3bd2946757fa41d6ccb114"
RULESET_CANONICAL_DIGEST = "sha256:e3751aac77b2ef0a0cdad99aff44d47861cd6d7d39d044e485a520a452e75b71"
IR_CORPUS_SHA256 = "5761b82cc67c8bfb139689d04c7ca36283d0c6e63fd8f82199b8a1fa9d013358"
IR_FREEZE_SHA256 = "a396e291add85e839d84972766dbb7b00d1ed9c9294136d201d3336d69a5f331"
NVIDIA_ADAPTER_SHA256 = "c1c02303cec29eaef8cb96d1baeec735ef724d9c8a06e20a61b91388d4350339"

SPECIMEN_COUNT = 29
RUNS_PER_SPECIMEN = 3
PLANNED_REQUESTS = 87

SELECTED_IDS = (
    "IIR-001", "IIR-002", "IIR-003", "IIR-004", "IIR-005", "IIR-006", "IIR-007", "IIR-008",
    "IIR-009", "IIR-010", "IIR-011", "IIR-012", "IIR-013", "IIR-014", "IIR-015", "IIR-016",
    "IIR-017", "IIR-018", "IIR-023", "IIR-024", "IIR-025", "IIR-026", "IIR-027", "IIR-028",
    "IIR-029", "IIR-030", "IIR-031", "IIR-032", "IIR-035",
)  # fmt: skip

NON_ADMITTED_IR_BOUNDARY_IDS = ("IIR-036", "IIR-037", "IIR-038", "IIR-039", "IIR-040")


def _load(repo_root: Path, relpath: Path) -> dict[str, Any]:
    document: dict[str, Any] = json.loads((repo_root / relpath).read_text(encoding="utf-8"))
    return document


def _harness(repo_root: Path) -> ModuleType:
    path = repo_root / HARNESS_RELPATH
    spec = importlib.util.spec_from_file_location("_characterize_proposal", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    return module


@pytest.fixture(scope="module")
def corpus(repo_root: Path) -> dict[str, Any]:
    return _load(repo_root, CORPUS_RELPATH)


@pytest.fixture(scope="module")
def freeze(repo_root: Path) -> dict[str, Any]:
    return _load(repo_root, FREEZE_RELPATH)


@pytest.fixture(scope="module")
def harness(repo_root: Path) -> ModuleType:
    return _harness(repo_root)


class RecordingProvider:
    """Captures the exact request body, so prompt-leak claims are checked not asserted."""

    def __init__(self, content: str = '{"proposed_assertions":[]}') -> None:
        self.calls: list[ModelRequest] = []
        self.content = content

    def complete(self, request: ModelRequest) -> ModelResponse:
        self.calls.append(request)
        return ModelResponse(
            provider="fake", model="fake", content=self.content, request_id=None, raw={}
        )


def _rendered_prompt(specimen: dict[str, Any], *, include_unit_type: bool = False) -> str:
    provider = RecordingProvider()
    candidate = specimen["candidate"]
    admission = specimen["admission"]
    propose_interpretation(
        binding=AdmittedCandidateBinding(
            admission_receipt_id=admission["admission_receipt_id"],
            admission_state=admission["admission_state"],
            candidate_unit_id=admission["candidate_unit_id"],
            candidate_projection_digest=admission["candidate_projection_digest"],
            candidate_span=candidate["candidate_span"],
            provisional_unit_type=candidate["unit_type"] if include_unit_type else None,
        ),
        provider=provider,
        proposer_id="contract-test",
    )
    request = provider.calls[0]
    return request.system_prompt + "\n" + request.user_prompt


# ---------------------------------------------------------------------------
# 1-4. Frozen governing artifacts
# ---------------------------------------------------------------------------


def test_the_starting_sha_is_pinned_and_present(repo_root: Path) -> None:
    resolved = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"{STARTING_SHA}^{{commit}}"],
        cwd=repo_root,
        check=False,
        capture_output=True,
    )
    assert resolved.returncode == 0
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", STARTING_SHA, "HEAD"],
        cwd=repo_root,
        check=False,
        capture_output=True,
    )
    assert ancestor.returncode == 0, "the recorded starting SHA is not an ancestor of HEAD"


@pytest.mark.parametrize(
    ("relpath", "digest"),
    [
        (DESIGN / "INTERPRETATION-PROPOSAL-v0.1.schema.json", PROPOSAL_SCHEMA_SHA256),
        (DESIGN / "INTERPRETATION-RULESET-v0.1.json", RULESET_SHA256),
        (DESIGN / "TEST-VECTORS-v0.1.json", IR_CORPUS_SHA256),
        (DESIGN / "TEST-VECTORS-FREEZE-v0.1.json", IR_FREEZE_SHA256),
        (Path("src/oic/nvidia_nim.py"), NVIDIA_ADAPTER_SHA256),
    ],
)
def test_governing_artifacts_are_byte_identical(
    repo_root: Path, relpath: Path, digest: str
) -> None:
    assert hashlib.sha256((repo_root / relpath).read_bytes()).hexdigest() == digest, relpath


def test_the_interpretation_ruleset_canonical_digest_is_unchanged(repo_root: Path) -> None:
    ruleset = _load(repo_root, DESIGN / "INTERPRETATION-RULESET-v0.1.json")
    canonical = json.dumps(
        ruleset, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    assert "sha256:" + hashlib.sha256(canonical).hexdigest() == RULESET_CANONICAL_DIGEST


def test_the_institutional_ir_design_package_is_untouched(repo_root: Path) -> None:
    changed = subprocess.run(
        ["git", "diff", "--name-only", f"{STARTING_SHA}...HEAD", "--", DESIGN.as_posix()],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert changed == ""


def test_the_frozen_admission_and_candidate_layers_are_untouched(repo_root: Path) -> None:
    changed = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            f"{STARTING_SHA}...HEAD",
            "--",
            "src/oic/admission.py",
            "src/oic/admission_specs",
            "src/oic/candidate_extraction.py",
            "src/oic/nvidia_nim.py",
            "src/oic/model_provider.py",
            "schemas",
            "benchmarks/characterization/admission-runtime-freeze-001",
            "benchmarks/characterization/candidate-layer-freeze-001",
        ],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert changed == ""


# ---------------------------------------------------------------------------
# 5-7. The carried corpus
# ---------------------------------------------------------------------------


def test_the_corpus_is_byte_frozen(repo_root: Path, freeze: dict[str, Any]) -> None:
    raw = (repo_root / CORPUS_RELPATH).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == freeze["corpus_sha256"]
    assert len(raw) == freeze["corpus_bytes"]
    assert freeze["live_run_executed"] is False
    assert freeze["model_call_made"] is False


def test_exactly_twenty_nine_admitted_specimens_are_carried(corpus: dict[str, Any]) -> None:
    specimens = corpus["specimens"]
    assert len(specimens) == corpus["specimen_count"] == SPECIMEN_COUNT
    assert tuple(item["specimen_id"] for item in specimens) == SELECTED_IDS
    for specimen in specimens:
        assert specimen["admission"]["admission_state"] == "ADMITTED", specimen["specimen_id"]
        assert specimen["admission"]["reason_code"] == "OIC-ADM-0000"


def test_exactly_eighty_seven_live_requests_are_planned(
    corpus: dict[str, Any], freeze: dict[str, Any]
) -> None:
    assert corpus["runs_per_specimen"] == RUNS_PER_SPECIMEN
    assert corpus["planned_live_requests"] == PLANNED_REQUESTS
    assert corpus["specimen_count"] * corpus["runs_per_specimen"] == PLANNED_REQUESTS
    assert freeze["planned_live_requests"] == PLANNED_REQUESTS


def test_no_non_admitted_ir_boundary_vector_enters_the_live_corpus(
    corpus: dict[str, Any],
) -> None:
    carried = {specimen["specimen_id"] for specimen in corpus["specimens"]}
    assert carried.isdisjoint(NON_ADMITTED_IR_BOUNDARY_IDS)


def test_carried_specimens_preserve_the_design_corpus_exactly(
    repo_root: Path, corpus: dict[str, Any]
) -> None:
    source = _load(repo_root, DESIGN / "TEST-VECTORS-v0.1.json")
    by_id = {vector["vector_id"]: vector for vector in source["vectors"]}
    for specimen in corpus["specimens"]:
        vector = by_id[specimen["specimen_id"]]
        receipt = vector["admission_receipts"][0]
        candidate = vector["admission_inputs"][0]["candidate"]
        assert specimen["candidate"]["candidate_span"] == candidate["candidate_span"]
        assert specimen["candidate"]["unit_id"] == candidate["unit_id"]
        assert specimen["admission"]["admission_receipt_id"] == receipt["admission_receipt_id"]
        assert specimen["admission"]["source_digest"] == receipt["source_digest"]
        assert specimen["admission"]["source_version"] == receipt["source_version"]


# ---------------------------------------------------------------------------
# 8-10. The answer key never reaches the provider
# ---------------------------------------------------------------------------


def test_the_prompt_is_a_pure_function_of_the_admitted_proposition(
    corpus: dict[str, Any],
) -> None:
    """The strongest form of "the model never sees the answer key".

    Every specimen's prompt is rendered for real and its own candidate span removed. What
    remains must be byte-identical across all 29 specimens. If any gold value, expected
    status, expected force, reference kind, admission binding or authority fact could reach
    the provider, the remainders would differ, because the gold differs per specimen.
    """
    remainders: dict[str, str] = {}
    for specimen in corpus["specimens"]:
        prompt = _rendered_prompt(specimen)
        span = specimen["candidate"]["candidate_span"]
        assert span in prompt, specimen["specimen_id"]
        remainders[specimen["specimen_id"]] = prompt.replace(span, "<PROPOSITION>")
    distinct = set(remainders.values())
    assert len(distinct) == 1, (
        "the request body varies with the specimen beyond its proposition: "
        f"{sorted(remainders)[:3]}"
    )


def test_no_gold_token_count_varies_with_the_specimen(corpus: dict[str, Any]) -> None:
    """Gold vocabulary appears only in the fixed instructions, never in specimen-dependent
    quantity.

    The status and reference-kind words do occur in the prompt: once each, in the sentences
    that forbid a status and enumerate the reference kinds. What would betray a leak is a
    count that moves with the specimen's own gold. Word boundaries are used so
    ``DEFINITION`` inside ``CONSTITUTIVE_DEFINITION`` and ``ESTABLISHED`` inside
    ``NOT_ESTABLISHED`` are not miscounted.
    """
    tokens = (
        "ESTABLISHED",
        "AMBIGUOUS",
        "NOT_ESTABLISHED",
        "NOT_APPLICABLE",
        "INTERNAL_PROVISION",
        "EXTERNAL_DOCUMENT",
        "DEFINITION",
        "UNCLASSIFIED",
        "OPEN",
        "CLOSED_BY_WARRANT",
    )
    counts: dict[str, set[int]] = {token: set() for token in tokens}
    for specimen in corpus["specimens"]:
        prompt = _rendered_prompt(specimen)
        for token in tokens:
            counts[token].add(len(re.findall(rf"\b{token}\b", prompt)))
    for token, observed in counts.items():
        assert len(observed) == 1, f"{token} occurrence count varies with the specimen"
    # The status vocabulary is mentioned exactly once, in the sentence forbidding it.
    for token in ("ESTABLISHED", "AMBIGUOUS", "NOT_ESTABLISHED", "NOT_APPLICABLE"):
        assert counts[token] == {1}, token
    # The exception-closure vocabulary belongs to canonicalization and is never mentioned.
    for token in ("OPEN", "CLOSED_BY_WARRANT"):
        assert counts[token] == {0}, token


def test_no_gold_slot_status_or_alternative_marking_reaches_the_prompt(
    corpus: dict[str, Any],
) -> None:
    """Gold slot values are quoted from the proposition, so their presence proves nothing.

    What would be a leak is the gold *judgement about* them: which slots are established,
    which are ambiguous, and what their alternatives are.
    """
    for specimen in corpus["specimens"]:
        prompt = _rendered_prompt(specimen)
        gold = specimen["gold"]
        for slot, entry in gold["expected_slots"].items():
            assert f"{slot}: {entry['status']}" not in prompt, (specimen["specimen_id"], slot)
            assert f"{slot}={entry['status']}" not in prompt, (specimen["specimen_id"], slot)
            for alternative in entry["alternatives"]:
                assert f"alternative: {alternative}" not in prompt
                assert f"alternatives: {alternative}" not in prompt
        assert gold["exception_closure"] not in prompt.replace("PROPOSITION", "")


def test_no_authority_evidence_or_admission_metadata_is_sent(corpus: dict[str, Any]) -> None:
    for specimen in corpus["specimens"]:
        prompt = _rendered_prompt(specimen)
        admission = specimen["admission"]
        for leak in (
            admission["admission_receipt_id"],
            admission["candidate_unit_id"],
            admission["candidate_projection_digest"],
            admission["source_id"],
            admission["source_digest"],
            admission["source_version"] if len(admission["source_version"]) > 2 else "###",
            admission["reason_code"],
            admission["evaluation_time"],
        ):
            assert leak not in prompt, (specimen["specimen_id"], leak)
        for token in (
            "authority_evidence",
            "admission_warrant",
            "authority_basis_ref",
            "admission_authority_id",
            "delegation_basis_ref",
            "evaluation_scope",
            "applicability_scope",
        ):
            assert token not in prompt, (specimen["specimen_id"], token)


def test_no_interpretation_evidence_or_warrant_is_sent(corpus: dict[str, Any]) -> None:
    for specimen in corpus["specimens"]:
        prompt = _rendered_prompt(specimen)
        for token in (
            "interpretation_evidence",
            "INSTITUTIONAL_INTERPRETATION_WARRANT",
            "REGISTERED_INTERPRETATION_RULE",
            "DETERMINISTIC_NORMALIZATION",
            "interpretation_basis",
            "permitted_operations",
        ):
            assert token not in prompt, (specimen["specimen_id"], token)


def test_the_prompt_carries_the_proposition_and_the_vocabulary(corpus: dict[str, Any]) -> None:
    for specimen in corpus["specimens"]:
        prompt = _rendered_prompt(specimen)
        assert specimen["candidate"]["candidate_span"] in prompt
        for slot in SLOT_VOCABULARY:
            assert slot in prompt
        for force in FORCE_VALUES:
            assert force in prompt


def test_the_preregistered_arm_omits_the_provisional_unit_type(corpus: dict[str, Any]) -> None:
    assert corpus["include_provisional_unit_type_in_prompt"] is False
    for specimen in corpus["specimens"]:
        prompt = _rendered_prompt(specimen)
        assert "An earlier stage proposed" not in prompt
    # The second arm exists for a later A/B and is not run here.
    hinted = _rendered_prompt(corpus["specimens"][0], include_unit_type=True)
    assert "An earlier stage proposed" in hinted


# ---------------------------------------------------------------------------
# 11-12. Envelope authority
# ---------------------------------------------------------------------------


def test_produced_envelopes_validate_against_the_frozen_proposal_schema(
    repo_root: Path, corpus: dict[str, Any]
) -> None:
    """The production module enforces the contract in code; this proves it implies the
    frozen design schema without packaging a copy of that schema into the wheel."""
    validator = Draft202012Validator(
        _load(repo_root, DESIGN / "INTERPRETATION-PROPOSAL-v0.1.schema.json")
    )
    payload = json.dumps(
        {
            "proposed_assertions": [
                {
                    "slot": "normative_force",
                    "proposed_value": "OBLIGATION",
                    "proposed_source_quote": None,
                },
                {
                    "slot": "action",
                    "proposed_value": "retain",
                    "proposed_source_quote": "retain",
                    "proposed_material_qualifiers": ["for seven years"],
                },
            ],
            "proposed_unresolved_references": [
                {"reference_text": "Policy B", "reference_kind": "EXTERNAL_DOCUMENT"}
            ],
        }
    )
    for specimen in corpus["specimens"]:
        candidate = specimen["candidate"]
        admission = specimen["admission"]
        result = propose_interpretation(
            binding=AdmittedCandidateBinding(
                admission_receipt_id=admission["admission_receipt_id"],
                admission_state="ADMITTED",
                candidate_unit_id=admission["candidate_unit_id"],
                candidate_projection_digest=admission["candidate_projection_digest"],
                candidate_span=candidate["candidate_span"],
            ),
            provider=RecordingProvider(payload),
            proposer_id="contract-test",
        )
        errors = list(validator.iter_errors(result.proposal))
        assert errors == [], (specimen["specimen_id"], errors[0].message if errors else "")
        assert result.proposal["admission_receipt_id"] == admission["admission_receipt_id"]
        assert result.proposal["candidate_unit_id"] == admission["candidate_unit_id"]
        assert (
            result.proposal["candidate_projection_digest"]
            == admission["candidate_projection_digest"]
        )


# ---------------------------------------------------------------------------
# The harness: preflight, metrics on synthetic fixtures, determinism
# ---------------------------------------------------------------------------


def test_the_harness_preflight_verifies_the_frozen_artifacts(harness: ModuleType) -> None:
    plan = harness.preflight()
    assert len(plan.specimens) == SPECIMEN_COUNT
    assert plan.corpus["planned_live_requests"] == PLANNED_REQUESTS
    digests = plan.digests
    assert digests["proposal_schema_sha256"] == PROPOSAL_SCHEMA_SHA256
    assert digests["interpretation_ruleset_canonical_digest"] == RULESET_CANONICAL_DIGEST


def test_an_offline_run_constructs_no_provider(repo_root: Path, harness: ModuleType) -> None:
    del repo_root
    assert harness.main([]) == 0


def _fixture(harness: ModuleType, specimen_id: str) -> Any:  # noqa: ANN401 - the harness is loaded dynamically
    plan = harness.preflight()
    return next(item for item in plan.specimens if item.specimen_id == specimen_id)


def _attempt(harness: ModuleType, specimen_id: str, payload: dict[str, Any], run: int = 1) -> Any:  # noqa: ANN401 - the harness is loaded dynamically
    proposal = {
        "proposal_id": f"iip-{specimen_id.lower()}-{run}",
        "proposal_schema_id": "OIC-INTERPRETATION-PROPOSAL-v0.1",
        "admission_receipt_id": "admrec-sha256:" + "a" * 64,
        "candidate_unit_id": "cnu-" + "b" * 24,
        "candidate_projection_digest": "sha256:" + "c" * 64,
        "proposer": {"proposer_kind": "MODEL", "proposer_id": "fixture"},
        "proposal_state": "PROVISIONAL",
        "epistemic_state": "uncertain",
        **payload,
    }
    return harness.Attempt(
        specimen_id=specimen_id,
        run_index=run,
        outcome=harness.ACCEPTED,
        proposal=proposal,
        provider="fake",
        model="fake",
    )


def _slot(
    slot: str,
    value: str | None,
    quote: str | None = None,
    **extra: Any,  # noqa: ANN401 - fixture builder for arbitrary JSON payloads
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "slot": slot,
        "proposed_value": value,
        "proposed_source_quote": quote,
    }
    entry.update(extra)
    return entry


def test_metric_a_separates_provider_errors_from_boundary_rejections(
    harness: ModuleType,
) -> None:
    attempts = [
        _attempt(harness, "IIR-001", {"proposed_assertions": []}),
        harness.Attempt("IIR-001", 2, harness.PROVIDER_ERROR, error_type="ModelProviderError"),
        harness.Attempt(
            "IIR-001",
            3,
            harness.BOUNDARY_REJECTED,
            error_type="ProposalBoundaryError",
            error_message="bad json",
        ),
    ]
    metric = harness.metric_a_provider_boundary(attempts, PLANNED_REQUESTS)
    assert metric["requests_planned"] == PLANNED_REQUESTS
    assert metric["provider_errors"] == 1
    assert metric["proposal_boundary_rejected"] == 1
    assert metric["accepted_proposals"] == 1
    assert metric["provider_accepted"] == 2


def test_metric_b_does_not_call_an_empty_proposal_a_provider_failure(
    harness: ModuleType,
) -> None:
    specimen = _fixture(harness, "IIR-001")
    attempts = [
        _attempt(harness, "IIR-001", {"proposed_assertions": []}, run=1),
        _attempt(harness, "IIR-001", {"proposed_assertions": [_slot("action", "retain")]}, run=2),
    ]
    metric = harness.metric_b_proposal_presence([specimen], attempts)
    entry = metric["IIR-001"]
    assert entry["accepted_runs"] == 2
    assert entry["empty_proposal_runs"] == 1
    assert entry["runs_with_at_least_one_assertion"] == 1


def test_metric_c_reports_a_confusion_matrix_not_an_accuracy(harness: ModuleType) -> None:
    advisory = _fixture(harness, "IIR-027")
    permission = _fixture(harness, "IIR-028")
    attempts = [
        _attempt(
            harness, "IIR-027", {"proposed_assertions": [_slot("normative_force", "OBLIGATION")]}
        ),
        _attempt(
            harness, "IIR-028", {"proposed_assertions": [_slot("normative_force", "OBLIGATION")]}
        ),
        _attempt(harness, "IIR-028", {"proposed_assertions": []}, run=2),
    ]
    metric = harness.metric_c_force([advisory, permission], attempts)
    matrix = metric["confusion_matrix"]
    assert matrix["ADVISORY"]["OBLIGATION"] == 1
    assert matrix["PERMISSION"]["OBLIGATION"] == 1
    assert matrix["PERMISSION"]["OMITTED"] == 1
    assert "accuracy" not in metric
    assert len(metric["mismatch_instances"]) == 3


def test_metric_d_detects_an_invented_bearer_on_passive_voice(harness: ModuleType) -> None:
    specimen = _fixture(harness, "IIR-029")
    assert specimen.gold_slot("bearer")["status"] == "NOT_ESTABLISHED"
    attempts = [
        _attempt(
            harness,
            "IIR-029",
            {"proposed_assertions": [_slot("bearer", "the finance team")]},
        )
    ]
    metric = harness.metric_d_invention([specimen], attempts)
    assert metric["counts"]["invented_bearer_on_passive_voice"] == 1
    assert metric["instances"][0]["proposed_value"] == "the finance team"


def test_metric_d_detects_an_invented_business_convention(harness: ModuleType) -> None:
    specimen = _fixture(harness, "IIR-032")
    attempts = [
        _attempt(
            harness,
            "IIR-032",
            {"proposed_assertions": [_slot("condition", "during normal business hours")]},
        )
    ]
    metric = harness.metric_d_invention([specimen], attempts)
    assert metric["counts"]["invented_condition"] == 1


def test_metric_e_distinguishes_omission_from_incompatibility(harness: ModuleType) -> None:
    specimen = _fixture(harness, "IIR-001")
    attempts = [
        _attempt(
            harness,
            "IIR-001",
            {"proposed_assertions": [_slot("bearer", "The Records Officer")]},
            run=1,
        ),
        _attempt(
            harness, "IIR-001", {"proposed_assertions": [_slot("bearer", "somebody else")]}, run=2
        ),
        _attempt(harness, "IIR-001", {"proposed_assertions": []}, run=3),
    ]
    metric = harness.metric_e_established_recall([specimen], attempts)
    bearer = metric["per_slot"]["bearer"]
    assert bearer["proposed_compatible"] == 1
    assert bearer["incompatible"] == 1
    assert bearer["omitted"] == 1
    assert bearer["expected_established"] == 3


def test_metric_f_distinguishes_single_choice_from_preserved_alternatives(
    harness: ModuleType,
) -> None:
    specimen = _fixture(harness, "IIR-017")
    assert specimen.gold_slot("bearer")["status"] == "AMBIGUOUS"
    both = _attempt(
        harness,
        "IIR-017",
        {
            "proposed_assertions": [
                _slot("bearer", "The department"),
                _slot("bearer", "its contractor"),
            ]
        },
        run=1,
    )
    one = _attempt(
        harness, "IIR-017", {"proposed_assertions": [_slot("bearer", "The department")]}, run=2
    )
    third = _attempt(
        harness, "IIR-017", {"proposed_assertions": [_slot("bearer", "the regulator")]}, run=3
    )
    none = _attempt(harness, "IIR-017", {"proposed_assertions": []}, run=4)
    metric = harness.metric_f_ambiguity([specimen], [both, one, third, none])
    assert metric["counts"]["alternatives_preserved"] == 1
    assert metric["counts"]["single_alternative_proposed"] == 1
    assert metric["counts"]["unsupported_alternative_proposed"] == 1
    assert metric["counts"]["omitted"] == 1


def test_metric_g_detects_a_bearer_counterparty_swap(harness: ModuleType) -> None:
    specimen = _fixture(harness, "IIR-016")
    swapped = _attempt(
        harness,
        "IIR-016",
        {
            "proposed_assertions": [
                _slot("bearer", "the compliance office"),
                _slot("counterparty", "The vendor"),
            ]
        },
    )
    metric = harness.metric_g_role_separation([specimen], [swapped])
    assert metric["counts"]["swapped"] >= 1
    assert "correct_bearer" not in metric["counts"]


def test_metric_g_records_a_correct_role_assignment(harness: ModuleType) -> None:
    specimen = _fixture(harness, "IIR-016")
    correct = _attempt(
        harness,
        "IIR-016",
        {
            "proposed_assertions": [
                _slot("bearer", "The vendor"),
                _slot("counterparty", "the compliance office"),
            ]
        },
    )
    metric = harness.metric_g_role_separation([specimen], [correct])
    assert metric["counts"]["correct_bearer"] == 1
    assert metric["counts"]["correct_counterparty"] == 1
    assert "swapped" not in metric["counts"]


def test_metric_h_separates_omission_from_wrong_slot_placement(harness: ModuleType) -> None:
    specimen = _fixture(harness, "IIR-030")
    omitted = _attempt(
        harness, "IIR-030", {"proposed_assertions": [_slot("action", "require")]}, run=1
    )
    misplaced = _attempt(
        harness,
        "IIR-030",
        {
            "proposed_assertions": [
                _slot("condition", "except withdrawals under an approved standing order")
            ]
        },
        run=2,
    )
    metric = harness.metric_h_material_preservation([specimen], [omitted, misplaced])
    assert metric["counts"]["exception"]["omitted"] == 1
    assert metric["counts"]["exception"]["moved_to_wrong_slot"] == 1


def test_metric_h_detects_a_broadened_threshold(harness: ModuleType) -> None:
    specimen = _fixture(harness, "IIR-031")
    broadened = _attempt(
        harness, "IIR-031", {"proposed_assertions": [_slot("quantum", "250 units")]}
    )
    preserved = _attempt(
        harness, "IIR-031", {"proposed_assertions": [_slot("quantum", "over 250 units")]}, run=2
    )
    metric = harness.metric_h_material_preservation([specimen], [broadened, preserved])
    assert metric["counts"]["quantum"]["broadened"] == 1
    assert metric["counts"]["quantum"]["preserved"] == 1


def test_metric_h_detects_a_lost_currency(harness: ModuleType) -> None:
    specimen = _fixture(harness, "IIR-013")
    lost = _attempt(harness, "IIR-013", {"proposed_assertions": [_slot("quantum", "10,000")]})
    metric = harness.metric_h_material_preservation([specimen], [lost])
    assert metric["counts"]["currency"]["omitted"] == 1


def test_metric_i_records_an_ungrounded_quote_without_repairing_it(
    harness: ModuleType,
) -> None:
    specimen = _fixture(harness, "IIR-001")
    attempt = _attempt(
        harness,
        "IIR-001",
        {
            "proposed_assertions": [
                _slot("bearer", "The Records Officer", "The Records Officer"),
                _slot("action", "retain", "a phrase that is not in the source"),
            ]
        },
    )
    metric = harness.metric_i_quote_grounding([specimen], [attempt])
    assert metric["grounded"] == 1
    assert metric["ungrounded"] == 1
    assert metric["ungrounded_instances"][0]["quote"] == "a phrase that is not in the source"
    assert attempt.proposal is not None
    assert (
        attempt.proposal["proposed_assertions"][1]["proposed_source_quote"]
        == "a phrase that is not in the source"
    )


def test_metric_j_catches_a_quote_that_supports_a_different_role(harness: ModuleType) -> None:
    specimen = _fixture(harness, "IIR-016")
    attempt = _attempt(
        harness,
        "IIR-016",
        {
            "proposed_assertions": [
                _slot("bearer", "the compliance office", "the compliance office")
            ]
        },
    )
    metric = harness.metric_j_quote_support([specimen], [attempt])
    assert metric["counts"]["supports_a_different_role"] == 1
    assert metric["instances"][0]["actually_supports"] == ["counterparty"]


def test_metric_k_detects_an_omitted_and_a_resolved_reference(harness: ModuleType) -> None:
    specimen = _fixture(harness, "IIR-024")
    omitted = _attempt(harness, "IIR-024", {"proposed_assertions": []}, run=1)
    resolved = _attempt(
        harness,
        "IIR-024",
        {"proposed_assertions": [_slot("definiens", "a bank licensed in the jurisdiction")]},
        run=2,
    )
    metric = harness.metric_k_reference_recall([specimen], [omitted, resolved])
    assert metric["counts"]["omitted"] == 2
    assert metric["counts"]["resolved_instead_of_surfaced"] == 1


def test_metric_k_credits_a_surfaced_reference_with_the_right_kind(
    harness: ModuleType,
) -> None:
    specimen = _fixture(harness, "IIR-026")
    surfaced = _attempt(
        harness,
        "IIR-026",
        {
            "proposed_assertions": [],
            "proposed_unresolved_references": [
                {"reference_text": "Policy B", "reference_kind": "EXTERNAL_DOCUMENT"}
            ],
        },
    )
    metric = harness.metric_k_reference_recall([specimen], [surfaced])
    assert metric["counts"]["correct_kind"] == 1
    assert metric["counts"].get("omitted", 0) == 0


@pytest.mark.parametrize(
    ("specimen_id", "payload", "expected_kind"),
    [
        (
            "IIR-027",
            {"proposed_assertions": [_slot("normative_force", "OBLIGATION")]},
            "advisory_to_obligation",
        ),
        (
            "IIR-028",
            {"proposed_assertions": [_slot("normative_force", "OBLIGATION")]},
            "permission_to_obligation",
        ),
        (
            "IIR-030",
            {"proposed_assertions": [_slot("action", "require")]},
            "exception_bearing_to_exceptionless_by_dropped_exception",
        ),
        (
            "IIR-031",
            {"proposed_assertions": [_slot("action", "reviewed")]},
            "threshold_bearing_to_unbounded_by_dropped_quantum",
        ),
        (
            "IIR-010",
            {"proposed_assertions": [_slot("action", "escalate")]},
            "conditional_to_unconditional_by_dropped_condition",
        ),
        (
            "IIR-016",
            {"proposed_assertions": [_slot("bearer", "the compliance office")]},
            "recipient_promoted_to_bearer",
        ),
        (
            "IIR-024",
            {"proposed_assertions": [_slot("definiens", "an institution of any kind")]},
            "undefined_supplied_from_general_knowledge",
        ),
    ],
)
def test_metric_l_detects_each_named_strengthening(
    harness: ModuleType, specimen_id: str, payload: object, expected_kind: str
) -> None:
    assert isinstance(payload, dict)
    specimen = _fixture(harness, specimen_id)
    metric = harness.metric_l_strengthening([specimen], [_attempt(harness, specimen_id, payload)])
    assert metric["counts"].get(expected_kind, 0) >= 1, metric["counts"]
    assert any(entry["kind"] == expected_kind for entry in metric["instances"])


def test_metric_m_reports_stability_and_binding_determinism(harness: ModuleType) -> None:
    specimen = _fixture(harness, "IIR-001")
    same = {"proposed_assertions": [_slot("action", "retain", "retain")]}
    stable = [
        _attempt(harness, "IIR-001", same, run=1),
        _attempt(harness, "IIR-001", same, run=2),
    ]
    metric = harness.metric_m_repeat_stability([specimen], stable)["IIR-001"]
    assert metric["semantic_hash_stable"] is True
    assert metric["slot_set_stable"] is True
    assert metric["oic_binding_deterministic"] is True

    drifting = [
        _attempt(harness, "IIR-001", same, run=1),
        _attempt(harness, "IIR-001", {"proposed_assertions": [_slot("action", "keep")]}, run=2),
    ]
    unstable = harness.metric_m_repeat_stability([specimen], drifting)["IIR-001"]
    assert unstable["semantic_hash_stable"] is False
    assert unstable["per_slot_value_stable"]["action"] is False


def test_the_semantic_hash_is_deterministic_and_order_insensitive(
    harness: ModuleType,
) -> None:
    first = _attempt(
        harness,
        "IIR-001",
        {
            "proposed_assertions": [
                _slot("action", "retain", "retain"),
                _slot("bearer", "The Records Officer", None),
            ]
        },
    )
    second = _attempt(
        harness,
        "IIR-001",
        {
            "proposed_assertions": [
                _slot("bearer", "The Records Officer", None),
                _slot("action", "retain", "retain"),
            ]
        },
        run=2,
    )
    assert first.proposal is not None and second.proposal is not None
    assert harness.semantic_hash(first.proposal) == harness.semantic_hash(second.proposal)
    assert harness.semantic_hash(first.proposal).startswith("sha256:")


def test_the_semantic_hash_ignores_the_proposal_id_and_proposer(harness: ModuleType) -> None:
    attempt = _attempt(harness, "IIR-001", {"proposed_assertions": []})
    assert attempt.proposal is not None
    projection = harness.semantic_projection(attempt.proposal)
    assert set(projection) == {"proposed_assertions", "proposed_unresolved_references"}


def test_the_semantic_hash_is_not_the_canonical_ir_equivalence_key(
    repo_root: Path, harness: ModuleType
) -> None:
    del repo_root
    source = Path(str(harness.__file__)).read_text(encoding="utf-8")
    assert "semantic_equivalence_key" in source
    assert "NOT the canonical IR" in source or "not the canonical IR" in source


def test_the_critical_diagnostics_cover_every_named_specimen(harness: ModuleType) -> None:
    covered = {specimen_id for specimen_id, _ in harness.CRITICAL_SPECIMENS}
    assert covered == {
        "IIR-015", "IIR-016", "IIR-017", "IIR-018", "IIR-027", "IIR-028",
        "IIR-029", "IIR-030", "IIR-031", "IIR-032", "IIR-035",
    }  # fmt: skip
    plan = harness.preflight()
    sections = harness.critical_diagnostics(plan.specimens, [])
    assert set(sections) == covered
    for section in sections.values():
        assert section["candidate_span"]
        assert set(section["expected_slots"]) == set(SLOT_VOCABULARY)


def test_the_receipt_records_the_full_metric_set_and_the_claim_ceiling(
    harness: ModuleType,
) -> None:
    plan = harness.preflight()
    receipt = harness.build_receipt(
        specimens=plan.specimens,
        attempts=[],
        digests=plan.digests,
        corpus=plan.corpus,
        provider_name=None,
        model_name=None,
        live=False,
    )
    assert set(receipt["metrics"]) == {
        "A_provider_structural_boundary",
        "B_proposal_presence",
        "C_force_classification",
        "D_unsupported_semantic_invention",
        "E_established_slot_recall",
        "F_ambiguity_overcommitment",
        "G_bearer_counterparty_separation",
        "H_material_qualifier_preservation",
        "I_source_quote_grounding",
        "J_quote_to_value_support",
        "K_unresolved_reference_recall",
        "L_strengthening_rate",
        "M_repeat_stability",
    }
    assert receipt["work_order"] == "OIC-INTERPRETATION-PROPOSAL-CHARACTERIZATION-001"
    assert receipt["starting_sha"] == STARTING_SHA
    assert receipt["planned_live_requests"] == PLANNED_REQUESTS
    assert receipt["retry_policy"].startswith("none")
    assert receipt["canonicalization_performed"] is False
    assert receipt["institutional_ir_constructed"] is False
    assert receipt["independent_validation_claim"] is False
    assert receipt["self_adjudication"] == "NOT SELF-ADJUDICATED"
    assert receipt["live_run_executed"] is False
    for claim in (
        "canonical institutional meaning",
        "interpretation authority",
        "cross-model generalization",
        "independent validation",
    ):
        assert claim in receipt["claim_ceiling"]


# ---------------------------------------------------------------------------
# No canonicalization anywhere in the work order
# ---------------------------------------------------------------------------


def test_no_institutional_ir_runtime_exists(repo_root: Path) -> None:
    assert not (repo_root / "src/oic/institutional_ir.py").exists()
    modules = {path.name for path in (repo_root / "src" / "oic").glob("*.py")}
    assert "institutional_ir.py" not in modules
    assert not list((repo_root / "src").rglob("*.rego"))


#: Keys that would mean an act-4 canonicalization decision had been written down.
_CANONICAL_OUTPUT_KEYS = frozenset(
    {
        "interpretation_status",
        "interpretation_basis",
        "interpretation_evidence_refs",
        "ir_unit_id",
        "ir_schema_id",
        "semantic_equivalence_key",
        "supersedes_ir_unit_id",
        "exception_closure",
    }
)


@pytest.mark.parametrize(
    "relpath",
    [
        "src/oic/interpretation_proposal.py",
        "scripts/characterize_interpretation_proposal.py",
        "scripts/build_interpretation_proposal_corpus.py",
    ],
)
def test_no_component_of_this_work_order_writes_a_canonicalization_decision(
    repo_root: Path, relpath: str
) -> None:
    """Structural, not textual: no dict literal anywhere builds a canonical IR field.

    Grepping the source would catch the word in a docstring that exists to say the word is
    forbidden. What matters is whether any of these modules ever *constructs* one.
    """
    tree = ast.parse((repo_root / relpath).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        keys = {
            key.value
            for key in node.keys
            if isinstance(key, ast.Constant) and isinstance(key.value, str)
        }
        offending = keys & _CANONICAL_OUTPUT_KEYS
        # The corpus builder reads gold out of the frozen design corpus; reading a status
        # is not assigning one, so only *writing* a canonical output key is refused.
        assert offending <= {"exception_closure"} or "build_interpretation" in relpath, (
            relpath,
            sorted(offending),
        )
        assert not (offending - {"exception_closure"}), (relpath, sorted(offending))


def test_the_harness_never_assigns_an_interpretation_basis(repo_root: Path) -> None:
    """The basis vocabulary belongs to canonicalization. The harness must not carry it."""
    tree = ast.parse((repo_root / HARNESS_RELPATH).read_text(encoding="utf-8"))
    basis_values = {
        "INSTITUTIONAL_INTERPRETATION_WARRANT",
        "REGISTERED_INTERPRETATION_RULE",
        "DETERMINISTIC_NORMALIZATION",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            assert node.value not in basis_values, node.value


@pytest.mark.parametrize(
    "relpath",
    ["src/oic/interpretation_proposal.py", "scripts/characterize_interpretation_proposal.py"],
)
def test_the_instrument_calls_the_provider_exactly_once_per_attempt(
    repo_root: Path, relpath: str
) -> None:
    """No retry and no backoff, established from the parsed module rather than from prose."""
    source = (repo_root / relpath).read_text(encoding="utf-8")
    tree = ast.parse(source)
    completions = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "complete"
    ]
    assert len(completions) <= 1, f"{relpath} calls provider.complete more than once"
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert node.func.attr not in {"sleep", "retry"}, node.func.attr
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert "time" not in imported


def test_no_provider_is_named_in_the_production_module(repo_root: Path) -> None:
    source = (repo_root / "src/oic/interpretation_proposal.py").read_text(encoding="utf-8")
    for vendor in ("nvidia", "nim", "nemotron", "openai", "gpt", "anthropic", "claude"):
        assert vendor not in source.casefold(), vendor
