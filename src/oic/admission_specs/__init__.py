"""Byte-identical runtime copies of the frozen Admission Boundary 001 specifications.

These files are data, not code. Each is a byte-for-byte copy of its original under
``design/admission-boundary-001/``; ``oic.admission`` verifies that identity is what the
frozen ruleset digest attests, and the contract suite asserts the bytes still match.
They are packaged so the evaluator runs from an installed wheel without the design tree.
"""

from __future__ import annotations

__all__: list[str] = []
