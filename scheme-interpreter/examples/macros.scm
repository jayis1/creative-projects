; Macros: swap!, while, unless, my-if

; swap! macro
(define-syntax swap!
  (syntax-rules ()
    ((swap! a b)
     (let ((tmp a))
       (set! a b)
       (set! b tmp)))))

(define x 1)
(define y 2)
(swap! x y)
(display "After swap: x=") (display x) (display " y=") (display y) (newline)

; while loop macro
(define-syntax while
  (syntax-rules ()
    ((while test body ...)
     (let loop ()
       (if test
           (begin body ... (loop))
           #f)))))

(define i 0)
(while (< i 5)
  (display i) (display " ")
  (set! i (+ i 1)))
(newline)

; Variadic macro with ellipsis
(define-syntax my-list
  (syntax-rules ()
    ((my-list x ...) (list x ...))))

(display (my-list 1 2 3 4 5))
(newline)

; Recursive macro
(define-syntax my-when
  (syntax-rules ()
    ((my-when test body ...)
     (if test (begin body ...) #f))))

(my-when (> 3 2)
  (display "3 > 2 is true")
  (newline))

; Macro with literals
(define-syntax for
  (syntax-rules (in)
    ((for var in lst body ...)
     (for-each (lambda (var) body ...) lst))))

(for x in (list 1 2 3 4 5)
  (display (* x x))
  (display " "))
(newline)