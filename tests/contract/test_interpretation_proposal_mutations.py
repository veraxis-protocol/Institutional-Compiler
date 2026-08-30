"""Mutation tests for the interpretation-proposal boundary and its instrument.

Each case weakens one exact line of the production module or the harness, loads the result
as a separate module, and requires a named probe to notice. A mutation that survives names
a property nothing actually checks.

Two of these matter more than the rest, because they are the failure modes that would make
the whole characterization worthless: sending the answer key to the provider, and quietly
repairing a defect before measuring it.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

pytestmark = pytest.mark.contract

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "src/oic/interpretation_proposal.py"
HARNESS_PATH = ROOT / "scripts/characterize_interpretation_proposal.py"
CORPUS_PATH = ROOT / "benchmarks/characterization/interpretation-proposal-001/CORPUS-v0.1.json"

SPAN = "The Records Officer must retain each closed file for seven years."
RECEIPT_ID = "admrec-sha256:" + "a" * 64
UNIT_ID = "cnu-" + "b" * 24
PROJECTION_DIGEST = "sha256:" + "c" * 64


def _mutate(source: str, old: str, new: str) -> str:
    count = source.count(old)
    if count != 1:
        raise AssertionError(f"mutation target appears {count} times, expected 1: {old!r}")
    return source.replace(old, new, 1)


def _load_many(name: str, path: Path, pairs: tuple[tuple[str, str], ...]) -> ModuleType:
    source = path.read_text(encoding="utf-8")
    for old, new in pairs:
        source = _mutate(source, old, new)
    return _exec(name, path, source)


def _load(name: str, path: Path, old: str, new: str) -> ModuleType:
    return _load_many(name, path, ((old, new),))


def _unmutated(name: str, path: Path) -> ModuleType:
    """The control. Without it a probe that fails on everything would look perfect."""
    return _exec(name, path, path.read_text(encoding="utf-8"))


def _exec(name: str, path: Path, source: str) -> ModuleType:
    module_name = f"_oic_proposal_mutant_{name}"
    spec = importlib.util.spec_from_loader(module_name, loader=None)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    module.__file__ = str(path)
    sys.modules[module_name] = module
    try:
        exec(compile(source, str(path), "exec"), module.__dict__)  # noqa: S102
    finally:
        sys.modules.pop(module_name, None)
    return module


class Recorder:
    def __init__(self, content: str = '{"proposed_assertions":[]}') -> None:
        self.calls: list[Any] = []
        self.content = content

    def complete(self, request: Any) -> Any:  # noqa: ANN401 - mutant modules are dynamic
        from oic.model_provider import ModelResponse

        self.calls.append(request)
        return ModelResponse(
            provider="fake", model="fake", content=self.content, request_id=None, raw={}
        )


def _binding(module: ModuleType, state: str = "ADMITTED", unit_type: str | None = None) -> Any:  # noqa: ANN401 - mutant modules are dynamic
    return module.AdmittedCandidateBinding(
        admission_receipt_id=RECEIPT_ID,
        admission_state=state,
        candidate_unit_id=UNIT_ID,
        candidate_projection_digest=PROJECTION_DIGEST,
        candidate_span=SPAN,
        provisional_unit_type=unit_type,
    )


def _refuses(module: ModuleType, content: str) -> bool:
    """True when the mutant still refuses this payload."""
    provider = Recorder(content)
    try:
        module.propose_interpretation(
            binding=_binding(module), provider=provider, proposer_id="probe"
        )
    except module.ProposalBoundaryError:
        return True
    except Exception:  # any refusal at all counts
        return True
    return False


# ---------------------------------------------------------------------------
# Boundary mutations: the probe must notice the weakening
# ---------------------------------------------------------------------------

_CONFIDENCE = json.dumps(
    {
        "proposed_assertions": [
            {
                "slot": "bearer",
                "proposed_value": "x",
                "proposed_source_quote": None,
                "confidence": 0.99,
            }
        ]
    }
)
_CANONICAL = json.dumps(
    {
        "proposed_assertions": [
            {
                "slot": "bearer",
                "proposed_value": "x",
                "proposed_source_quote": None,
                "canonical": True,
            }
        ]
    }
)
_STATUS = json.dumps(
    {
        "proposed_assertions": [
            {"slot": "bearer", "proposed_value": "ESTABLISHED", "proposed_source_quote": None}
        ]
    }
)
_RECEIPT_OVERRIDE = json.dumps(
    {
        "proposed_assertions": [],
        "admission_receipt_id": "admrec-sha256:" + "9" * 64,
    }
)
_BAD_FORCE = json.dumps(
    {
        "proposed_assertions": [
            {"slot": "normative_force", "proposed_value": "MANDATE", "proposed_source_quote": None}
        ]
    }
)


_UNEXPECTED_ASSERTION_KEY_CHECK = (
    "    unexpected = set(item) - _ASSERTION_ALLOWED_KEYS\n"
    "    if unexpected:\n"
    "        raise ProposalBoundaryError(\n"
    '            f"proposed assertion {index} has unexpected fields: {sorted(unexpected)}"\n'
    "        )\n"
)
_FORBIDDEN_SCAN = "    forbidden: set[str] = set()\n    _forbidden_keys_in(parsed, forbidden)\n"
_ROOT_KEY_CHECK = (
    "    unexpected = set(parsed) - _ROOT_KEYS\n"
    "    if unexpected:\n"
    "        raise ProposalBoundaryError(\n"
    '            f"provider proposal output has unexpected root keys: {sorted(unexpected)}"\n'
    "        )\n"
)


def test_m01_allowing_a_confidence_field_is_caught() -> None:
    """Two independent layers refuse it. Both are proved load-bearing.

    Removing the structural key check alone still refuses, because the deep forbidden-key
    scan catches it. Removing both accepts it -- which is what makes the scan more than
    decoration.
    """
    one_layer = _load("m01a", MODULE_PATH, _UNEXPECTED_ASSERTION_KEY_CHECK, "")
    assert _refuses(one_layer, _CONFIDENCE), "the deep scan must still refuse on its own"
    no_layers = _load_many(
        "m01b",
        MODULE_PATH,
        (
            (_UNEXPECTED_ASSERTION_KEY_CHECK, ""),
            (_FORBIDDEN_SCAN, "    forbidden: set[str] = set()\n"),
        ),
    )
    assert not _refuses(no_layers, _CONFIDENCE), "removing both layers must actually accept it"
    assert _refuses(_unmutated("m01_control", MODULE_PATH), _CONFIDENCE)


def test_m02_allowing_a_canonical_field_is_caught() -> None:
    one_layer = _load("m02a", MODULE_PATH, _UNEXPECTED_ASSERTION_KEY_CHECK, "")
    assert _refuses(one_layer, _CANONICAL)
    no_layers = _load_many(
        "m02b",
        MODULE_PATH,
        (
            (_UNEXPECTED_ASSERTION_KEY_CHECK, ""),
            ('        "canonical",\n', ""),
        ),
    )
    assert not _refuses(no_layers, _CANONICAL), "removing both layers must actually accept it"
    assert _refuses(_unmutated("m02_control", MODULE_PATH), _CANONICAL)


def test_m03_allowing_an_established_status_in_model_output_is_caught() -> None:
    mutant = _load(
        "m03",
        MODULE_PATH,
        "    tokens: set[str] = set()\n    _forbidden_value_tokens_in(parsed, tokens)\n",
        "    tokens: set[str] = set()\n",
    )
    assert not _refuses(mutant, _STATUS)


def test_m04_letting_a_model_supply_an_admission_receipt_id_is_caught() -> None:
    """The model is never asked for a binding field, and cannot smuggle one in."""
    one_layer = _load("m04a", MODULE_PATH, _ROOT_KEY_CHECK, "")
    assert _refuses(one_layer, _RECEIPT_OVERRIDE), "the deep scan must still refuse on its own"
    no_layers = _load_many(
        "m04b",
        MODULE_PATH,
        (
            (_ROOT_KEY_CHECK, ""),
            ('        "admission_receipt_id",\n        "admission_state",\n', ""),
        ),
    )
    assert not _refuses(no_layers, _RECEIPT_OVERRIDE)
    # Even then, the envelope is written by OIC, so the model's value never survives.
    provider = Recorder(_RECEIPT_OVERRIDE)
    result = no_layers.propose_interpretation(
        binding=_binding(no_layers), provider=provider, proposer_id="probe"
    )
    assert result.proposal["admission_receipt_id"] == RECEIPT_ID


def test_m05_accepting_an_invented_normative_force_is_caught() -> None:
    mutant = _load(
        "m05",
        MODULE_PATH,
        '    if slot == "normative_force" and value is not None and value not in FORCE_VALUES:\n',
        "    if False:\n",
    )
    assert not _refuses(mutant, _BAD_FORCE)


def test_m06_accepting_an_unknown_slot_is_caught() -> None:
    mutant = _load(
        "m06",
        MODULE_PATH,
        "    if not isinstance(slot, str) or slot not in SLOT_VOCABULARY:\n",
        "    if not isinstance(slot, str):\n",
    )
    payload = json.dumps(
        {
            "proposed_assertions": [
                {"slot": "invented", "proposed_value": "x", "proposed_source_quote": None}
            ]
        }
    )
    assert not _refuses(mutant, payload)


def test_m07_calling_the_provider_for_non_admitted_input_is_caught() -> None:
    mutant = _load(
        "m07",
        MODULE_PATH,
        '    if binding.admission_state != "ADMITTED":\n',
        "    if False:\n",
    )
    provider = Recorder()
    mutant.propose_interpretation(
        binding=_binding(mutant, "REVOKED"), provider=provider, proposer_id="probe"
    )
    assert provider.calls, "the mutation must actually let a non-ADMITTED input through"
    # The real module refuses and makes no call. That is the property under test.
    from oic.interpretation_proposal import ProposalInputBoundaryError, propose_interpretation

    honest = Recorder()
    with pytest.raises(ProposalInputBoundaryError):
        propose_interpretation(
            binding=_binding(sys.modules["oic.interpretation_proposal"], "REVOKED"),
            provider=honest,
            proposer_id="probe",
        )
    assert honest.calls == []


# ---------------------------------------------------------------------------
# Repair mutations: the instrument must never launder a defect
# ---------------------------------------------------------------------------


def test_m08_silently_repairing_an_ungrounded_quote_is_caught() -> None:
    """A repair here would make metric I report perfect grounding over a broken model."""
    mutant = _load(
        "m08",
        MODULE_PATH,
        '    normalized: JsonObject = {\n        "slot": slot,\n        "proposed_value": value,\n'
        '        "proposed_source_quote": quote,\n    }\n',
        '    normalized: JsonObject = {\n        "slot": slot,\n        "proposed_value": value,\n'
        '        "proposed_source_quote": None,\n    }\n',
    )
    payload = json.dumps(
        {
            "proposed_assertions": [
                {
                    "slot": "bearer",
                    "proposed_value": "x",
                    "proposed_source_quote": "not in the source",
                }
            ]
        }
    )
    provider = Recorder(payload)
    result = mutant.propose_interpretation(
        binding=_binding(mutant), provider=provider, proposer_id="probe"
    )
    repaired = result.proposal["proposed_assertions"][0]["proposed_source_quote"]
    assert repaired is None, "the mutation must actually repair the quote"

    from oic.interpretation_proposal import propose_interpretation

    honest = propose_interpretation(
        binding=_binding(sys.modules["oic.interpretation_proposal"]),
        provider=Recorder(payload),
        proposer_id="probe",
    )
    assert (
        honest.proposal["proposed_assertions"][0]["proposed_source_quote"] == "not in the source"
    ), "the real module must record the ungrounded quote exactly"


def test_m09_dropping_duplicate_slot_proposals_is_caught() -> None:
    """A proposer contradicting itself is evidence; deduplication would erase it."""
    mutant = _load(
        "m09",
        MODULE_PATH,
        "    assertions = [_normalize_assertion(item, index) for index, item in "
        "enumerate(raw_assertions)]\n",
        "    _seen: set[str] = set()\n"
        "    assertions = []\n"
        "    for index, item in enumerate(raw_assertions):\n"
        "        normalized = _normalize_assertion(item, index)\n"
        '        if normalized["slot"] in _seen:\n'
        "            continue\n"
        '        _seen.add(normalized["slot"])\n'
        "        assertions.append(normalized)\n",
    )
    payload = json.dumps(
        {
            "proposed_assertions": [
                {"slot": "bearer", "proposed_value": "A", "proposed_source_quote": None},
                {"slot": "bearer", "proposed_value": "B", "proposed_source_quote": None},
            ]
        }
    )
    provider = Recorder(payload)
    result = mutant.propose_interpretation(
        binding=_binding(mutant), provider=provider, proposer_id="probe"
    )
    assert len(result.proposal["proposed_assertions"]) == 1, "the mutation must actually dedupe"

    from oic.interpretation_proposal import propose_interpretation

    honest = propose_interpretation(
        binding=_binding(sys.modules["oic.interpretation_proposal"]),
        provider=Recorder(payload),
        proposer_id="probe",
    )
    assert [item["proposed_value"] for item in honest.proposal["proposed_assertions"]] == [
        "A",
        "B",
    ]


def test_m10_treating_the_provisional_unit_type_as_canonical_force_is_caught() -> None:
    """The prior stage's guess must never become this stage's answer."""
    mutant = _load(
        "m10",
        MODULE_PATH,
        "    envelope = build_proposal_envelope(\n",
        "    if binding.provisional_unit_type is not None and not any(\n"
        '        item["slot"] == "normative_force" for item in assertions\n'
        "    ):\n"
        "        assertions.insert(\n"
        "            0,\n"
        "            {\n"
        '                "slot": "normative_force",\n'
        '                "proposed_value": "OBLIGATION",\n'
        '                "proposed_source_quote": None,\n'
        "            },\n"
        "        )\n"
        "    envelope = build_proposal_envelope(\n",
    )
    provider = Recorder('{"proposed_assertions":[]}')
    result = mutant.propose_interpretation(
        binding=_binding(mutant, unit_type="mandate"), provider=provider, proposer_id="probe"
    )
    assert result.proposal["proposed_assertions"], "the mutation must actually inject a force"

    from oic.interpretation_proposal import propose_interpretation

    honest = propose_interpretation(
        binding=_binding(sys.modules["oic.interpretation_proposal"], unit_type="mandate"),
        provider=Recorder('{"proposed_assertions":[]}'),
        proposer_id="probe",
    )
    assert honest.proposal["proposed_assertions"] == [], (
        "the real module must never derive a force from the provisional unit_type"
    )


def test_m11_sending_the_gold_expected_ir_in_the_prompt_is_caught() -> None:
    """The prompt-purity invariant is the check; this proves it is not vacuous."""
    mutant = _load(
        "m11",
        MODULE_PATH,
        '        f"ADMITTED PROPOSITION:\\n{binding.candidate_span}"\n',
        '        f"ADMITTED PROPOSITION:\\n{binding.candidate_span}\\n"\n'
        '        f"EXPECTED FORCE: {binding.admission_state}"\n',
    )
    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    remainders = set()
    for specimen in corpus["specimens"][:3]:
        provider = Recorder()
        candidate = specimen["candidate"]
        admission = specimen["admission"]
        mutant.propose_interpretation(
            binding=mutant.AdmittedCandidateBinding(
                admission_receipt_id=admission["admission_receipt_id"],
                admission_state="ADMITTED",
                candidate_unit_id=admission["candidate_unit_id"],
                candidate_projection_digest=admission["candidate_projection_digest"],
                candidate_span=candidate["candidate_span"],
            ),
            provider=provider,
            proposer_id="probe",
        )
        prompt = provider.calls[0].system_prompt + provider.calls[0].user_prompt
        remainders.add(prompt.replace(candidate["candidate_span"], "<PROPOSITION>"))
    assert "EXPECTED FORCE" in next(iter(remainders)), "the mutation must actually leak"


def test_m12_sending_authority_evidence_in_the_prompt_is_caught() -> None:
    mutant = _load(
        "m12",
        MODULE_PATH,
        '        f"ADMITTED PROPOSITION:\\n{binding.candidate_span}"\n',
        '        f"ADMITTED PROPOSITION:\\n{binding.candidate_span}\\n"\n'
        '        f"AUTHORITY EVIDENCE: {binding.admission_receipt_id}"\n',
    )
    provider = Recorder()
    mutant.propose_interpretation(binding=_binding(mutant), provider=provider, proposer_id="probe")
    prompt = provider.calls[0].user_prompt
    assert RECEIPT_ID in prompt, "the mutation must actually leak the admission binding"

    from oic.interpretation_proposal import propose_interpretation

    honest = Recorder()
    propose_interpretation(
        binding=_binding(sys.modules["oic.interpretation_proposal"]),
        provider=honest,
        proposer_id="probe",
    )
    assert RECEIPT_ID not in honest.calls[0].user_prompt


def test_m13_converting_a_proposal_into_institutional_ir_is_caught() -> None:
    """The proposal envelope must never grow a canonical field."""
    mutant = _load(
        "m13",
        MODULE_PATH,
        '        "proposed_assertions": assertions,\n    }\n    if references:',
        '        "proposed_assertions": assertions,\n'
        '        "interpretation_status": "ESTABLISHED",\n'
        '        "ir_unit_id": "iir-sha256:" + "0" * 64,\n'
        "    }\n    if references:",
    )
    provider = Recorder()
    result = mutant.propose_interpretation(
        binding=_binding(mutant), provider=provider, proposer_id="probe"
    )
    assert "ir_unit_id" in result.proposal, "the mutation must actually canonicalize"

    from oic.interpretation_proposal import propose_interpretation

    honest = propose_interpretation(
        binding=_binding(sys.modules["oic.interpretation_proposal"]),
        provider=Recorder(),
        proposer_id="probe",
    )
    assert "ir_unit_id" not in honest.proposal
    assert "interpretation_status" not in honest.proposal


# ---------------------------------------------------------------------------
# Harness mutations: the metrics must not stop detecting
# ---------------------------------------------------------------------------


def _harness_mutant(name: str, old: str, new: str) -> ModuleType:
    return _load(name, HARNESS_PATH, old, new)


def _specimen(module: ModuleType, specimen_id: str) -> Any:  # noqa: ANN401 - dynamic
    plan = module.preflight()
    return next(item for item in plan.specimens if item.specimen_id == specimen_id)


def _attempt(module: ModuleType, specimen_id: str, assertions: list[dict[str, Any]]) -> Any:  # noqa: ANN401 - mutant modules are dynamic
    return module.Attempt(
        specimen_id=specimen_id,
        run_index=1,
        outcome=module.ACCEPTED,
        proposal={
            "proposal_id": "iip-probe",
            "admission_receipt_id": RECEIPT_ID,
            "candidate_unit_id": UNIT_ID,
            "candidate_projection_digest": PROJECTION_DIGEST,
            "proposed_assertions": assertions,
        },
    )


def _assertion(slot: str, value: str) -> dict[str, Any]:
    return {"slot": slot, "proposed_value": value, "proposed_source_quote": None}


def test_m14_a_comparison_that_accepts_anything_stops_detecting_invention() -> None:
    mutant = _harness_mutant(
        "m14",
        "    return left in right or right in left\n",
        "    return True\n",
    )
    specimen = _specimen(mutant, "IIR-016")
    swapped = _attempt(mutant, "IIR-016", [_assertion("bearer", "the compliance office")])
    metric = mutant.metric_g_role_separation([specimen], [swapped])
    assert metric["counts"].get("correct_bearer", 0) == 1, (
        "the mutation must actually make everything compatible"
    )

    real = _unmutated("m14_control", HARNESS_PATH)
    real_metric = real.metric_g_role_separation(
        [_specimen(real, "IIR-016")],
        [_attempt(real, "IIR-016", [_assertion("bearer", "the compliance office")])],
    )
    assert real_metric["counts"].get("swapped", 0) == 1
    assert real_metric["counts"].get("correct_bearer", 0) == 0


def test_m15_a_strengthening_detector_that_ignores_dropped_material_is_caught() -> None:
    mutant = _harness_mutant(
        "m15",
        '                if gold["status"] == "ESTABLISHED" and not _values_for_slot('
        "proposal, slot):\n",
        "                if False:\n",
    )
    specimen = _specimen(mutant, "IIR-030")
    attempt = _attempt(mutant, "IIR-030", [_assertion("action", "require")])
    metric = mutant.metric_l_strengthening([specimen], [attempt])
    assert (
        metric["counts"].get("exception_bearing_to_exceptionless_by_dropped_exception", 0) == 0
    ), "the mutation must actually stop detecting"

    real = _unmutated("m15_control", HARNESS_PATH)
    real_metric = real.metric_l_strengthening(
        [_specimen(real, "IIR-030")],
        [_attempt(real, "IIR-030", [_assertion("action", "require")])],
    )
    assert real_metric["counts"]["exception_bearing_to_exceptionless_by_dropped_exception"] == 1


def test_m16_an_ambiguity_metric_that_credits_a_single_choice_is_caught() -> None:
    mutant = _harness_mutant(
        "m16",
        "                elif len(matched) >= 2:\n"
        '                    outcome = "alternatives_preserved"\n',
        "                elif len(matched) >= 1:\n"
        '                    outcome = "alternatives_preserved"\n',
    )
    specimen = _specimen(mutant, "IIR-017")
    single = _attempt(mutant, "IIR-017", [_assertion("bearer", "The department")])
    metric = mutant.metric_f_ambiguity([specimen], [single])
    assert metric["counts"].get("alternatives_preserved", 0) == 1, (
        "the mutation must actually credit a single choice"
    )

    real = _unmutated("m16_control", HARNESS_PATH)
    real_metric = real.metric_f_ambiguity(
        [_specimen(real, "IIR-017")],
        [_attempt(real, "IIR-017", [_assertion("bearer", "The department")])],
    )
    assert real_metric["counts"]["single_alternative_proposed"] == 1
    assert real_metric["counts"].get("alternatives_preserved", 0) == 0


def test_m17_a_grounding_metric_that_counts_everything_grounded_is_caught() -> None:
    mutant = _harness_mutant(
        "m17",
        "            if is_quote_grounded(quote, candidate_span=span):\n",
        "            if True:\n",
    )
    specimen = _specimen(mutant, "IIR-001")
    attempt = mutant.Attempt(
        specimen_id="IIR-001",
        run_index=1,
        outcome=mutant.ACCEPTED,
        proposal={
            "proposed_assertions": [
                {
                    "slot": "bearer",
                    "proposed_value": "x",
                    "proposed_source_quote": "nowhere in the source",
                }
            ]
        },
    )
    metric = mutant.metric_i_quote_grounding([specimen], [attempt])
    assert metric["ungrounded"] == 0, "the mutation must actually stop detecting"

    real = _unmutated("m17_control", HARNESS_PATH)
    real_metric = real.metric_i_quote_grounding(
        [_specimen(real, "IIR-001")],
        [
            real.Attempt(
                specimen_id="IIR-001",
                run_index=1,
                outcome=real.ACCEPTED,
                proposal={
                    "proposed_assertions": [
                        {
                            "slot": "bearer",
                            "proposed_value": "x",
                            "proposed_source_quote": "nowhere in the source",
                        }
                    ]
                },
            )
        ],
    )
    assert real_metric["ungrounded"] == 1


def test_the_mutation_set_covers_every_named_requirement() -> None:
    """The work order names eleven mutations. These are those, plus four for the harness."""
    tests = {name for name in globals() if name.startswith("test_m")}
    for requirement in (
        "m01",  # a confidence field
        "m02",  # a canonical field
        "m03",  # an ESTABLISHED status in model output
        "m04",  # a model-generated admission receipt id overriding the OIC binding
        "m07",  # calling the provider for non-ADMITTED input
        "m08",  # silently repairing an ungrounded quote
        "m09",  # dropping duplicate slot proposals
        "m10",  # treating the provisional unit_type as canonical force
        "m11",  # sending the gold expected IR in the prompt
        "m12",  # sending authority evidence in the prompt
        "m13",  # converting a proposal directly into Institutional IR
    ):
        assert any(name.startswith(f"test_{requirement}") for name in tests), requirement
    assert len(tests) >= 17
