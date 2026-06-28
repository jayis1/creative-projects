; Theory combination: EUF + LRA
(declare-fun f (Real) Real)
(declare-const a Real)
(declare-const b Real)
(declare-const c Real)
(assert (= a b))
(assert (> a 5.0))
(assert (< b 10.0))
(assert (= (f a) c))
(assert (= (f b) c))
(check-sat)
(get-model)
; expected: sat