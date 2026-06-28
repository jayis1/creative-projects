; String operations test
(declare-const s String)
(assert (= (str.len s) 5))
(assert (str.prefixof "ab" s))
(check-sat)
; expected: sat