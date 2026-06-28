; Push/pop incremental solving test
(declare-const x Real)
(assert (> x 0.0))
(push)
(assert (> x 100.0))
(check-sat)
; expected: sat
(pop)
(check-sat)
; expected: sat