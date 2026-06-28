; XOR and Boolean equality test
(declare-const a Bool)
(declare-const b Bool)
(assert (xor a b))
(assert (= a (not b)))
(check-sat)
; expected: sat