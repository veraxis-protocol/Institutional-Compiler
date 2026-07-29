"""Open Institutional Compiler - non-semantic infrastructure foundation.

This package contains repository infrastructure only: artifact hashing, manifest
verification, JSON Schema discovery and validation, environment diagnostics, and the
CLI that exposes them.

It contains no semantic implementation. It does not interpret institutional documents,
determine authority, record admission, produce an Open Control Envelope, generate Rego,
or call ZTL or VEIP. The semantic implementation gate is BLOCKED (see ``STATUS.md``).
"""

from __future__ import annotations

__all__ = ["__version__"]

__version__ = "0.1.0a0"
