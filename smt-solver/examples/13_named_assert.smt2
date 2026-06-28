; Named assertions for UNSAT core test
(declare-const x Real)
(assert (! (> x 0.0) :named pos))
(assert (! (< x 5.0) :named upper))
(assert (! (> x 10.0) :named conflict))
(check-sat)
; expected: unsat