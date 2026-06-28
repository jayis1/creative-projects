; ITE expansion test
(declare-const x Real)
(declare-const y Real)
(declare-const b Bool)
(assert (= y (ite b 1.0 2.0)))
(assert b)
(assert (> y 0.0))
(check-sat)
(get-model)
; expected: sat