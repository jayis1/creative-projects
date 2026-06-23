; Fibonacci with tail-call optimization
(define (fib n)
  (let loop ((i 0) (a 0) (b 1))
    (if (= i n)
        a
        (loop (+ i 1) b (+ a b)))))

(display "fib(10) = ")
(display (fib 10))
(newline)

(display "fib(30) = ")
(display (fib 30))
(newline)

; Factorial
(define (factorial n)
  (if (= n 0) 1 (* n (factorial (- n 1)))))

(display "factorial(10) = ")
(display (factorial 10))
(newline)

; Y combinator
(define Y
  (lambda (f)
    ((lambda (x) (f (lambda (v) ((x x) v))))
     (lambda (x) (f (lambda (v) ((x x) v)))))))

(define fact-y
  (Y (lambda (fact)
       (lambda (n)
         (if (= n 0) 1 (* n (fact (- n 1))))))))

(display "Y-combinator fact(5) = ")
(display (fact-y 5))
(newline)

; Association list operations
(define db '((name . "Alice") (age . 30) (city . "Boston")))
(display "Name: ")
(display (cdr (assoc 'name db)))
(newline)

; Higher-order functions
(display "Squares: ")
(display (map (lambda (x) (* x x)) (list 1 2 3 4 5)))
(newline)

(display "Evens: ")
(display (filter (lambda (x) (= (modulo x 2) 0)) (list 1 2 3 4 5 6 7 8 9 10)))
(newline)

(display "Sum 1-100: ")
(display (fold-right + 0 (let loop ((i 100) (acc '())) (if (= i 0) acc (loop (- i 1) (cons i acc))))))
(newline)