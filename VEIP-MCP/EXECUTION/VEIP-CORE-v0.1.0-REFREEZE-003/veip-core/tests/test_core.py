from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

PROJECT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = PROJECT.parent
sys.path.insert(0, str(PROJECT / "src"))

from veip_core import EngineError, adjudicate, explain_boundary  # noqa: E402
from veip_core.canonical import dumps as canonical_dumps  # noqa: E402
from veip_core.manifest import manifest_hash  # noqa: E402
from veip_core.reasons import RESERVED_CODES  # noqa: E402

CORPUS_PATH = PACKAGE_ROOT / "inputs" / "VEIP_CANONICAL_FIXTURES_v0.3.json"


def corpus() -> dict:
    return json.loads(CORPUS_PATH.read_text(encoding="utf-8"))


def execute(fixture: dict) -> dict:
    try:
        if fixture["entry_point"] == "adjudicate":
            return adjudicate(deepcopy(fixture["input"]))
        return explain_boundary(deepcopy(fixture["input"]))
    except EngineError as exc:
        return exc.to_dict()


class FrozenConformanceTests(unittest.TestCase):
    def test_all_frozen_fixtures(self) -> None:
        for fixture in corpus()["fixtures"]:
            with self.subTest(case=fixture["fixture_id"]):
                actual = execute(fixture)
                expected = fixture["expected"]
                if expected["result_type"] == "EngineError":
                    for key in expected["match_scope"]:
                        self.assertEqual(expected[key], actual[key])
                    self.assertTrue(actual["message"])
                else:
                    wanted = {key: value for key, value in expected.items() if key != "result_type"}
                    self.assertEqual(wanted, actual)

    def test_error_precedence_adversarial_cases(self) -> None:
        fixtures = {item["fixture_id"]: item for item in corpus()["fixtures"]}
        for identifier in ("V03-053", "V03-054", "V03-055", "V03-056"):
            with self.subTest(case=identifier):
                self.assertEqual(fixtures[identifier]["expected"]["error_code"], execute(fixtures[identifier])["error_code"])


class AntiMemorizationTests(unittest.TestCase):
    def _successful_adjudications(self) -> list[dict]:
        return [
            item
            for item in corpus()["fixtures"]
            if item["entry_point"] == "adjudicate"
            and item["expected"]["result_type"] in {"ClaimEvaluationResult", "CompletionEvaluationResult"}
        ]

    def test_source_never_reads_fixture_id(self) -> None:
        for source in (PROJECT / "src").rglob("*.py"):
            self.assertNotIn("fixture_id", source.read_text(encoding="utf-8"), source)

    def test_external_fixture_renaming_cannot_change_results(self) -> None:
        fixture = self._successful_adjudications()[0]
        renamed = deepcopy(fixture)
        renamed["fixture_id"] = "RENAMED-WITHOUT-SEMANTIC-EFFECT"
        self.assertEqual(execute(fixture), execute(renamed))

    def test_irrelevant_evidence_order_does_not_change_result(self) -> None:
        fixture = next(
            item
            for item in self._successful_adjudications()
            if len(item["input"]["evidence_pack"]["references"]) >= 2
        )
        changed = deepcopy(fixture)
        changed["input"]["evidence_pack"]["references"].reverse()
        self.assertEqual(execute(fixture), execute(changed))

    def test_unreferenced_decoy_cannot_change_adjudication(self) -> None:
        fixture = next(
            item
            for item in self._successful_adjudications()
            if item["expected"]["result_type"] == "CompletionEvaluationResult"
        )
        changed = deepcopy(fixture)
        pack = changed["input"]["evidence_pack"]
        pack["references"].append(
            {
                "evidence_id": "decoy-not-referenced",
                "payload_sha256": "0" * 64,
                "source_type": "adversarial-decoy",
                "subject_ref": "wrong-subject",
                "extent_ref": "wrong-extent",
            }
        )
        pack["manifest_sha256"] = manifest_hash(pack["references"])
        self.assertEqual(execute(fixture), execute(changed))

    def test_repeated_inputs_are_byte_identical(self) -> None:
        for fixture in self._successful_adjudications():
            first = canonical_dumps(execute(fixture))
            second = canonical_dumps(execute(fixture))
            self.assertEqual(first, second)

    def test_reserved_codes_never_emit_and_positive_ceiling_holds(self) -> None:
        prohibited_positive = {
            "claim_support",
            "execution",
            "outcome",
            "currentness",
            "provenance_binding",
            "task_completion",
        }
        for fixture in self._successful_adjudications():
            result = execute(fixture)
            self.assertFalse(set(result["reason_codes"]) & RESERVED_CODES)
            self.assertEqual("NOT_ESTABLISHED", result["dimensions"]["channel_independence"])
            for dimension in prohibited_positive:
                self.assertNotEqual("ESTABLISHED_WITHIN_SCOPE", result["dimensions"][dimension])


if __name__ == "__main__":
    unittest.main()
