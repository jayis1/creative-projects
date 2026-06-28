; Unsatisfiable LRA problem
(set-logic LRA)
(declare-const x Real)
(declare-const y Real)
(assert (> x 5.0))
(assert (< x 3.0))
(check-sat)