"""Stage-2 seam repair: prior-state derivation, owner issuance, attempt ledger.

Non-result-bearing. Nothing here executes Stage 2 against the frozen mission
population, evaluates a real transition, emits an event, renders drafts or
performs a correction. Stage-2 machinery is exercised on rehydrated evidence and
synthetic non-mission fixtures so the seams can be observed refusing and, where a
test needs the gate open, opening on something visibly synthetic.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import shutil
import subprocess
import sys
import threading
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from cdc_e2e_support import PACKAGE_RELPATH, STUB_RUNTIME, exact_clearance

from oic import cdc_e2e_mission
from oic.cdc_e2e_mission import (
    ExecutionClearance,
    FrozenActionPlan,
    FrozenMissionInput,
    MissionProjection,
    OwnerStage2Authorization,
    OwnerStage2AuthorizationError,
    Stage1Observation,
)

M = cdc_e2e_mission

DispositionMap = dict[str, Mapping[str, object]]
BINDING_FIELDS: list[str] = list(cdc_e2e_mission.STAGE_2_AUTHORIZATION_BINDING_FIELDS)
STAGE_1_EVIDENCE_COMMIT = "c44c9bf7d24b79990fb00274b871326f0d7617e9"
DISPOSITION_EVIDENCE_COMMIT = "a61fae0a94eeaf54f69c42f40af67d9e43516294"
DISPOSITION_EVIDENCE_TREE = "e1747b5bfa1a11f3f852a92ad13fdd975aceef9e"
STAGE_1_RAW_SHA = "aa32274f238d01bc9f6c6d1c67879acfb4765a34d0dc0b4ccf568f3c07353a70"
STAGE_1_DIGEST = "0c7c9aa770aee07b7c42f9bb48ec3b13058bbaf7559d5696bc59c6eb276510be"
OWNER_M08_M09_ACCEPTANCE_SHA = "5f13fe1920be490429b9cc562bcaade38293de35e9898a4d5803f0744c29381a"


def _git_show(repo: Path, commit: str, path: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(repo), "show", f"{commit}:{path}"],
        capture_output=True,
        check=True,
    ).stdout


@pytest.fixture
def frozen(repo_root: Path) -> FrozenMissionInput:
    """The controlling frozen package, unmodified."""
    return M.verify_frozen_mission_input(repo_root / PACKAGE_RELPATH)


@pytest.fixture
def projection(frozen: FrozenMissionInput) -> MissionProjection:
    """The nine-chain projection."""
    return M.project_frozen_mission(frozen)


@pytest.fixture
def plan(repo_root: Path) -> FrozenActionPlan:
    """The frozen action plan."""
    return M.verify_frozen_action_plan(repo_root / M.HUMAN_ACTION_PLAN_RELPATH)


@pytest.fixture
def stage_1(repo_root: Path) -> Stage1Observation:
    """The real Stage-1 checkpoint, rehydrated from archived evidence."""
    raw = json.loads(
        _git_show(
            repo_root,
            STAGE_1_EVIDENCE_COMMIT,
            "veraxis/cdc-e2e-mission-001/executions/STAGE-1-RUN-001/"
            "CDC-END-TO-END-MISSION-001-STAGE-1-RAW-RESULT-v0.1.json",
        )
    )
    chains = []
    for c in raw["chains"]:
        a = c["artifact"]
        artifact = M.Stage1ChainArtifact(
            chain_id=a["chain_id"],
            procedure_id=a["procedure_id"],
            control_id=a["control_id"],
            ebawu_id=a["ebawu_id"],
            input_digest=a["input_digest"],
            evaluation=a["evaluation"],
            evaluation_digest=a["evaluation_digest"],
            warrant_class=a["warrant_class"],
            warrant_ref=a["warrant_ref"],
            warrant=a["warrant"],
            warrant_digest=a["warrant_digest"],
            candidate_id=a["candidate_id"],
            candidate=a["candidate"],
            candidate_digest=a["candidate_digest"],
            outcome_state=a["outcome_state"],
        )
        chains.append(
            M.Stage1ChainObservation(
                chain_id=c["chain_id"],
                outcome_state=c["outcome_state"],
                candidate_digest=c["candidate_digest"],
                input_digest=c["input_digest"],
                detail=c["detail"],
                artifact=artifact,
            )
        )
    return Stage1Observation(
        mission_id=raw["mission_id"],
        package_sha256=raw["package_sha256"],
        provenance_token=raw["provenance_token"],
        stage=raw["stage"],
        chains=tuple(chains),
        accounting=raw["accounting"],
        authorization=raw["authorization"],
        owner_interpretation_sha256=raw["owner_interpretation_sha256"],
        owner_execution_authorization=raw["owner_execution_authorization"],
        attempt_record=raw["attempt_record"],
        institutional_transition=raw["institutional_transition"],
        draft_eligibility=raw["draft_eligibility"],
        official_handoff=raw["official_handoff"],
        human_disposition=raw["human_disposition"],
    )


@pytest.fixture
def dispositions(repo_root: Path, stage_1: Stage1Observation) -> dict[str, Mapping[str, Any]]:
    """The nine bound dispositions, rehydrated. Never rebound."""
    base = "veraxis/cdc-e2e-mission-001/executions/HUMAN-DISPOSITION-RUN-001/dispositions"
    return {
        chain_id: json.loads(
            _git_show(repo_root, DISPOSITION_EVIDENCE_COMMIT, f"{base}/DISPOSITION-{chain_id}.json")
        )
        for chain_id in stage_1.artifacts()
    }


def _authorization_document(
    path: Path,
    runtime: M.RuntimeIdentity,
    frozen: FrozenMissionInput,
    stage_1: Stage1Observation,
    dispositions: Mapping[str, Mapping[str, Any]],
    plan: FrozenActionPlan,
    *,
    overrides: Mapping[str, Any] | None = None,
    binding_overrides: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    document: dict[str, Any] = {
        **M.STAGE_2_AUTHORIZATION_DECLARATIONS,
        "authorization_id": "SYNTHETIC-TEST-STAGE-2-AUTHORIZATION-001",
        "synthetic_test_fixture": True,
        "canonical_authorization_path": str(path.resolve()),
        "bindings": {
            "implementation_commit": runtime.implementation_commit,
            "implementation_tree": runtime.implementation_tree,
            "environment_manifest_sha256": runtime.environment_manifest_sha256,
            "mission_package_sha256": frozen.package_sha256,
            "stage_1_component_profile_sha256": M.STAGE_1_COMPONENT_PROFILE_SHA256,
            "oracle_sha256": M.ORACLE_SHA256,
            "adjudication_protocol_sha256": M.ADJUDICATION_PROTOCOL_SHA256,
            "action_plan_sha256": plan.sha256_hex,
            "action_plan_provenance_token": plan.provenance_token,
            "owner_preexecution_interpretation_sha256": M.OWNER_PREEXECUTION_INTERPRETATION_SHA256,
            "stage_1_raw_result_sha256": STAGE_1_RAW_SHA,
            "stage_1_observation_digest": stage_1.digest(),
            "human_disposition_evidence_commit": DISPOSITION_EVIDENCE_COMMIT,
            "human_disposition_evidence_tree": DISPOSITION_EVIDENCE_TREE,
            "correction_stimulus_digest": plan.correction.digest(),
            "owner_m08_m09_acceptance_sha256": OWNER_M08_M09_ACCEPTANCE_SHA,
            "stage_2_human_disposition_binding_digests": sorted(
                M.sha256(dict(r)) for r in dispositions.values()
            ),
        },
    }
    if overrides:
        document.update(overrides)
    if binding_overrides:
        document["bindings"] = {**document["bindings"], **binding_overrides}
    return document


def _write_authorization(path: Path, document: Mapping[str, Any]) -> Path:
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _clearance_for(path: Path) -> ExecutionClearance:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return ExecutionClearance(
        **{
            **exact_clearance().as_mapping(),
            "owner_execution_authorization": f"sha256:{digest}",
        }
    )


def _verify(
    path: Path,
    frozen: FrozenMissionInput,
    stage_1: Stage1Observation,
    dispositions: Mapping[str, Mapping[str, Any]],
    plan: FrozenActionPlan,
) -> OwnerStage2Authorization:
    return M.verify_owner_stage_2_authorization(
        path,
        clearance=_clearance_for(path),
        runtime=STUB_RUNTIME,
        frozen=frozen,
        stage_1=stage_1,
        dispositions=dispositions,
        action_plan=plan,
    )


# === Prior-state seam =======================================================


def test_frozen_v0_6_still_has_no_prior_institutional_state(repo_root: Path) -> None:
    """1. The frozen package is unchanged and still omits the field."""
    for procedure in ("P001", "P002", "P003"):
        population = json.loads(
            (repo_root / PACKAGE_RELPATH / f"02-POPULATION/{procedure}.json").read_bytes()
        )
        for chain in population.values():
            assert "prior_institutional_state" not in chain


def test_no_package_file_changed(repo_root: Path, frozen: FrozenMissionInput) -> None:
    """2. Package identity is byte-for-byte what it was."""
    assert frozen.package_sha256 == M.FROZEN_MISSION_PACKAGE_SHA256
    assert frozen.manifest_sha256 == M.FROZEN_MISSION_MANIFEST_SHA256
    assert frozen.package_bytes == M.FROZEN_MISSION_PACKAGE_BYTES
    changed = subprocess.run(
        [
            "git",
            "-C",
            str(repo_root),
            "diff",
            "--name-only",
            "2e15267194d320b54015f0c212a8041cedc22050",
            "--",
            PACKAGE_RELPATH,
        ],
        capture_output=True,
        check=True,
        text=True,
    ).stdout.strip()
    assert changed == ""


@pytest.mark.parametrize("bad", [None, "CANDIDATE_FORMED", {"stage": "x"}, 1, object()])
def test_prior_state_requires_a_real_stage_1_observation(bad: object) -> None:
    """3, 5. Nothing but a Stage1Observation can supply it."""
    with pytest.raises(M.PriorStateDerivationError):
        M.derive_stage_2_prior_state(bad, "P001xC-TENDER-01")


def test_prior_state_unavailable_before_an_actual_candidate(
    stage_1: Stage1Observation,
) -> None:
    """3. Unknown chain, unterminated stage and unauthorized stage all refuse."""
    import dataclasses

    with pytest.raises(M.PriorStateDerivationError, match="no Stage-1 artifact"):
        M.derive_stage_2_prior_state(stage_1, "P999xC-NONE")
    unterminated = dataclasses.replace(stage_1, stage="EVALUATION_IN_PROGRESS")
    with pytest.raises(M.PriorStateDerivationError, match="not"):
        M.derive_stage_2_prior_state(unterminated, "P001xC-TENDER-01")
    helper = dataclasses.replace(stage_1, authorization=M.STAGE_1_AUTHORIZATION_HELPER)
    with pytest.raises(M.PriorStateDerivationError, match="owner-cleared"):
        M.derive_stage_2_prior_state(helper, "P001xC-TENDER-01")


def test_completed_owner_cleared_candidate_yields_candidate_formed(
    stage_1: Stage1Observation,
) -> None:
    """4. Deterministic CANDIDATE_FORMED for all nine chains."""
    assert stage_1.digest() == STAGE_1_DIGEST
    for chain_id in stage_1.artifacts():
        assert M.derive_stage_2_prior_state(stage_1, chain_id) == "CANDIDATE_FORMED"
    assert M.DERIVED_PRIOR_INSTITUTIONAL_STATE == "CANDIDATE_FORMED"
    assert M.PRIOR_STATE_SOURCE == "ACTUAL_STAGE_1_OBSERVATION"


def test_registry_and_proposal_use_the_same_derived_state(
    projection: MissionProjection,
    stage_1: Stage1Observation,
    dispositions: dict[str, Mapping[str, Any]],
) -> None:
    """6. One derivation, consumed by both."""
    chain_id = "P001xC-TENDER-01"
    artifact = stage_1.artifacts()[chain_id]
    registry = M.derive_transition_registry(projection, artifact, stage_1)
    proposal = M.derive_transition_proposal(projection, artifact, dispositions[chain_id], stage_1)
    derived = M.derive_stage_2_prior_state(stage_1, chain_id)
    assert registry["states"][artifact.ebawu_id] == derived == "CANDIDATE_FORMED"
    assert proposal["prior_institutional_state"] == derived
    for source in (M.derive_transition_registry, M.derive_transition_proposal):
        assert "derive_stage_2_prior_state" in inspect.getsource(source)


def test_no_public_api_accepts_a_caller_supplied_prior_state() -> None:
    """5. No parameter anywhere on the Stage-2 path carries it."""
    for function in (
        M.execute_authorized_stage_2,
        M.derive_transition_registry,
        M.derive_transition_proposal,
        M.require_stage_2_clearance,
    ):
        parameters = set(inspect.signature(function).parameters)
        for forbidden in ("prior_institutional_state", "prior_state", "states"):
            assert forbidden not in parameters, f"{function.__name__}:{forbidden}"
    source = inspect.getsource(M.execute_authorized_stage_2)
    assert '"prior_institutional_state",' in source
    assert '"states",' in source


def test_structural_stage_2_precondition_crosses_without_touching_frozen_input(
    projection: MissionProjection,
    stage_1: Stage1Observation,
    dispositions: dict[str, Mapping[str, Any]],
    frozen: FrozenMissionInput,
) -> None:
    """7. The real v0.6 + real checkpoint now derive prior state for all nine."""
    assert len(dispositions) == 9
    for chain_id in dispositions:
        artifact = stage_1.artifacts()[chain_id]
        registry = M.derive_transition_registry(projection, artifact, stage_1)
        assert registry["states"][artifact.ebawu_id] == "CANDIDATE_FORMED"
    assert frozen.package_sha256 == M.FROZEN_MISSION_PACKAGE_SHA256


# === Stage-2 authorization ==================================================


def test_absent_authorization_refuses(
    tmp_path: Path,
    frozen: FrozenMissionInput,
    stage_1: Stage1Observation,
    dispositions: dict[str, Mapping[str, Any]],
    plan: FrozenActionPlan,
) -> None:
    """8."""
    with pytest.raises(OwnerStage2AuthorizationError, match="not readable"):
        M.verify_owner_stage_2_authorization(
            tmp_path / "absent.json",
            clearance=exact_clearance(),
            runtime=STUB_RUNTIME,
            frozen=frozen,
            stage_1=stage_1,
            dispositions=dispositions,
            action_plan=plan,
        )


def test_a_label_or_flag_or_mapping_refuses(
    tmp_path: Path,
    frozen: FrozenMissionInput,
    stage_1: Stage1Observation,
    dispositions: dict[str, Mapping[str, Any]],
    plan: FrozenActionPlan,
) -> None:
    """9. Non-JSON content and a clearance label alone are both refused."""
    victim = tmp_path / "auth.json"
    victim.write_bytes(b"OWNER_STAGE_2_EXECUTION_AUTHORIZATION = true\n")
    with pytest.raises(OwnerStage2AuthorizationError, match="not structured JSON"):
        _verify(victim, frozen, stage_1, dispositions, plan)
    good = _write_authorization(
        tmp_path / "good.json",
        _authorization_document(
            tmp_path / "good.json", STUB_RUNTIME, frozen, stage_1, dispositions, plan
        ),
    )
    with pytest.raises(OwnerStage2AuthorizationError, match="a label is not the artifact"):
        M.verify_owner_stage_2_authorization(
            good,
            clearance=exact_clearance(),
            runtime=STUB_RUNTIME,
            frozen=frozen,
            stage_1=stage_1,
            dispositions=dispositions,
            action_plan=plan,
        )


DECLARATION_DEFECTS: list[tuple[str, object]] = [
    ("record_class", "OWNER_STAGE_1_EXECUTION_AUTHORIZATION"),
    ("mission_id", "CDC-OTHER-MISSION"),
    ("authorized_stage", "STAGE_1_ONLY"),
    ("authorization_scope", "UNLIMITED_STAGE_2_EXECUTIONS"),
    ("owner_authorized", False),
    ("single_use", False),
    ("automatic_retry_authorized", True),
    ("stage_1_reexecution_authorized", True),
    ("additional_human_disposition_authorized", True),
    ("stage_2_transition_evaluation_authorized", False),
    ("official_handoff_authorized", True),
]


@pytest.mark.parametrize(("field", "value"), DECLARATION_DEFECTS)
def test_each_declaration_defect_refuses(
    tmp_path: Path,
    frozen: FrozenMissionInput,
    stage_1: Stage1Observation,
    dispositions: DispositionMap,
    plan: FrozenActionPlan,
    field: str,
    value: object,
) -> None:
    """10, 11, 12, 13."""
    path = tmp_path / "auth.json"
    _write_authorization(
        path,
        _authorization_document(
            path, STUB_RUNTIME, frozen, stage_1, dispositions, plan, overrides={field: value}
        ),
    )
    with pytest.raises(OwnerStage2AuthorizationError, match="authorization semantics"):
        _verify(path, frozen, stage_1, dispositions, plan)


@pytest.mark.parametrize("binding", BINDING_FIELDS)
def test_each_binding_mismatch_refuses(
    tmp_path: Path,
    frozen: FrozenMissionInput,
    stage_1: Stage1Observation,
    dispositions: DispositionMap,
    plan: FrozenActionPlan,
    binding: str,
) -> None:
    """14, 15, 17, 18 and every other bound identity, each independently."""
    path = tmp_path / "auth.json"
    _write_authorization(
        path,
        _authorization_document(
            path,
            STUB_RUNTIME,
            frozen,
            stage_1,
            dispositions,
            plan,
            binding_overrides={binding: "WRONG"},
        ),
    )
    with pytest.raises(OwnerStage2AuthorizationError):
        _verify(path, frozen, stage_1, dispositions, plan)


def test_wrong_human_disposition_binding_set_refuses(
    tmp_path: Path,
    frozen: FrozenMissionInput,
    stage_1: Stage1Observation,
    dispositions: dict[str, Mapping[str, Any]],
    plan: FrozenActionPlan,
) -> None:
    """16. The nine Stage-2 binding digests must be exact."""
    path = tmp_path / "auth.json"
    _write_authorization(
        path,
        _authorization_document(
            path,
            STUB_RUNTIME,
            frozen,
            stage_1,
            dispositions,
            plan,
            binding_overrides={"stage_2_human_disposition_binding_digests": ["0" * 64]},
        ),
    )
    with pytest.raises(OwnerStage2AuthorizationError, match="binding set"):
        _verify(path, frozen, stage_1, dispositions, plan)


def test_relocated_byte_identical_authorization_refuses(
    tmp_path: Path,
    frozen: FrozenMissionInput,
    stage_1: Stage1Observation,
    dispositions: dict[str, Mapping[str, Any]],
    plan: FrozenActionPlan,
) -> None:
    """19. One issuance, one location."""
    home = tmp_path / "issued"
    away = tmp_path / "copied"
    home.mkdir()
    away.mkdir()
    path = home / "auth.json"
    _write_authorization(
        path, _authorization_document(path, STUB_RUNTIME, frozen, stage_1, dispositions, plan)
    )
    _verify(path, frozen, stage_1, dispositions, plan)
    copy = away / "auth.json"
    shutil.copyfile(path, copy)
    assert copy.read_bytes() == path.read_bytes()
    with pytest.raises(OwnerStage2AuthorizationError, match="not a second issuance"):
        _verify(copy, frozen, stage_1, dispositions, plan)


def test_canonical_alias_resolves_to_the_same_namespace(
    tmp_path: Path,
    frozen: FrozenMissionInput,
    stage_1: Stage1Observation,
    dispositions: dict[str, Mapping[str, Any]],
    plan: FrozenActionPlan,
) -> None:
    """20. A `..` detour is the same issuance and the same attempt namespace."""
    home = tmp_path / "issued"
    home.mkdir()
    path = home / "auth.json"
    _write_authorization(
        path, _authorization_document(path, STUB_RUNTIME, frozen, stage_1, dispositions, plan)
    )
    direct = _verify(path, frozen, stage_1, dispositions, plan)
    awkward = home / ".." / "issued" / "auth.json"
    aliased = _verify(awkward, frozen, stage_1, dispositions, plan)
    assert M.stage_2_attempt_record_path(direct) == M.stage_2_attempt_record_path(aliased)


def test_a_valid_shaped_authorization_verifies(
    tmp_path: Path,
    frozen: FrozenMissionInput,
    stage_1: Stage1Observation,
    dispositions: dict[str, Mapping[str, Any]],
    plan: FrozenActionPlan,
) -> None:
    """The fixture opens only the test gate; it binds STUB runtime identities."""
    path = tmp_path / "auth.json"
    _write_authorization(
        path, _authorization_document(path, STUB_RUNTIME, frozen, stage_1, dispositions, plan)
    )
    verified = _verify(path, frozen, stage_1, dispositions, plan)
    assert verified.record_class == "OWNER_STAGE_2_EXECUTION_AUTHORIZATION"
    assert verified.authorized_stage == "STAGE_2_ONLY"
    assert verified.authorization_scope == "ONE_RESULT_BEARING_STAGE_2_EXECUTION"
    assert json.loads(path.read_bytes())["synthetic_test_fixture"] is True


# === Stage-2 attempt ledger =================================================


def _claim(
    tmp_path: Path,
    frozen: FrozenMissionInput,
    stage_1: Stage1Observation,
    dispositions: Mapping[str, Mapping[str, Any]],
    plan: FrozenActionPlan,
) -> tuple[OwnerStage2Authorization, list[str]]:
    path = tmp_path / "auth.json"
    _write_authorization(
        path, _authorization_document(path, STUB_RUNTIME, frozen, stage_1, dispositions, plan)
    )
    verified = _verify(path, frozen, stage_1, dispositions, plan)
    digests = [M.sha256(dict(r)) for r in dispositions.values()]
    return verified, digests


def test_stage_2_ledger_is_separate_from_stage_1(
    tmp_path: Path,
    frozen: FrozenMissionInput,
    stage_1: Stage1Observation,
    dispositions: dict[str, Mapping[str, Any]],
    plan: FrozenActionPlan,
) -> None:
    """The Stage-1 attempt record is neither reused nor mutated."""
    verified, _ = _claim(tmp_path, frozen, stage_1, dispositions, plan)
    path = M.stage_2_attempt_record_path(verified)
    assert ".cdc-e2e-stage-2-attempt-" in path.name
    assert verified.sha256_hex in path.name
    stage_1_record = stage_1.attempt_record
    assert stage_1_record is not None
    assert path != Path(str(stage_1_record["attempt_record_path"]))


def test_precondition_failure_creates_no_stage_2_claim(
    tmp_path: Path,
    frozen: FrozenMissionInput,
    stage_1: Stage1Observation,
    dispositions: dict[str, Mapping[str, Any]],
    plan: FrozenActionPlan,
) -> None:
    """21. A refused authorization leaves NO_ATTEMPT_RECORD."""
    path = tmp_path / "auth.json"
    _write_authorization(
        path,
        _authorization_document(
            path,
            STUB_RUNTIME,
            frozen,
            stage_1,
            dispositions,
            plan,
            binding_overrides={"mission_package_sha256": "WRONG"},
        ),
    )
    with pytest.raises(OwnerStage2AuthorizationError):
        _verify(path, frozen, stage_1, dispositions, plan)
    assert not list(tmp_path.glob(".cdc-e2e-stage-2-attempt-*"))


def test_claim_then_consume_transitions(
    tmp_path: Path,
    frozen: FrozenMissionInput,
    stage_1: Stage1Observation,
    dispositions: dict[str, Mapping[str, Any]],
    plan: FrozenActionPlan,
) -> None:
    """22, 26. NONE -> CLAIMED -> CONSUMED, with persisted identity bound."""
    verified, digests = _claim(tmp_path, frozen, stage_1, dispositions, plan)
    assert M.read_stage_2_attempt_state(verified) == M.ATTEMPT_STATE_NONE
    claimed = M.claim_stage_2_attempt(verified, STUB_RUNTIME, frozen, stage_1, digests)
    assert M.read_stage_2_attempt_state(verified) == M.ATTEMPT_STATE_CLAIMED
    consumed = M.mark_stage_2_attempt_consumed(claimed, stage_1, digests)
    assert M.read_stage_2_attempt_state(verified) == M.ATTEMPT_STATE_STAGE_2_CONSUMED
    identity = consumed.identity()
    persisted = M.stage_2_attempt_record_path(verified).read_bytes()
    assert identity["attempt_record_sha256"] == hashlib.sha256(persisted).hexdigest()
    assert identity["attempt_record_bytes"] == len(persisted)
    assert M.attempt_record_identity_is_intact(identity)
    body = json.loads(persisted)
    assert body["stage"] == "STAGE_2_ONLY"
    assert body["stage_1_observation_digest"] == stage_1.digest()
    assert body["human_disposition_binding_digests"] == sorted(digests)


def test_claimed_blocks_retry_and_consumed_blocks_reuse(
    tmp_path: Path,
    frozen: FrozenMissionInput,
    stage_1: Stage1Observation,
    dispositions: dict[str, Mapping[str, Any]],
    plan: FrozenActionPlan,
) -> None:
    """23, 24."""
    verified, digests = _claim(tmp_path, frozen, stage_1, dispositions, plan)
    claimed = M.claim_stage_2_attempt(verified, STUB_RUNTIME, frozen, stage_1, digests)
    with pytest.raises(M.MissionAttemptStateError, match="separate owner decision"):
        M.require_unclaimed_stage_2_attempt(verified)
    M.mark_stage_2_attempt_consumed(claimed, stage_1, digests)
    with pytest.raises(M.MissionAttemptStateError, match="non-reusable"):
        M.require_unclaimed_stage_2_attempt(verified)
    with pytest.raises(M.MissionAttemptStateError, match="already claimed"):
        M.claim_stage_2_attempt(verified, STUB_RUNTIME, frozen, stage_1, digests)


def test_concurrent_claims_permit_one_winner(
    tmp_path: Path,
    frozen: FrozenMissionInput,
    stage_1: Stage1Observation,
    dispositions: dict[str, Mapping[str, Any]],
    plan: FrozenActionPlan,
) -> None:
    """25."""
    verified, digests = _claim(tmp_path, frozen, stage_1, dispositions, plan)
    wins: list[str] = []
    losses: list[str] = []
    barrier = threading.Barrier(8)

    def attempt() -> None:
        barrier.wait()
        try:
            M.claim_stage_2_attempt(verified, STUB_RUNTIME, frozen, stage_1, digests)
            wins.append("claimed")
        except M.MissionAttemptStateError:
            losses.append("refused")

    threads = [threading.Thread(target=attempt) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(wins) == 1
    assert len(losses) == 7


def test_tampering_or_deleting_the_stage_2_record_is_detectable(
    tmp_path: Path,
    frozen: FrozenMissionInput,
    stage_1: Stage1Observation,
    dispositions: dict[str, Mapping[str, Any]],
    plan: FrozenActionPlan,
) -> None:
    """27. Detectable, not prevented."""
    verified, digests = _claim(tmp_path, frozen, stage_1, dispositions, plan)
    claimed = M.claim_stage_2_attempt(verified, STUB_RUNTIME, frozen, stage_1, digests)
    consumed = M.mark_stage_2_attempt_consumed(claimed, stage_1, digests)
    identity = consumed.identity()
    assert M.attempt_record_identity_is_intact(identity)
    path = M.stage_2_attempt_record_path(verified)
    body = json.loads(path.read_bytes())
    body["attempt_state"] = M.ATTEMPT_STATE_NONE
    path.write_bytes((json.dumps(body, indent=2, sort_keys=True) + "\n").encode())
    assert not M.attempt_record_identity_is_intact(identity)
    path.unlink()
    assert not M.attempt_record_identity_is_intact(identity)


# === Correction temporal seam ===============================================


def test_correction_argument_is_inert_until_eligibility_exists() -> None:
    """The correction artifact is created only after an eligible predecessor.

    The `correction` argument carries proposed content. `bind_correction` is
    reached only after the chain's outcome is `transitioned` with an emitted
    event, and the predecessor digest is derived from that actual event rather
    than preregistered.
    """
    source = inspect.getsource(M.integrate_correction)
    eligible = source.index("eligible = (")
    guard = source.index("if not eligible or artifact is None")
    bind = source.index("bind_correction(")
    derived = source.index("derived = sha256(predecessor)")
    assert eligible < guard < derived < bind
    assert 'outcome.outcome_state == "transitioned"' in source
    assert "outcome.transition_event is not None" in source
    assert 'str(outcome.transition_event["new_state"])' in source
    # A preregistered predecessor digest cannot override the derived one.
    assert "supplied is not None and supplied != derived" in source
    assert "PredecessorBindingError" in source


def test_correction_is_not_created_without_an_eligible_predecessor(
    projection: MissionProjection,
    stage_1: Stage1Observation,
    plan: FrozenActionPlan,
) -> None:
    """No transition, no correction -- and no manufactured predecessor."""
    outcomes = [
        M.Stage2ChainOutcome(
            chain_id=chain_id,
            outcome_state="blocked",
            decision=None,
            reason_code=None,
            epistemic_state=None,
            transition_event=None,
            detail="no transition",
        )
        for chain_id in stage_1.artifacts()
    ]
    record = M.integrate_correction(
        projection,
        stage_1,
        outcomes,
        plan,
        {
            "new_ebawu_or_successor_id": "X",
            "new_candidate_digest": "1" * 64,
            "correction_reason": "r",
            "changed_fact_or_control_refs": [],
            "new_state": "QUALIFIED",
            "correction_event_id": "e",
            "affected_output_refs": [],
        },
    )
    assert record["correction_executed"] is False
    assert record["m12_state"] == "unavailable_incomplete"
    assert record["eligible_completed_predecessor"] is False
    assert "predecessor_before_digest" not in record


# === Regression =============================================================


def test_no_caller_supplied_proposal_or_registry_is_reachable() -> None:
    """32."""
    parameters = set(inspect.signature(M.execute_authorized_stage_2).parameters)
    for forbidden in ("transition_proposal", "transition_registry", "registry", "proposal"):
        assert forbidden not in parameters


def test_denominator_and_binding_fields_unchanged() -> None:
    """31 and the Stage-2 binding contract."""
    assert M.EXPECTED_CHAIN_COUNT == 9
    assert list(M.STAGE_2_BINDING_FIELDS) == [
        "stage_1_observation_digest",
        "human_disposition_artifact_digests",
        "correction_stimulus_digest",
        "action_plan_sha256",
        "action_plan_provenance_token",
    ]


def test_historical_evidence_identities_are_not_rewritten(
    repo_root: Path,
    stage_1: Stage1Observation,
) -> None:
    """30. Stage-1 and disposition evidence still hash to their recorded values."""
    raw = _git_show(
        repo_root,
        STAGE_1_EVIDENCE_COMMIT,
        "veraxis/cdc-e2e-mission-001/executions/STAGE-1-RUN-001/"
        "CDC-END-TO-END-MISSION-001-STAGE-1-RAW-RESULT-v0.1.json",
    )
    assert hashlib.sha256(raw).hexdigest() == STAGE_1_RAW_SHA
    assert stage_1.digest() == STAGE_1_DIGEST
    assert stage_1.owner_execution_authorization is not None
    assert (
        stage_1.owner_execution_authorization["owner_execution_authorization_sha256"]
        == "47b97fadf9d44fdeec8359f7c582caf0269046d74cdd4b4353001b2ef7e3b240"
    )


def test_persisted_and_stage_2_digest_domains_remain_distinct(
    dispositions: dict[str, Mapping[str, Any]],
) -> None:
    """5. The two domains are not redefined into equality."""
    same = 0
    for record in dispositions.values():
        if record["disposition_artifact_digest"] == M.sha256(dict(record)):
            same += 1
    assert same == 0
    expected = {
        "P001xC-TENDER-01": "c33812f65a976ac414ea765f0836ab03fb00ae21fe915976b2b2ccca94105736",
        "P003xC-AWARD-01": "2eabeda78c5a1de266aa4a635adb2e34e7cbc06b58e8adf43a14e3dc83757a75",
    }
    for chain_id, digest in expected.items():
        assert M.sha256(dict(dispositions[chain_id])) == digest
