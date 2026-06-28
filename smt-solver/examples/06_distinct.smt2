; Distinct constraint test
(declare-const a Real)
(declare-const b Real)
(declare-const c Real)
(assert (distinct a b c))
(assert (> a 0.0))
(assert (> b 0.0))
(assert (> c 0.0))
(assert (< a 10.0))
(assert (< b 10.0))
(assert (< c 10.0))
(check-sat)
(get-model)
; expected: sat