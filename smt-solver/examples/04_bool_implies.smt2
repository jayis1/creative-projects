; Boolean satisfiability test
; expected: unsat
(declare-const a Bool)
(declare-const b Bool)
(declare-const c Bool)
(assert (=> a b))
(assert (=> b c))
(assert (not (=> a c)))
(check-sat)
; expected: unsat