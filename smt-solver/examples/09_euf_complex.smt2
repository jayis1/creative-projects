; EUF with multiple functions
(declare-fun f (Real) Real)
(declare-fun g (Real) Real)
(declare-const a Real)
(declare-const b Real)
(assert (= a b))
(assert (= (f a) (g b)))
(assert (= (f (g a)) (g (f b))))
(check-sat)
; expected: sat