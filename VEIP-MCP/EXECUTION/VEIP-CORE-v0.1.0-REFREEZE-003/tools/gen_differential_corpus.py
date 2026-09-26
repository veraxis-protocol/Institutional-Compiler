#!/usr/bin/env python3
"""
Generate the 999,511-value IEEE-754 differential corpus with Python canonical values.

Segments (deterministic, seed 0xC0FFEE):
  1. 600,000 random float64 values (seed 0xC0FFEE)
  2. 150,000 random integer-valued float64 in [-2^53, 2^53]
  3. 249,483 boundary/stress values (subnormals, powers-of-2, extra random)
  4.      24 RFC 8785 Appendix B canonical number vectors
  5.       4 special zero/near-zero values
Total: 999,511

Output: inputs/differential_corpus.jsonl
Each line: {"bits": "<16hex>", "py": "<python canonical string>"}
"""
from __future__ import annotations

import json
import random
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "veip-core" / "src"))
from veip_core.canonical import dumps  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "inputs" / "differential_corpus.jsonl"


def float_from_hex(bits: str) -> float:
    return struct.unpack(">d", bytes.fromhex(bits))[0]


def rand_float64(rng: random.Random) -> float:
    while True:
        raw = rng.getrandbits(64)
        exp = (raw >> 52) & 0x7FF
        if exp != 0x7FF:
            return struct.unpack(">d", raw.to_bytes(8, "big"))[0]


RFC8785_APPENDIX_B_BITS = [
    "0000000000000000", "8000000000000000", "0000000000000001", "8000000000000001",
    "7fefffffffffffff", "ffefffffffffffff", "4340000000000000", "c340000000000000",
    "4430000000000000", "44b52d02c7e14af5", "44b52d02c7e14af6", "44b52d02c7e14af7",
    "444b1ae4d6e2ef4e", "444b1ae4d6e2ef4f", "444b1ae4d6e2ef50", "3eb0c6f7a0b5ed8c",
    "3eb0c6f7a0b5ed8d", "41b3de4355555553", "41b3de4355555554", "41b3de4355555555",
    "41b3de4355555556", "41b3de4355555557", "becbf647612f3696", "43143ff3c1cb0959",
]

SPECIAL_BITS = [
    "0000000000000000",  # +0.0
    "8000000000000000",  # -0.0
    "0000000000000001",  # 5e-324 (min positive subnormal)
    "8000000000000001",  # -5e-324
]


def main() -> int:
    rng = random.Random(0xC0FFEE)
    values: list[float] = []

    for _ in range(600_000):
        values.append(rand_float64(rng))

    limit = 2**53
    for _ in range(150_000):
        values.append(float(rng.randint(-limit, limit)))

    # Subnormal sweep: first 65,536 positive subnormals
    for mantissa in range(0, 65_536):
        values.append(struct.unpack(">d", mantissa.to_bytes(8, "big"))[0])
    # Powers of 2: exponents 1..1023 and their negatives
    for exp in range(1, 1024):
        bits_pos = exp << 52
        bits_neg = bits_pos | (1 << 63)
        values.append(struct.unpack(">d", bits_pos.to_bytes(8, "big"))[0])
        values.append(struct.unpack(">d", bits_neg.to_bytes(8, "big"))[0])
    already = 65_536 + 1023 * 2
    remaining = 249_483 - already
    for _ in range(remaining):
        values.append(rand_float64(rng))

    for bits in RFC8785_APPENDIX_B_BITS:
        values.append(float_from_hex(bits))

    for bits in SPECIAL_BITS:
        values.append(float_from_hex(bits))

    assert len(values) == 999_511, f"Expected 999511, got {len(values)}"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        for v in values:
            bits = struct.pack(">d", v).hex()
            py_canon = dumps(v)
            f.write(json.dumps({"bits": bits, "py": py_canon}, separators=(",", ":")) + "\n")

    print(f"Written {len(values)} entries to {OUT}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
