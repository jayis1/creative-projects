"""Quotient Filter placeholder.

The full Quotient Filter (Bender et al. 2012) with its 3-bit metadata scheme
is notoriously error-prone.  Rather than ship an incorrect implementation,
this module is intentionally empty — use ``BlockedBloomFilter`` for
cache-friendly membership testing, or ``CuckooFilter`` for membership with
deletion."""