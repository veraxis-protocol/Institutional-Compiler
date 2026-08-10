# CDC-EXEC-VERTICAL-SLICE-001 — Claude merge-portability rehearsal v0.1

Non-mutating analysis only. No branch was merged, rebased, pushed or modified.

## Coordinates

```text
claude_branch          = cdc-exec-vertical-slice-001-adversarial
claude_branch_base     = 617370e53ee72910408ef3f5d34785f430085ce1
target_core_snapshot   = 673bb27b134e43369b4028e9f35af1a0c1a60734
relationship           = target is a direct descendant of the base
delta_base_to_target   = 1 file added
                         docs/operations/CDC-EXEC-VERTICAL-SLICE-001-FO-2-BASELINE-SUITE-FAILURE.md
```

## Result

```text
core_files_modified_by_claude   = 0
integration_files_added         = 12
path_conflicts                  = 0
semantic_surface_conflicts      = 0
expected_manual_merge_points    = 0
```

Required assertions:

```text
src/oic/cdc_slice.py modified by Claude        = FALSE
tests/unit/test_cdc_slice.py modified by Claude = FALSE
```

Both verified by `git status --porcelain` against each path: `UNMODIFIED`.

## Added paths

All additions are new files on paths absent from the target tree, so applying
this preparation onto `673bb27b` is an add-only operation.

```text
scripts/cdc_slice_run_plan.py
scripts/cdc_slice_evidence_skeleton.py
scripts/cdc_slice_adjudication_handoff.py
scripts/cdc_slice_render_deliverable.py
scripts/cdc_slice_reproduce.sh
tests/integration/cdc_slice_corpus.py
tests/integration/cdc_slice_adversarial.py
tests/integration/cdc_slice_harness.py
tests/integration/cdc_slice_interlock.py
tests/integration/cdc_slice_observation.py
tests/integration/test_cdc_slice_preparation.py
docs/operations/CDC-EXEC-VERTICAL-SLICE-001-CLAUDE-MERGE-PORTABILITY-v0.1.md
```

Collision check: every added path was compared against the full recursive file
list of the target tree. No path appears in both.

## Seam requirements

None discovered. No modification to a Codex-owned file is required by this
preparation.

One seam is worth naming even though it is not a conflict today. The baseline
contract test `tests/contract/test_warrant_contract.py::test_this_work_order_added_no_source_module`
asserts the exact `src/oic` module set. Codex amended that guard when it added
`src/oic/cdc_slice.py`. This preparation adds **no** source module, so it does
not interact with that guard. If a future result-bearing stage needs runtime
code under `src/oic/`, the guard becomes a shared seam and the amendment is
Codex's to make, not mine.

## First-observation provenance

The future package must reference these and must not orphan them on merge:

```text
FO-1  fe6aeee35c5aa097812e88128ca1f88bc5f5616171eaefc90a0ca91451ba644b
FO-2  9c1a3c56a03d0608c837a6ed0ec43e1b81d1caa25004b624c4151ff4c9c483f9
FO-3  5c4fd18587ef75d408a7d818c761ae5cbc2490be9ec0df81abe8f9602e2dc927
```

They are carried in two places that survive a merge: section `01-BASELINES` of
the evidence-package skeleton, and `first_observation_provenance` in the run
plan. Neither is reinterpreted here; both are references only.

## Unresolved external identities

Declared by the work order but not resolvable on this machine. Recorded as
declared rather than fabricated:

```text
semantic_oracle          2ce3bdab0acc6a0411f63a20e32164c1f0c8d4a9   commit absent locally
adjudication_protocol    ff78860882748d3f03754f240e7a5c7f1873b174   commit absent locally
merge_seam_checklist     ff78860882748d3f03754f240e7a5c7f1873b174   commit absent locally
```

Neither commit exists in `open-institutional-compiler` nor in the Review Ledger.
The declared SHA-256 values are recorded, and every consumer marks them
`DECLARED_NOT_RESOLVABLE_ON_THIS_MACHINE`. The merge-seam checklist itself could
therefore not be applied; this rehearsal follows the work order's stated fields
instead.
