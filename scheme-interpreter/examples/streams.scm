; Streams: infinite sequence of natural numbers
(define (integers-from n)
  (cons-stream n (integers-from (+ n 1))))

(define naturals (integers-from 1))

; Sieve of Eratosthenes using streams
(define (sieve s)
  (cons-stream
    (stream-car s)
    (sieve (stream-filter
            (lambda (x) (not (= (modulo x (stream-car s)) 0)))
            (stream-cdr s)))))

(define primes (sieve (integers-from 2)))

; First 10 primes
(display "First 10 primes: ")
(display (stream-take primes 10))
(newline)

; Fibonacci using streams
(define fibs
  (cons-stream 0
    (cons-stream 1
      (stream-add fibs (stream-cdr fibs)))))

(define (stream-add s1 s2)
  (cons-stream (+ (stream-car s1) (stream-car s2))
              (stream-add (stream-cdr s1) (stream-cdr s2))))

; First 15 Fibonacci numbers
(display "First 15 Fibonacci: ")
(display (stream-take
          (cons-stream 0 (cons-stream 1 (stream-add fibs (stream-cdr fibs))))
          15))
(newline)

; Newton's method for square root
(define (sqrt-newton x)
  (define (good-enough? guess)
    (< (abs (- (* guess guess) x)) 0.0001))
  (define (improve guess)
    (/ (+ guess (/ x guess)) 2))
  (define (sqrt-iter guess)
    (if (good-enough? guess)
        guess
        (sqrt-iter (improve guess))))
  (sqrt-iter 1.0))

(display "sqrt(2) = ")
(display (sqrt-newton 2))
(newline)

(display "sqrt(100) = ")
(display (sqrt-newton 100))
(newline)

; Ackermann function (test deep non-tail recursion)
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