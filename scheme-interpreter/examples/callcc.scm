; call/cc examples

; Early return from a computation
(define (find pred lst)
  (call/cc
    (lambda (k)
      (for-each
        (lambda (x)
          (if (pred x) (k x) #f))
        lst)
      #f)))

(display "First even: ")
(display (find even? '(1 3 5 6 7 8)))
(newline)

; Sum with escape
(define (sum-list lst)
  (call/cc
    (lambda (k)
      (let loop ((l lst) (acc 0))
        (cond
          ((null? l) acc)
          ((number? (car l)) (loop (cdr l) (+ acc (car l))))
          (else (k 'error)))))))

(display "Sum: ") (display (sum-list '(1 2 3 4 5))) (newline)
(display "Sum with bad: ") (display (sum-list '(1 2 "x" 4 5))) (newline)

; call/cc for product with early exit on zero
(define (product lst)
  (call/cc
    (lambda (k)
      (let loop ((l lst) (acc 1))
        (cond
          ((null? l) acc)
          ((= (car l) 0) (k 0))
          (else (loop (cdr l) (* acc (car l)))))))))

(display "Product: ") (display (product '(1 2 3 4 5))) (newline)
(display "Product with 0: ") (display (product '(1 2 0 4 5))) (newline)