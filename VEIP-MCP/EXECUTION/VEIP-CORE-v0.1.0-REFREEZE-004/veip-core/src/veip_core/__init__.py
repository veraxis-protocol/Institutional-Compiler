"""Public API for veip-core v0.1.0."""

from .engine import adjudicate
from .errors import EngineError
from .explain import explain_boundary

__all__ = ["EngineError", "adjudicate", "explain_boundary"]
__version__ = "0.1.0"
