"""PostScript error hierarchy."""
class PSError(Exception):
    """Base PostScript error."""
    pass


class PSStackUnderflow(PSError):
    """Stack does not have enough operands."""
    pass


class PSTypeError(PSError):
    """Operand on the stack has the wrong type."""
    pass


class PSUndefined(PSError):
    """Reference to an undefined name or resource."""
    pass


class PSRangeCheck(PSError):
    """Value out of the expected range."""
    pass


class PSInvalidAccess(PSError):
    """Invalid access (e.g. modifying read-only dict)."""
    pass


class PSSyntaxError(PSError):
    """Tokenization / parsing error."""
    pass


class PSVMError(PSError):
    """Virtual memory error (allocation limit)."""
    pass