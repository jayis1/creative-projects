;;; streams.scm — Stream (lazy sequence) examples using the standard library.

;; ---------------------------------------------------------------------------
;; Infinite streams
;; ---------------------------------------------------------------------------

(define (integers-from n)
  "An infinite stream of integers starting from N."
  (cons-stream n (integers-from (+ n 1))))

(define naturals (integers-from 1))

(display "First 10 naturals: ")
(display (stream-take naturals 10))
(newline)

;; ---------------------------------------------------------------------------
;; Sieve of Eratosthenes using streams
;; ---------------------------------------------------------------------------

(define (sieve s)
  (cons-stream (stream-car s)
               (sieve (stream-filter
                        (lambda (x) (not (= (modulo x (stream-car s)) 0)))
                        (stream-cdr s)))))

(define primes (sieve (integers-from 2)))

(display "First 20 primes: ")
(display (stream-take primes 20))
(newline)

;; ---------------------------------------------------------------------------
;; Newton's method for square root using streams
;; ---------------------------------------------------------------------------

(define (sqrt-stream x)
  "Compute sqrt(x) via Newton's method as a stream of improving guesses."
  (define (improve guess)
    (/ (+ guess (/ x guess)) 2))
  (cons-stream 1.0 (stream-map improve (sqrt-stream x))))

(define sqrt2 (sqrt-stream 2))
(display "Newton's method sqrt(2) approximations: ")
(display (stream-take sqrt2 8))
(newline)

;; ---------------------------------------------------------------------------
;; Ackermann function (non-tail-recursive, tests deep recursion limits)
;; ---------------------------------------------------------------------------

(define (ackermann m n)
  (cond
    ((= m 0) (+ n 1))
    ((= n 0) (ackermann (- m 1) 1))
    (else (ackermann (- m 1) (ackermann m (- n 1))))))

(display "ackermann(2,3) = ")
(display (ackermann 2 3))
(newline)

(display "ackermann(3,3) = ")
(display (ackermann 3 3))
(newline)

;; ---------------------------------------------------------------------------
;; Using the standard library
;; ---------------------------------------------------------------------------

(display "Squares via compose: ")
(display (map (compose square inc) '(1 2 3 4 5)))
(newline)

(display "Evens via negate: ")
(display (filter (negate odd?) '(1 2 3 4 5 6 7 8 9 10)))
(newline)

(display "Set union: ")
(display (set-union '(1 2 3) '(3 4 5)))
(newline)

(display "Set intersection: ")
(display (set-intersection '(1 2 3 4 5) '(3 4 5 6 7)))
(newline)

(display "Iota: ")
(display (iota 10 1 2))
(newline)