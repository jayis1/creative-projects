"""Custom exception hierarchy for the jpeg-codec package.

These exceptions provide fine-grained error handling so callers can
distinguish between different failure modes (corrupt input, unsupported
features, I/O errors, etc.).
"""


class JPEGError(Exception):
    """Base exception for all jpeg-codec errors."""


class EncodingError(JPEGError):
    """Raised when encoding fails (invalid input, internal error)."""


class DecodingError(JPEGError):
    """Raised when decoding fails (corrupt stream, truncated data)."""


class InvalidMarkerError(DecodingError):
    """Raised when an unexpected or malformed marker is encountered."""

    def __init__(self, marker: int, offset: int, detail: str = ""):
        self.marker = marker
        self.offset = offset
        msg = f"Invalid marker 0x{marker:04X} at offset {offset}"
        if detail:
            msg += f": {detail}"
        super().__init__(msg)


class UnsupportedFeatureError(DecodingError):
    """Raised when the decoder encounters an unsupported JPEG feature.

    Examples: progressive SOS, arithmetic coding, 12-bit precision.
    """

    def __init__(self, feature: str):
        self.feature = feature
        super().__init__(f"Unsupported JPEG feature: {feature}")


class TruncatedDataError(DecodingError):
    """Raised when the bit stream ends prematurely."""


class InvalidQualityError(EncodingError):
    """Raised when quality is outside the valid range [1, 100]."""

    def __init__(self, quality):
        super().__init__(
            f"Quality must be in [1, 100], got {quality}"
        )


class InvalidSamplingError(EncodingError):
    """Raised when an unknown subsampling mode is requested."""

    def __init__(self, mode: str):
        super().__init__(
            f"Unknown sampling mode '{mode}'. "
            f"Valid modes: 4:4:4, 4:2:2, 4:2:0, 4:1:1"
        )


class InvalidImageError(EncodingError):
    """Raised when the input image has an unsupported shape or dtype."""

    def __init__(self, detail: str):
        super().__init__(f"Invalid image: {detail}")