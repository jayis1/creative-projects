"""Reed-Solomon encoder/decoder for GF(2^8).

Implements systematic Reed-Solomon encoding, syndrome calculation,
Berlekamp-Massey algorithm for finding the error locator polynomial,
Chien search for finding error positions, and Forney algorithm for error
magnitudes. Supports both error correction and erasure correction.

Polynomial convention: coefficients are stored LOWEST degree first.
  poly[0] = constant term, poly[1] = x^1 coefficient, etc.

Symbol size is 8 bits (GF(2^8)). The code is parameterised by nsym (number
of parity symbols). Codeword length n = k + nsym <= 255.
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


def generator_poly(nsym: int) -> List[int]:
    """Generate the Reed-Solomon generator polynomial.

    g(x) = (x - α^0)(x - α^1)...(x - α^{nsym-1})

    Returns coefficients lowest-degree-first: g[0] is the constant term.
    """
    g = [1]
    for i in range(nsym):
        # Multiply g by (x - α^i) = (x + α^i) in GF(2^8)
        # (x + α^i) in lowest-first: [α^i, 1]
        g = gf_poly_mul(g, [GF256.pow(2, i), 1])
    return g


# ---------------------------------------------------------------------------
# Encoding
# ---------------------------------------------------------------------------


def rs_encode(message: List[int], nsym: int) -> List[int]:
    """Systematic Reed-Solomon encoding.

    The message occupies the high-order coefficients and parity symbols
    are appended (low-order).

    Args:
        message: List of message symbols (each 0-255).
        nsym: Number of parity symbols to add.

    Returns:
        message + parity symbols (length = len(message) + nsym).
    """
    if nsym < 0:
        raise ValueError("nsym must be non-negative")
    if nsym == 0:
        return list(message)
    for s in message:
        if not 0 <= s <= 255:
            raise ValueError(f"message symbols must be 0-255, got {s}")

    gen = generator_poly(nsym)
    # We compute parity = (message * x^nsym) mod g(x)
    # In lowest-first, multiplying by x^nsym means appending nsym zeros
    msg_padded = [0] * nsym + list(message)  # message shifted up by nsym
    _, remainder = gf_poly_div(msg_padded, gen)
    # Parity goes in the low-order positions (before the message)
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
    # Use the standard BM formulation with lowest-degree-first polynomials.
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
            # sigma = sigma - (delta/b) * x^m * B
            coef = GF256.div(delta, b)
            # Shift B by m: prepend m zeros (lowest-degree-first → multiply by x^m)
            shifted_B = [0] * m + B
            # Ensure same length
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

    In the received polynomial (lowest-first), position i is the coefficient
    of x^i, corresponding to root α^{-i}.

    Args:
        sigma: Error locator polynomial (lowest-degree-first).
        n: Length of the received codeword.

    Returns:
        List of error positions (indices into the codeword, 0-based
        from the lowest-degree end).
    """
    errs = []
    for i in range(n):
        # Evaluate sigma at alpha^{-i}
        x_inv = GF256.pow(2, (255 - i) % 255) if i != 0 else 1
        if gf_poly_eval(sigma, x_inv) == 0:
            errs.append(i)
    return errs


# ---------------------------------------------------------------------------
# Forney algorithm
# ---------------------------------------------------------------------------


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
    # (already lowest-degree-first)
    S_poly = list(syndromes)

    # Compute Ω(x) = S(x) * Λ(x) mod x^{nsym}
    # The key identity: Ω(x) = (S(x) * Λ(x)) mod x^{nsym}
    prod = gf_poly_mul(S_poly, sigma)
    omega = prod[:nsym]
    while len(omega) < nsym:
        omega.append(0)

    # Compute Λ'(x) — formal derivative.
    # In GF(2^m), the derivative of c_i * x^i is i*c_i * x^{i-1}.
    # In characteristic 2, terms with even i vanish.
    # Λ'(x) = sum_{i odd} Λ_i * x^{i-1}
    sigma_prime = []
    for i in range(1, len(sigma)):
        if i % 2 == 1:
            sigma_prime.append(sigma[i])
        else:
            sigma_prime.append(0)

    corrections = []
    for pos in err_positions:
        # The root corresponding to position pos is X = α^{-pos}
        x_inv = GF256.pow(2, (255 - pos) % 255) if pos != 0 else 1

        # Evaluate Ω(X)
        omega_val = gf_poly_eval(omega, x_inv)

        # Evaluate Λ'(X)
        sigma_prime_val = gf_poly_eval(sigma_prime, x_inv)

        if sigma_prime_val == 0:
            raise ValueError("Λ'(X) = 0 — uncorrectable error pattern")

        # Forney's formula: e_j = X_j^{-1} * Ω(X_j) / Λ'(X_j)
        # where X_j = α^{-pos} is the root of Λ.
        # X_j^{-1} = α^{pos}, so:
        # e_j = α^{pos} * Ω(α^{-pos}) / Λ'(α^{-pos})
        x = GF256.pow(2, pos)  # X_j^{-1} = α^{pos}
        magnitude = GF256.div(GF256.mul(omega_val, x), sigma_prime_val)
        corrections.append((pos, magnitude))

    return corrections


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
        ValueError: If uncorrectable errors are detected.
    """
    if erasures is None:
        erasures = []

    received = list(received)
    n = len(received)

    if nsym <= 0:
        return received

    if len(erasures) > nsym:
        raise ValueError(f"Too many erasures ({len(erasures)}) for nsym={nsym}")

    for e in erasures:
        if e < 0 or e >= n:
            raise ValueError(f"erasure position {e} out of range [0, {n})")

    # Calculate syndromes
    syndromes = calc_syndromes(received, nsym)

    # If all syndromes are zero, no errors detected
    if all(s == 0 for s in syndromes):
        return received

    if not erasures:
        # Error-only correction
        sigma = berlekamp_massey(syndromes)

        # Find error positions
        err_positions = chien_search(sigma, n)

        num_errs = len(err_positions)
        if num_errs == 0:
            raise ValueError("Errors detected but Chien search found no roots — uncorrectable")
        if num_errs > nsym // 2:
            raise ValueError(
                f"Too many errors ({num_errs}) for nsym={nsym} "
                f"(max correctable: {nsym // 2})"
            )

        # Compute error magnitudes
        corrections = forney(syndromes, err_positions, sigma)

        # Apply corrections
        for pos, mag in corrections:
            received[pos] ^= mag

        # Verify
        check = calc_syndromes(received, nsym)
        if not all(s == 0 for s in check):
            raise ValueError("Correction failed — syndromes nonzero after correction")

        return received

    else:
        # Erasure + error correction
        # Build erasure locator polynomial
        # For each erasure at position p, the root of Λ is at α^{-p}.
        # Factor: (x - α^{-p}) = (x + α^{-p}) in GF(2^8)
        # In lowest-degree-first: [α^{-p}, 1]
        sigma = [1]
        for p in erasures:
            x_inv = GF256.pow(2, (255 - p) % 255) if p != 0 else 1
            sigma = gf_poly_mul(sigma, [x_inv, 1])

        # Compute syndrome polynomial
        S_poly = list(syndromes)

        # Compute Ω(x) = S(x) * Λ(x) mod x^{nsym}
        prod = gf_poly_mul(S_poly, sigma)
        omega = prod[:nsym]
        while len(omega) < nsym:
            omega.append(0)

        # Find all error positions via Chien search on sigma
        err_positions = chien_search(sigma, n)

        if len(err_positions) > nsym:
            raise ValueError(
                f"Too many errors+erasures ({len(err_positions)}) for nsym={nsym}"
            )

        if not err_positions:
            raise ValueError("Errors detected but no positions found")

        # Compute Λ'(x)
        sigma_prime = []
        for i in range(1, len(sigma)):
            if i % 2 == 1:
                sigma_prime.append(sigma[i])
            else:
                sigma_prime.append(0)

        corrections = []
        for pos in err_positions:
            x_inv = GF256.pow(2, (255 - pos) % 255) if pos != 0 else 1
            omega_val = gf_poly_eval(omega, x_inv)
            sigma_prime_val = gf_poly_eval(sigma_prime, x_inv)
            if sigma_prime_val == 0:
                raise ValueError("Λ'(X) = 0 — uncorrectable")
            x = GF256.pow(2, pos)  # X_j^{-1} = α^{pos}
            magnitude = GF256.div(GF256.mul(omega_val, x), sigma_prime_val)
            corrections.append((pos, magnitude))

        for pos, mag in corrections:
            received[pos] ^= mag

        # Verify
        check = calc_syndromes(received, nsym)
        if not all(s == 0 for s in check):
            raise ValueError("Correction failed — syndromes nonzero after correction")

        return received


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