; Multi-variable LRA with multiple constraints
(declare-const x Real)
(declare-const y Real)
(declare-const z Real)
(assert (>= (+ x y z) 10.0))
(assert (<= x 3.0))
(assert (<= y 4.0))
(assert (<= z 5.0))
(assert (>= x 0.0))
(assert (>= y 0.0))
(assert (>= z 0.0))
(check-sat)
(get-model)
; expected: sat