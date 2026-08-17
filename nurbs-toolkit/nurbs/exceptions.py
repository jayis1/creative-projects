"""Custom exception hierarchy for the NURBS toolkit."""


class NURBSError(Exception):
    """Base exception for all NURBS toolkit errors."""


class InvalidKnotVector(NURBSError):
    """Raised when a knot vector is malformed."""


class InvalidControlPoint(NURBSError):
    """Raised when control points are invalid."""


class InvalidWeight(NURBSError):
    """Raised when a weight is non-positive."""


class SingularMatrix(NURBSError):
    """Raised when a linear system is singular."""