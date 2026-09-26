from __future__ import annotations

import hashlib
from pathlib import Path
import struct
import sys
import unittest


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from veip_core.canonical import dumps, sha256  # noqa: E402


NUMBER_VECTORS = [
    ("0000000000000000", "0"),
    ("8000000000000000", "0"),
    ("0000000000000001", "5e-324"),
    ("8000000000000001", "-5e-324"),
    ("7fefffffffffffff", "1.7976931348623157e+308"),
    ("ffefffffffffffff", "-1.7976931348623157e+308"),
    ("4340000000000000", "9007199254740992"),
    ("c340000000000000", "-9007199254740992"),
    ("4430000000000000", "295147905179352830000"),
    ("44b52d02c7e14af5", "9.999999999999997e+22"),
    ("44b52d02c7e14af6", "1e+23"),
    ("44b52d02c7e14af7", "1.0000000000000001e+23"),
    ("444b1ae4d6e2ef4e", "999999999999999700000"),
    ("444b1ae4d6e2ef4f", "999999999999999900000"),
    ("444b1ae4d6e2ef50", "1e+21"),
    ("3eb0c6f7a0b5ed8c", "9.999999999999997e-7"),
    ("3eb0c6f7a0b5ed8d", "0.000001"),
    ("41b3de4355555553", "333333333.3333332"),
    ("41b3de4355555554", "333333333.33333325"),
    ("41b3de4355555555", "333333333.3333333"),
    ("41b3de4355555556", "333333333.3333334"),
    ("41b3de4355555557", "333333333.33333343"),
    ("becbf647612f3696", "-0.0000033333333333333333"),
    ("43143ff3c1cb0959", "1424953923781206.2"),
]


def value_from_hex(bits: str) -> float:
    return struct.unpack(">d", bytes.fromhex(bits))[0]


class JCSConformanceTests(unittest.TestCase):
    def test_rfc_8785_sample(self) -> None:
        value = {
            "numbers": [333333333.33333329, 1e30, 4.50, 2e-3, 1e-27],
            "string": "€$\u000f\nA'B\"\\\\\"/"  ,
            "literals": [None, True, False],
        }
        expected = (
            '{"literals":[null,true,false],'
            '"numbers":[333333333.3333333,1e+30,4.5,0.002,1e-27],'
            '"string":"€$\\u000f\\nA\'B\\"\\\\\\\\\\"/"}'
        )
        self.assertEqual(expected, dumps(value))

    def test_rfc_8785_appendix_b_number_vectors(self) -> None:
        for bits, expected in NUMBER_VECTORS:
            with self.subTest(bits=bits):
                self.assertEqual(expected, dumps(value_from_hex(bits)))

    def test_non_finite_numbers_are_rejected(self) -> None:
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    dumps(value)

    def test_integer_domain_boundary(self) -> None:
        self.assertEqual("9007199254740991", dumps(9007199254740991))
        self.assertEqual("-9007199254740991", dumps(-9007199254740991))
        for value in (9007199254740992, -9007199254740992, 2**68):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    dumps(value)

    def test_utf16_property_order(self) -> None:
        value = {
            "€": "Euro Sign",
            "\r": "Carriage Return",
            "דּ": "Hebrew Letter Dalet With Dagesh",
            "1": "One",
            "\U0001f600": "Emoji: Grinning Face",
            "\u0080": "Control",
            "ö": "Latin Small Letter O With Diaeresis",
        }
        expected = (
            '{"\\r":"Carriage Return","1":"One","\u0080":"Control",'
            '"ö":"Latin Small Letter O With Diaeresis","€":"Euro Sign",'
            '"\U0001f600":"Emoji: Grinning Face","דּ":"Hebrew Letter Dalet With Dagesh"}'
        )
        self.assertEqual(expected, dumps(value))

    def test_control_character_escaping(self) -> None:
        value = "".join(chr(i) for i in range(0x20)) + '"' + "\\" + "/" + "€"
        expected = (
            '"\\u0000\\u0001\\u0002\\u0003\\u0004\\u0005\\u0006\\u0007'
            "\\b\\t\\n\\u000b\\f\\r"
            "\\u000e\\u000f\\u0010\\u0011\\u0012\\u0013\\u0014\\u0015"
            "\\u0016\\u0017\\u0018\\u0019\\u001a\\u001b\\u001c\\u001d"
            '\\u001e\\u001f\\"\\\\/€"'
        )
        self.assertEqual(expected, dumps(value))

    def test_lone_surrogates_are_rejected(self) -> None:
        for value in ("\ud800", "\udfff"):
            with self.subTest(value=repr(value)):
                with self.assertRaises(ValueError):
                    dumps(value)

    def test_nested_payload_digest(self) -> None:
        value = {
            "z": [
                {"\U0001f600": -0.0, "€": 1e21, "a": "\u000f"},
                [333333333.33333329, 1e-7],
            ],
            "a": {"b": True, "a": None},
        }
        canonical = (
            '{"a":{"a":null,"b":true},"z":[{"a":"\\u000f",'
            '"€":1e+21,"\U0001f600":0},[333333333.3333333,1e-7]]}'
        )
        self.assertEqual(canonical, dumps(value))
        self.assertEqual(
            hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
            sha256(value),
        )


if __name__ == "__main__":
    unittest.main()
