class TraceParseError(ValueError):
    """Raised when the supported H1 trace format is malformed or ambiguous."""


class TraceNotAdmissible(ValueError):
    """Raised when a parsed trace cannot satisfy the narrow H1 admission contract."""
