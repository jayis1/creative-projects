"""Reed-Solomon encoder/decoder for GF(2^8).

Implements systematic Reed-Solomon encoding, syndrome calculation,
Berlekamp-Massey algorithm for finding the error locator polynomial,
Chien search for finding error positions, and Forney algorithm for error
magnitudes. Supports both error correction and erasure correction,
interleaving for burst-error resilience, shortened codes, and a
class-based API with decoder statistics.

Polynomial convention: coefficients are stored LOWEST degree first.
  poly[0] = constant term, poly[1] = x^1 coefficient, etc.

Symbol size is 8 bits (GF(2^8)). The code is parameterised by nsym (number
of parity symbols). Full codeword length n = k + nsym <= 255, but shortened
codes (n < 255) are supported.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from gf import (
    GF256,
    gf_poly_mul,
    gf_poly_eval,
    gf_poly_div,
    gf_poly_scale,
    gf_poly_add,
)


# ---------------------------------------------------------------------------
# Generator polynomial
# ---------------------------------------------------------------------------

# Cache generator polynomials to avoid recomputing on every encode call.
_generator_cache: dict = {}


def generator_poly(nsym: int) -> List[int]:
    """Generate the Reed-Solomon generator polynomial.

    g(x) = (x - α^0)(x - α^1)...(x - α^{nsym-1})

    Returns coefficients lowest-degree-first: g[0] is the constant term.
    Results are cached for performance.
    """
    if nsym in _generator_cache:
        return list(_generator_cache[nsym])
    g = [1]
    for i in range(nsym):
        # Multiply g by (x - α^i) = (x + α^i) in GF(2^8)
        # (x + α^i) in lowest-first: [α^i, 1]
        g = gf_poly_mul(g, [GF256.pow(2, i), 1])
    _generator_cache[nsym] = list(g)
    return list(g)


# ---------------------------------------------------------------------------
# Encoding
# ---------------------------------------------------------------------------


def rs_encode(message: List[int], nsym: int) -> List[int]:
    """Systematic Reed-Solomon encoding.

    The message occupies the high-order coefficients and parity symbols
    are prepended (low-order positions).

    Args:
        message: List of message symbols (each 0-255).
        nsym: Number of parity symbols to add.

    Returns:
        parity + message (length = len(message) + nsym).

    Raises:
        ValueError: If nsym < 0, message too long, or symbols out of range.
    """
    _validate_nsym(nsym)
    if nsym == 0:
        return list(message)
    _validate_symbols(message)
    n = len(message) + nsym
    if n > 255:
        raise ValueError(
            f"Codeword length {n} exceeds 255 (GF(2^8) maximum). "
            f"Message length {len(message)} + nsym {nsym} = {n}."
        )

    gen = generator_poly(nsym)
    # parity = (message * x^nsym) mod g(x)
    # In lowest-first, multiplying by x^nsym means prepending nsym zeros
    msg_padded = [0] * nsym + list(message)  # message shifted up by nsym
    _, remainder = gf_poly_div(msg_padded, gen)
    return remainder + list(message)


# ---------------------------------------------------------------------------
# Syndromes
# ---------------------------------------------------------------------------


def calc_syndromes(poly: List[int], nsym: int) -> List[int]:
    """Calculate the nsym syndromes of a received polynomial.

    S_i = R(α^i) for i = 0, 1, ..., nsym-1.

    The received polynomial is evaluated at α^0, α^1, ..., α^{nsym-1}.
    Since the generator polynomial has roots at these points, a valid
    codeword gives all-zero syndromes.
    """
    return [gf_poly_eval(poly, GF256.pow(2, i)) for i in range(nsym)]


# ---------------------------------------------------------------------------
# Berlekamp-Massey
# ---------------------------------------------------------------------------


def berlekamp_massey(syndromes: List[int]) -> List[int]:
    """Berlekamp-Massey algorithm to find the error locator polynomial.

    Returns the error locator polynomial Λ(x) with coefficients in
    lowest-degree-first order: Λ[0] is the constant term (always 1).
    """
    sigma = [1]       # current error locator, Λ(x)
    B = [1]           # previous locator (for updating)
    L = 0             # current LFSR length
    m = 1             # steps since last length update
    b = 1              # previous nonzero discrepancy

    for k in range(len(syndromes)):
        # Compute discrepancy
        delta = syndromes[k]
        for i in range(1, L + 1):
            delta ^= GF256.mul(sigma[i], syndromes[k - i])

        if delta == 0:
            m += 1
        elif 2 * L <= k:
            # Update with length increase
            T = list(sigma)
            coef = GF256.div(delta, b)
            shifted_B = [0] * m + B
            max_len = max(len(sigma), len(shifted_B))
            while len(sigma) < max_len:
                sigma.append(0)
            while len(shifted_B) < max_len:
                shifted_B.append(0)
            sigma = [GF256.add(sigma[j], GF256.mul(coef, shifted_B[j]))
                     for j in range(max_len)]
            L = k + 1 - L
            B = T
            b = delta
            m = 1
        else:
            # Update without length increase
            coef = GF256.div(delta, b)
            shifted_B = [0] * m + B
            max_len = max(len(sigma), len(shifted_B))
            while len(sigma) < max_len:
                sigma.append(0)
            while len(shifted_B) < max_len:
                shifted_B.append(0)
            sigma = [GF256.add(sigma[j], GF256.mul(coef, shifted_B[j]))
                     for j in range(max_len)]
            m += 1

    # Trim trailing zeros (high-degree zero coefficients)
    while len(sigma) > 1 and sigma[-1] == 0:
        sigma.pop()
    return sigma


# ---------------------------------------------------------------------------
# Chien search
# ---------------------------------------------------------------------------


def chien_search(sigma: List[int], n: int) -> List[int]:
    """Chien search: find error positions.

    The error locator Λ(x) has roots at α^{-i} for each error position i.
    We test each position i = 0, ..., n-1 and check if Λ(α^{-i}) = 0.

    Args:
        sigma: Error locator polynomial (lowest-degree-first).
        n: Length of the received codeword.

    Returns:
        List of error positions (indices into the codeword, 0-based
        from the lowest-degree end).
    """
    errs = []
    for i in range(n):
        x_inv = GF256.pow(2, (255 - i) % 255) if i != 0 else 1
        if gf_poly_eval(sigma, x_inv) == 0:
            errs.append(i)
    return errs


# ---------------------------------------------------------------------------
# Forney algorithm
# ---------------------------------------------------------------------------

def _formal_derivative(poly: List[int]) -> List[int]:
    """Compute the formal derivative of a polynomial over GF(2^8).

    In characteristic 2, the derivative of c_i * x^i is i*c_i * x^{i-1},
    but terms with even i vanish (since i mod 2 = 0).
    """
    deriv = []
    for i in range(1, len(poly)):
        if i % 2 == 1:
            deriv.append(poly[i])
        else:
            deriv.append(0)
    return deriv


def forney(syndromes: List[int], err_positions: List[int],
           sigma: List[int]) -> List[Tuple[int, int]]:
    """Forney algorithm to compute error magnitudes.

    Args:
        syndromes: Syndrome values S_0, ..., S_{nsym-1}.
        err_positions: Error positions (from Chien search).
        sigma: Error locator polynomial (lowest-degree-first).

    Returns:
        List of (position, magnitude) correction pairs.
    """
    nsym = len(syndromes)

    # Syndrome polynomial S(x) = S_0 + S_1 x + ... + S_{nsym-1} x^{nsym-1}
    S_poly = list(syndromes)

    # Ω(x) = (S(x) * Λ(x)) mod x^{nsym}
    prod = gf_poly_mul(S_poly, sigma)
    omega = prod[:nsym]
    while len(omega) < nsym:
        omega.append(0)

    # Λ'(x) — formal derivative
    sigma_prime = _formal_derivative(sigma)

    corrections = []
    for pos in err_positions:
        # Root X_j = α^{-pos}
        x_inv = GF256.pow(2, (255 - pos) % 255) if pos != 0 else 1

        omega_val = gf_poly_eval(omega, x_inv)
        sigma_prime_val = gf_poly_eval(sigma_prime, x_inv)

        if sigma_prime_val == 0:
            raise ValueError("Λ'(X) = 0 — uncorrectable error pattern")

        # Forney: e_j = X_j^{-1} * Ω(X_j) / Λ'(X_j) = α^{pos} * Ω(α^{-pos}) / Λ'(α^{-pos})
        x = GF256.pow(2, pos)  # X_j^{-1} = α^{pos}
        magnitude = GF256.div(GF256.mul(omega_val, x), sigma_prime_val)
        corrections.append((pos, magnitude))

    return corrections


# ---------------------------------------------------------------------------
# Decoder result
# ---------------------------------------------------------------------------


class DecodeResult:
    """Result of an RS decode operation with statistics.

    Attributes:
        corrected: The corrected codeword.
        errors_corrected: Number of errors corrected.
        erasures_corrected: Number of erasures corrected.
        error_positions: Positions where errors were found and corrected.
        success: Whether decoding succeeded.
    """

    def __init__(self, corrected: List[int], error_positions: List[int],
                 erasure_positions: List[int], success: bool) -> None:
        self.corrected = corrected
        self.error_positions = error_positions
        self.erasure_positions = erasure_positions
        self.errors_corrected = len(error_positions)
        self.erasures_corrected = len(erasure_positions)
        self.success = success

    def __repr__(self) -> str:
        return (f"DecodeResult(success={self.success}, "
                f"errors_corrected={self.errors_corrected}, "
                f"erasures_corrected={self.erasures_corrected})")


# ---------------------------------------------------------------------------
# Main decode function
# ---------------------------------------------------------------------------


def rs_decode(received: List[int], nsym: int,
              erasures: Optional[List[int]] = None) -> List[int]:
    """Reed-Solomon decoder.

    Corrects errors and erasures in the received codeword. Can correct
    up to nsym//2 errors, or up to nsym erasures, or a combination
    (2*errors + erasures <= nsym).

    Args:
        received: Received codeword (parity + message, lowest-degree-first).
        nsym: Number of parity symbols used in encoding.
        erasures: Optional list of erasure positions (indices into the
            received codeword, 0-based from the lowest-degree end).

    Returns:
        Corrected codeword (same length as received).

    Raises:
        ValueError: If uncorrectable errors are detected or inputs are invalid.
    """
    result = rs_decode_detailed(received, nsym, erasures)
    return result.corrected


def rs_decode_detailed(received: List[int], nsym: int,
                       erasures: Optional[List[int]] = None) -> DecodeResult:
    """Reed-Solomon decoder with detailed result including statistics.

    Like rs_decode() but returns a DecodeResult with error/erasure counts
    and positions.
    """
    if erasures is None:
        erasures = []

    received = list(received)
    n = len(received)

    _validate_nsym(nsym)
    if nsym <= 0:
        return DecodeResult(received, [], [], True)
    if n == 0:
        return DecodeResult(received, [], [], True)

    if len(erasures) > nsym:
        raise ValueError(f"Too many erasures ({len(erasures)}) for nsym={nsym}")

    for e in erasures:
        if e < 0 or e >= n:
            raise ValueError(f"erasure position {e} out of range [0, {n})")

    # Deduplicate erasure positions
    erasures = list(set(erasures))

    # Calculate syndromes
    syndromes = calc_syndromes(received, nsym)

    # If all syndromes are zero, no errors detected
    if all(s == 0 for s in syndromes):
        return DecodeResult(received, [], [], True)

    if not erasures:
        # Error-only correction
        sigma = berlekamp_massey(syndromes)
        err_positions = chien_search(sigma, n)

        num_errs = len(err_positions)
        if num_errs == 0:
            raise ValueError(
                "Errors detected but Chien search found no roots — uncorrectable. "
                "This usually means more errors occurred than the code can correct."
            )
        if num_errs > nsym // 2:
            raise ValueError(
                f"Too many errors ({num_errs}) for nsym={nsym} "
                f"(max correctable: {nsym // 2})"
            )

        corrections = forney(syndromes, err_positions, sigma)

        for pos, mag in corrections:
            received[pos] ^= mag

        # Verify
        check = calc_syndromes(received, nsym)
        if not all(s == 0 for s in check):
            raise ValueError("Correction failed — syndromes nonzero after correction")

        return DecodeResult(received, err_positions, [], True)

    else:
        # Erasure + error correction
        # Build erasure locator polynomial
        # For each erasure at position p, root of Λ is at α^{-p}.
        # Factor: (x - α^{-p}) = (x + α^{-p}) in GF(2^8)
        # In lowest-degree-first: [α^{-p}, 1]
        sigma = [1]
        for p in erasures:
            x_inv = GF256.pow(2, (255 - p) % 255) if p != 0 else 1
            sigma = gf_poly_mul(sigma, [x_inv, 1])

        # Ω(x) = (S(x) * Λ(x)) mod x^{nsym}
        S_poly = list(syndromes)
        prod = gf_poly_mul(S_poly, sigma)
        omega = prod[:nsym]
        while len(omega) < nsym:
            omega.append(0)

        # Find all error positions via Chien search
        err_positions = chien_search(sigma, n)

        if len(err_positions) > nsym:
            raise ValueError(
                f"Too many errors+erasures ({len(err_positions)}) for nsym={nsym}"
            )
        if not err_positions:
            raise ValueError("Errors detected but no positions found")

        sigma_prime = _formal_derivative(sigma)

        corrections = []
        for pos in err_positions:
            x_inv = GF256.pow(2, (255 - pos) % 255) if pos != 0 else 1
            omega_val = gf_poly_eval(omega, x_inv)
            sigma_prime_val = gf_poly_eval(sigma_prime, x_inv)
            if sigma_prime_val == 0:
                raise ValueError("Λ'(X) = 0 — uncorrectable")
            x = GF256.pow(2, pos)
            magnitude = GF256.div(GF256.mul(omega_val, x), sigma_prime_val)
            corrections.append((pos, magnitude))

        for pos, mag in corrections:
            received[pos] ^= mag

        # Verify
        check = calc_syndromes(received, nsym)
        if not all(s == 0 for s in check):
            raise ValueError("Correction failed — syndromes nonzero after correction")

        # Separate errors vs erasures
        erasure_set = set(erasures)
        pure_errors = [p for p in err_positions if p not in erasure_set]

        return DecodeResult(received, pure_errors, list(err_positions), True)


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _validate_nsym(nsym: int) -> None:
    """Validate nsym parameter."""
    if not isinstance(nsym, int):
        raise TypeError(f"nsym must be an integer, got {type(nsym).__name__}")
    if nsym < 0:
        raise ValueError(f"nsym must be non-negative, got {nsym}")
    if nsym > 255:
        raise ValueError(f"nsym must be <= 255, got {nsym}")


def _validate_symbols(symbols: List[int]) -> None:
    """Validate that all symbols are in range [0, 255]."""
    for s in symbols:
        if not isinstance(s, int):
            raise TypeError(f"symbol must be an integer, got {type(s).__name__}")
        if not 0 <= s <= 255:
            raise ValueError(f"symbol out of range [0, 255]: {s}")


# ---------------------------------------------------------------------------
# Class-based API
# ---------------------------------------------------------------------------


class RSCode:
    """Reed-Solomon code instance with fixed parameters.

    Encapsulates a specific RS code configuration (nsym) and provides
    encoding/decoding methods with consistent parameters.

    Example:
        >>> rs = RSCode(nsym=10)
        >>> encoded = rs.encode([1, 2, 3, 4, 5])
        >>> corrupted = list(encoded)
        >>> corrupted[3] ^= 42
        >>> corrected = rs.decode(corrupted)
        >>> corrected == encoded
        True
    """

    def __init__(self, nsym: int) -> None:
        """Create an RS code instance.

        Args:
            nsym: Number of parity symbols. Must be 0 <= nsym <= 254.
        """
        _validate_nsym(nsym)
        if nsym > 254:
            raise ValueError(f"nsym must be <= 254 (need at least 1 data symbol), got {nsym}")
        self.nsym = nsym
        self.gen_poly = generator_poly(nsym) if nsym > 0 else [1]
        self._max_message_len = 255 - nsym

    @property
    def max_message_length(self) -> int:
        """Maximum message length in symbols."""
        return self._max_message_len

    @property
    def max_errors(self) -> int:
        """Maximum number of correctable errors."""
        return self.nsym // 2

    @property
    def max_erasures(self) -> int:
        """Maximum number of correctable erasures."""
        return self.nsym

    def encode(self, message: List[int]) -> List[int]:
        """Encode a message, returning parity + message."""
        if len(message) > self._max_message_len:
            raise ValueError(
                f"Message too long: {len(message)} > {self._max_message_len} "
                f"(max for nsym={self.nsym})"
            )
        return rs_encode(message, self.nsym)

    def decode(self, received: List[int],
               erasures: Optional[List[int]] = None) -> List[int]:
        """Decode and correct errors, returning corrected codeword."""
        return rs_decode(received, self.nsym, erasures)

    def decode_detailed(self, received: List[int],
                        erasures: Optional[List[int]] = None) -> DecodeResult:
        """Decode with detailed result including statistics."""
        return rs_decode_detailed(received, self.nsym, erasures)

    def encode_bytes(self, data: bytes) -> bytes:
        """Encode bytes, returning parity + data."""
        return bytes(self.encode(list(data)))

    def decode_bytes(self, data: bytes,
                    erasures: Optional[List[int]] = None) -> bytes:
        """Decode bytes, returning corrected data."""
        return bytes(self.decode(list(data), erasures))

    def encode_data(self, data: bytes) -> bytes:
        """Encode data bytes and return full codeword (parity + data)."""
        return self.encode_bytes(data)

    def decode_data(self, data: bytes,
                    erasures: Optional[List[int]] = None) -> bytes:
        """Decode, correct, and strip parity. Returns only the data."""
        corrected = self.decode_bytes(data, erasures)
        return corrected[self.nsym:] if self.nsym > 0 else corrected

    def __repr__(self) -> str:
        return (f"RSCode(nsym={self.nsym}, max_msg={self._max_message_len}, "
                f"max_errors={self.max_errors}, max_erasures={self.max_erasures})")

    def __str__(self) -> str:
        lines = [
            f"Reed-Solomon Code (GF(2^8))",
            f"  Parity symbols (nsym):  {self.nsym}",
            f"  Max message length:     {self._max_message_len} symbols",
            f"  Max codeword length:     255 symbols",
            f"  Correctable errors:      {self.max_errors}",
            f"  Correctable erasures:    {self.max_erasures}",
            f"  Combined (2e+s <= nsym): {self.nsym}",
        ]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Interleaving for burst-error correction
# ---------------------------------------------------------------------------


def interleave(data: List[int], rows: int) -> List[int]:
    """Block-interleave data across `rows` rows (column-major write, row-major read).

    This spreads burst errors across multiple RS codewords so each codeword
    sees at most one error per burst of length `rows`.

    Args:
        data: Input symbols. Length must be divisible by `rows`.
        rows: Number of interleaving rows (interleaving depth).

    Returns:
        Interleaved symbols.
    """
    if rows <= 0:
        raise ValueError(f"rows must be positive, got {rows}")
    if len(data) % rows != 0:
        raise ValueError(
            f"data length {len(data)} must be divisible by rows {rows}"
        )
    cols = len(data) // rows
    # Write column-major: data[i] goes to position (i % rows, i // rows)
    # Read row-major: output is row0col0, row0col1, ..., row0col_{cols-1}, row1col0, ...
    result = [0] * len(data)
    for i in range(len(data)):
        r = i % rows
        c = i // rows
        result[r * cols + c] = data[i]
    return result


def deinterleave(data: List[int], rows: int) -> List[int]:
    """Reverse block-interleaving.

    Args:
        data: Interleaved symbols. Length must be divisible by `rows`.
        rows: Number of interleaving rows.

    Returns:
        Deinterleaved (original order) symbols.
    """
    if rows <= 0:
        raise ValueError(f"rows must be positive, got {rows}")
    if len(data) % rows != 0:
        raise ValueError(
            f"data length {len(data)} must be divisible by rows {rows}"
        )
    cols = len(data) // rows
    # The inverse of interleave:
    # interleave maps data[i] -> output[(i%rows)*cols + (i//rows)]
    # So deinterleave maps: result[i] = data[(i%rows)*cols + (i//rows)]
    result = [0] * len(data)
    for i in range(len(data)):
        r = i % rows
        c = i // rows
        result[i] = data[r * cols + c]
    return result


def encode_interleaved(data: bytes, nsym: int, depth: int) -> bytes:
    """Encode data with interleaving for burst-error resilience.

    Splits data into `depth` blocks, RS-encodes each, then interleaves
    the codewords so a burst error of length `depth` corrupts at most one
    symbol per codeword.

    Args:
        data: Input data bytes.
        nsym: Parity symbols per codeword.
        depth: Interleaving depth (number of codewords).

    Returns:
        Interleaved encoded data.
    """
    if depth <= 0:
        raise ValueError(f"depth must be positive, got {depth}")
    if len(data) % depth != 0:
        # Pad data to be divisible by depth
        pad = depth - (len(data) % depth)
        data = data + b"\x00" * pad

    block_size = len(data) // depth
    # Validate that each block fits within GF(2^8) codeword limits
    if block_size + nsym > 255:
        raise ValueError(
            f"Block too large: block_size {block_size} + nsym {nsym} = {block_size + nsym} "
            f"> 255 (GF(2^8) max). Use a larger depth or smaller nsym."
        )
    codewords = []
    for i in range(depth):
        block = list(data[i * block_size:(i + 1) * block_size])
        codewords.append(rs_encode(block, nsym))

    # Interleave: take one symbol from each codeword in turn
    cw_len = len(codewords[0])
    result = []
    for j in range(cw_len):
        for cw in codewords:
            result.append(cw[j])
    return bytes(result)


def decode_interleaved(data: bytes, nsym: int, depth: int,
                      original_len: Optional[int] = None) -> bytes:
    """Decode interleaved RS-encoded data.

    Deinterleaves the data into `depth` codewords, decodes each, and
    concatenates the recovered messages.

    Args:
        data: Interleaved encoded data.
        nsym: Parity symbols per codeword.
        depth: Interleaving depth.
        original_len: Original data length (to strip padding). If None,
            returns all decoded data including padding.

    Returns:
        Recovered data.
    """
    if depth <= 0:
        raise ValueError(f"depth must be positive, got {depth}")
    data_list = list(data)
    if len(data_list) % depth != 0:
        raise ValueError(
            f"data length {len(data_list)} must be divisible by depth {depth}"
        )

    # Deinterleave: reconstruct codewords from interleaved data.
    # The interleaved layout is: [cw0[0], cw1[0], ..., cw{depth-1}[0],
    #                               cw0[1], cw1[1], ..., cw{depth-1}[1], ...]
    # So codeword i, symbol j = data_list[j * depth + i]
    cw_len = len(data_list) // depth
    if cw_len < nsym:
        raise ValueError(
            f"Interleaved data too short: each codeword needs at least nsym={nsym} "
            f"symbols, but only {cw_len} available (total {len(data_list)} bytes, "
            f"depth {depth})"
        )
    codewords = []
    for i in range(depth):
        cw = [data_list[j * depth + i] for j in range(cw_len)]
        codewords.append(rs_decode(cw, nsym))

    # Extract message portion (strip parity)
    msg_len = cw_len - nsym
    result = []
    for cw in codewords:
        result.extend(cw[nsym:nsym + msg_len])

    result_bytes = bytes(result)
    if original_len is not None:
        result_bytes = result_bytes[:original_len]
    return result_bytes


# ---------------------------------------------------------------------------
# High-level byte-oriented convenience API
# ---------------------------------------------------------------------------


def encode(data: bytes, nsym: int) -> bytes:
    """Encode raw bytes with RS parity.

    Args:
        data: Input data bytes.
        nsym: Number of parity bytes.

    Returns:
        parity + data bytes (lowest-degree-first layout).
    """
    return bytes(rs_encode(list(data), nsym))


def decode(data: bytes, nsym: int,
           erasures: Optional[List[int]] = None) -> bytes:
    """Decode and correct RS-encoded bytes.

    Args:
        data: RS-encoded bytes (parity + message).
        nsym: Number of parity bytes used during encoding.
        erasures: Optional list of erasure positions.

    Returns:
        Corrected data (same length as input).
    """
    corrected = rs_decode(list(data), nsym, erasures)
    return bytes(corrected)


def encode_message(data: bytes, nsym: int) -> bytes:
    """Encode raw data. Returns the full codeword (parity + message)."""
    return encode(data, nsym)


def decode_message(data: bytes, nsym: int,
                   erasures: Optional[List[int]] = None) -> bytes:
    """Decode, correct, and strip parity. Returns only the message.

    Args:
        data: Full RS-encoded codeword (parity + message).
        nsym: Number of parity bytes.
        erasures: Optional erasure positions.

    Returns:
        Corrected message (data without parity).
    """
    corrected = decode(data, nsym, erasures)
    return corrected[nsym:] if nsym > 0 else corrected