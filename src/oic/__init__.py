"""Open Institutional Compiler - infrastructure and bounded reference implementation.

This package contains repository infrastructure only: artifact hashing, manifest
verification, JSON Schema discovery and validation, environment diagnostics, and the
CLI that exposes them.

The separately admitted reference path handles synthetic candidates, supplied admission
evidence and provisional interpretations. It does not establish institutional meaning,
produce an Open Control Envelope, generate Rego, or call ZTL or VEIP. The broader
production semantic gate remains BLOCKED (see ``STATUS.md``).
"""

from __future__ import annotations

from oic.admission import evaluate_admission_bytes
from oic.candidate_extraction import propose_candidate_units
from oic.interpretation_proposal import propose_interpretation
from oic.review_docket import build_review_docket

__all__ = [
    "__version__",
    "build_review_docket",
    "evaluate_admission_bytes",
    "propose_candidate_units",
    "propose_interpretation",
]

__version__ = "0.1.0a0"
