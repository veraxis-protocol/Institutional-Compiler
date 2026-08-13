"""Non-result-bearing shadow preflight for AUTH-002.

execute_authorized_stage_2 is never called. Nothing is claimed, nothing is
written. The only implementation function invoked that touches the candidate is
verify_owner_stage_2_authorization, and it is invoked against the review path
precisely to observe that it refuses there.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys

REPO = pathlib.Path("/private/tmp/claude-501/cleanroom")
RUN_DIR = pathlib.Path("/private/tmp/cdc-e2e-stage2-run-001")
REVIEW_DIR = pathlib.Path("/private/tmp/cdc-e2e-stage2-authorization-review")
STAGE = pathlib.Path("/private/tmp/cdc-e2e-stage2-rehydration")

CANDIDATE = REVIEW_DIR / (
    "CDC-END-TO-END-MISSION-001-OWNER-STAGE-2-EXECUTION-AUTHORIZATION-v0.2.CANDIDATE.json"
)
ENV_V2 = RUN_DIR / "CDC-END-TO-END-MISSION-001-STAGE-2-EXECUTION-ENVIRONMENT-v0.2.json"
AUTH_001_CANONICAL = RUN_DIR / (
    "CDC-END-TO-END-MISSION-001-OWNER-STAGE-2-EXECUTION-AUTHORIZATION-v0.1.json"
)
AUTH_002_CANONICAL = RUN_DIR / (
    "CDC-END-TO-END-MISSION-001-OWNER-STAGE-2-EXECUTION-AUTHORIZATION-v0.2.json"
)

PROJECT_VENV_ROOT = pathlib.Path("/private/tmp/claude-501/cleanroom/.venv")
PROJECT_VENV_INTERPRETER = PROJECT_VENV_ROOT / "bin" / "python"
STAGE_1_OBSERVATION_DIGEST = "0c7c9aa770aee07b7c42f9bb48ec3b13058bbaf7559d5696bc59c6eb276510be"
ENVIRONMENT_V0_2_SHA256 = "da57daaaa090a6a115797daa50c12baadbe40d0f69f5af394ecb833b12842ecb"

# Functions this preflight must never reach. Listed so the prohibition is
# inspectable in the artifact rather than merely asserted in prose.
PROHIBITED_CALLS = (
    "execute_authorized_stage_2",
    "evaluate_test_transition",
    "emit_transition_event",
    "integrate_correction",
    "render_drafts",
)

CHAINS = [
    "P001xC-TENDER-01",
    "P001xC-EVAL-01",
    "P001xC-AWARD-01",
    "P002xC-TENDER-01",
    "P002xC-EVAL-01",
    "P002xC-AWARD-01",
    "P003xC-TENDER-01",
    "P003xC-EVAL-01",
    "P003xC-AWARD-01",
]

out: dict[str, object] = {}

# ------------------------------------------------- operator substrate identity
out["prohibited_calls_declared"] = list(PROHIBITED_CALLS)
out["sys_executable"] = sys.executable
out["sys_executable_resolved"] = str(pathlib.Path(sys.executable).resolve())
out["sys_prefix"] = sys.prefix
out["sys_prefix_resolved"] = str(pathlib.Path(sys.prefix).resolve())
out["sys_base_prefix"] = sys.base_prefix
out["sys_base_prefix_resolved"] = str(pathlib.Path(sys.base_prefix).resolve())
out["declared_venv_root_resolved"] = str(PROJECT_VENV_ROOT.resolve())
out["declared_venv_interpreter_resolved"] = str(PROJECT_VENV_INTERPRETER.resolve())
out["version_info"] = list(sys.version_info[:3])

# The venv interpreter is a symlink into the underlying Anaconda installation,
# so a matching resolved sys.executable is satisfied equally by a direct
# Anaconda launch that never activated the venv. The prefixes are what
# distinguish them.
out["RESOLVED_SYS_EXECUTABLE_ALONE_PROVES_VENV_ACTIVATION"] = False
out["resolved_sys_executable_matches_declared_interpreter"] = (
    pathlib.Path(sys.executable).resolve() == PROJECT_VENV_INTERPRETER.resolve()
)

venv_conditions = {
    "version_major_is_3": sys.version_info.major == 3,
    "version_minor_is_12": sys.version_info.minor == 12,
    "sys_prefix_is_project_venv": (
        pathlib.Path(sys.prefix).resolve() == PROJECT_VENV_ROOT.resolve()
    ),
    "base_prefix_differs_from_prefix": (
        pathlib.Path(sys.base_prefix).resolve() != pathlib.Path(sys.prefix).resolve()
    ),
}
out["venv_conditions"] = venv_conditions
failed = sorted(name for name, ok in venv_conditions.items() if not ok)
out["project_venv_identity"] = "MATCH" if not failed else "MISMATCH"
if failed:
    out["OPERATOR_SUBSTRATE_PRECONDITION_BLOCK"] = failed
    out["classification"] = (
        "OPERATOR_SUBSTRATE_PRECONDITION_BLOCK; not a Stage-2 semantic result "
        "and not a consumed execution ordinal"
    )
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(3)

sys.path.insert(0, str(REPO / "src"))
from oic import cdc_e2e_mission as m  # noqa: E402

out["module_file"] = m.__file__

# ------------------------------------------------------------ frozen artifacts
frozen = m.verify_frozen_mission_input(REPO / m.FROZEN_MISSION_INPUT_RELPATH)
projection = m.project_frozen_mission(frozen)
out["mission_package_sha256"] = frozen.package_sha256
out["mission_manifest_sha256"] = frozen.manifest_sha256
out["mission_package_bytes"] = frozen.package_bytes
out["projection_chain_count"] = len(projection.chains)

plan = m.verify_frozen_action_plan(
    REPO
    / "veraxis/cdc-e2e-mission-001/preexecution/CDC-END-TO-END-MISSION-001-HUMAN-ACTION-PLAN-v0.1.json"
)
out["action_plan_sha256"] = plan.sha256_hex
out["action_plan_provenance_token"] = plan.provenance_token
out["correction_stimulus_digest"] = plan.correction.digest()

# ------------------------------------------------------- Stage-1 rehydration
raw_payload = (STAGE / "CDC-END-TO-END-MISSION-001-STAGE-1-RAW-RESULT-v0.1.json").read_bytes()
out["stage_1_raw_result_sha256"] = hashlib.sha256(raw_payload).hexdigest()
raw = json.loads(raw_payload)

stage_1 = m.Stage1Observation(
    mission_id=raw["mission_id"],
    package_sha256=raw["package_sha256"],
    provenance_token=raw["provenance_token"],
    stage=raw["stage"],
    chains=tuple(
        m.Stage1ChainObservation(
            chain_id=c["chain_id"],
            outcome_state=c["outcome_state"],
            candidate_digest=c["candidate_digest"],
            input_digest=c["input_digest"],
            detail=c["detail"],
            artifact=None if c["artifact"] is None else m.Stage1ChainArtifact(**c["artifact"]),
        )
        for c in raw["chains"]
    ),
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
out["stage_1_rehydrated_record_equals_archive"] = stage_1.as_record() == raw
out["stage_1_observation_digest"] = stage_1.digest()
out["stage_1_observation_digest_matches"] = stage_1.digest() == STAGE_1_OBSERVATION_DIGEST
out["stage_1_owner_cleared"] = stage_1.is_owner_cleared()

# ------------------------------------------------------------- dispositions
dispositions = {
    chain: json.loads((STAGE / f"DISPOSITION-{chain}.json").read_bytes()) for chain in CHAINS
}
out["dispositions_loaded"] = len(dispositions)
observed_disposition_digests = sorted(m.sha256(dict(r)) for r in dispositions.values())

# ------------------------------------------------- environment v0.2 observation
env_payload = ENV_V2.read_bytes()
observed_env_sha = hashlib.sha256(env_payload).hexdigest()
out["environment_v0_2_bytes"] = len(env_payload)
out["environment_v0_2_sha256_observed"] = observed_env_sha
out["environment_v0_2_sha256_matches"] = observed_env_sha == ENVIRONMENT_V0_2_SHA256

candidate_payload = CANDIDATE.read_bytes()
out["candidate_bytes"] = len(candidate_payload)
out["candidate_sha256"] = hashlib.sha256(candidate_payload).hexdigest()
candidate = json.loads(candidate_payload)
declared = candidate["bindings"]

# ----------------------------------------------- shadow binding recomputation
observed = {
    "implementation_commit": subprocess.run(
        ["git", "-C", str(REPO), "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip(),
    "implementation_tree": subprocess.run(
        ["git", "-C", str(REPO), "rev-parse", "HEAD^{tree}"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip(),
    "environment_manifest_sha256": observed_env_sha,
    "mission_package_sha256": frozen.package_sha256,
    "stage_1_component_profile_sha256": m.STAGE_1_COMPONENT_PROFILE_SHA256,
    "oracle_sha256": m.ORACLE_SHA256,
    "adjudication_protocol_sha256": m.ADJUDICATION_PROTOCOL_SHA256,
    "action_plan_sha256": plan.sha256_hex,
    "action_plan_provenance_token": plan.provenance_token,
    "owner_preexecution_interpretation_sha256": m.OWNER_PREEXECUTION_INTERPRETATION_SHA256,
    "stage_1_raw_result_sha256": m.STAGE_1_RAW_RESULT_SHA256,
    "stage_1_observation_digest": stage_1.digest(),
    "human_disposition_evidence_commit": m.HUMAN_DISPOSITION_EVIDENCE_COMMIT,
    "human_disposition_evidence_tree": m.HUMAN_DISPOSITION_EVIDENCE_TREE,
    "correction_stimulus_digest": plan.correction.digest(),
    "owner_m08_m09_acceptance_sha256": m.OWNER_M08_M09_ACCEPTANCE_SHA256,
}
out["binding_field_count_checked"] = len(observed)
out["binding_field_set_equals_implementation_contract"] = sorted(observed) == sorted(
    m.STAGE_2_AUTHORIZATION_BINDING_FIELDS
)
mismatched = sorted(n for n, v in observed.items() if declared.get(n) != v)
out["shadow_binding_mismatches"] = mismatched
out["shadow_binding_comparison"] = f"{len(observed) - len(mismatched)}/{len(observed)}"

declared_dispositions = [str(v) for v in declared["stage_2_human_disposition_binding_digests"]]
per_chain = {
    chain: m.sha256(dict(record)) in declared_dispositions
    for chain, record in dispositions.items()
}
out["shadow_disposition_matches"] = sum(per_chain.values())
out["shadow_disposition_comparison"] = f"{sum(per_chain.values())}/9"
out["shadow_disposition_sets_identical"] = (
    sorted(declared_dispositions) == observed_disposition_digests
)

# ------------------------------------------------ declarations, path, absences
out["declaration_mismatches"] = sorted(
    f"{k}={candidate.get(k)!r} (required {v!r})"
    for k, v in m.STAGE_2_AUTHORIZATION_DECLARATIONS.items()
    if candidate.get(k) is not v and candidate.get(k) != v
)
out["auth_001_canonical_path_exists"] = AUTH_001_CANONICAL.exists()
out["auth_002_canonical_path_exists"] = AUTH_002_CANONICAL.exists()
out["attempt_records_in_run_dir"] = sorted(p.name for p in RUN_DIR.glob(".cdc-e2e-stage-2-*"))
out["attempt_records_anywhere_in_run_tree"] = sorted(
    str(p) for p in RUN_DIR.rglob(".cdc-e2e-stage-2-*")
)

# ------------------------------- the real verifier, invoked at the review path
runtime = m.RuntimeIdentity(
    implementation_commit=observed["implementation_commit"],
    implementation_tree=observed["implementation_tree"],
    environment_manifest_sha256=observed_env_sha,
)
clearance = m.ExecutionClearance(
    owner_execution_authorization=f"sha256:{out['candidate_sha256']}",
    implementation_commit=observed["implementation_commit"],
    implementation_tree=observed["implementation_tree"],
    environment_manifest_sha256=observed_env_sha,
    mission_package_sha256=frozen.package_sha256,
    oracle_sha256=m.ORACLE_SHA256,
    adjudication_protocol_sha256=m.ADJUDICATION_PROTOCOL_SHA256,
    action_plan_sha256=plan.sha256_hex,
    owner_preexecution_interpretation_sha256=m.OWNER_PREEXECUTION_INTERPRETATION_SHA256,
    stage_1_component_profile_sha256=m.STAGE_1_COMPONENT_PROFILE_SHA256,
)
try:
    m.verify_owner_stage_2_authorization(
        CANDIDATE,
        clearance=clearance,
        runtime=runtime,
        frozen=frozen,
        stage_1=stage_1,
        dispositions=dispositions,
        action_plan=plan,
    )
except m.OwnerStage2AuthorizationError as error:
    message = str(error)
    out["actual_verifier_executed"] = True
    out["actual_verifier_exception"] = type(error).__name__
    out["actual_verifier_message"] = message
    # Classified from the observed refusal text, never inferred from source.
    out["ACTUAL_VERIFIER_RESULT"] = (
        "CANONICAL_PATH_MISMATCH"
        if "a relocated copy is not a second issuance" in message
        else "REFUSED_FOR_ANOTHER_REASON"
    )
else:
    out["actual_verifier_executed"] = True
    out["ACTUAL_VERIFIER_RESULT"] = "ACCEPTED_UNEXPECTEDLY"

print(json.dumps(out, indent=2, sort_keys=True))
