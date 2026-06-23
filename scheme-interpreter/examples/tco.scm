; Tail-call optimization demonstrations

; Tail-recursive sum (no stack overflow even for huge n)
(define (sum-to n)
  (let loop ((i 0) (acc 0))
    (if (= i n)
        acc
        (loop (+ i 1) (+ acc i)))))

(display "sum-to(1000000) = ")
(display (sum-to 1000000))
(newline)

; Mutual tail recursion (even?/odd? are tail-recursive)
(define (my-even? n)
  (if (= n 0) #t (my-odd? (- n 1))))

(define (my-odd? n)
  (if (= n 0) #f (my-even? (- n 1))))

(display "(my-even? 100000) = ")
(display (my-even? 100000))
(newline)

; Named let with deep recursion
(define (count-down n)
  (let loop ((i n) (acc '()))
    (if (= i 0)
        acc
        (loop (- i 1) (cons i acc)))))

(display "count-down(10) = ")
(display (count-down 10))
(newline)

; do loop with tail recursion
(define (do-sum n)
  (do ((i 0 (+ i 1))
       (s 0 (+ s i)))
      ((= i n) s)))

(display "do-sum(100) = ")
(display (do-sum 100))
(newline)