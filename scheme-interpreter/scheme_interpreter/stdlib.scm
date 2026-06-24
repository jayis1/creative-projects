; Standard library for the Scheme interpreter.
; This file is loaded automatically on startup.
; Functions already defined as primitives are not redefined here.

;; ----- higher-order combinators -----

(define (compose f g)
  (lambda (x) (f (g x))))

(define (constantly x)
  (lambda () x))

(define (negate pred)
  (lambda (x) (not (pred x))))

(define (conjoin . preds)
  (lambda (x)
    (let loop ((ps preds))
      (cond
        ((null? ps) #t)
        ((not ((car ps) x)) #f)
        (else (loop (cdr ps)))))))

(define (disjoin . preds)
  (lambda (x)
    (let loop ((ps preds))
      (cond
        ((null? ps) #f)
        (((car ps) x) #t)
        (else (loop (cdr ps)))))))

;; ----- numerical utilities -----

(define (square x) (* x x))

(define (cube x) (* x x x))

(define (average a b) (/ (+ a b) 2))

(define (inc x) (+ x 1))

(define (dec x) (- x 1))

;; ----- string utilities -----

(define (string-prefix? s prefix)
  (let ((slen (string-length s))
        (plen (string-length prefix)))
    (and (>= slen plen)
         (string=? (substring s 0 plen) prefix))))

(define (string-suffix? s suffix)
  (let ((slen (string-length s))
        (sflen (string-length suffix)))
    (and (>= slen sflen)
         (string=? (substring s (- slen sflen) slen) suffix))))

(define (string-trim s)
  (let* ((len (string-length s))
         (start (let loop ((i 0))
                  (if (>= i len)
                      len
                      (if (char-whitespace? (string-ref s i))
                          (loop (+ i 1))
                          i))))
         (end (let loop ((i (- len 1)))
                (if (< i 0)
                    0
                    (if (char-whitespace? (string-ref s i))
                        (loop (- i 1))
                        (+ i 1))))))
    (if (>= start end)
        ""
        (substring s start end))))

(define (string-reverse s)
  (let loop ((i (- (string-length s) 1)) (acc '()))
    (if (< i 0)
        (list->string (reverse acc))
        (loop (- i 1) (cons (string-ref s i) acc)))))

;; ----- stream utilities (lazy sequences) -----

(define-syntax cons-stream
  (syntax-rules ()
    ((cons-stream a d)
     (cons a (delay d)))))

(define (stream-car s) (car s))

(define (stream-cdr s) (force (cdr s)))

(define (stream-null? s) (null? s))

(define (stream-ref s n)
  (if (= n 0)
      (stream-car s)
      (stream-ref (stream-cdr s) (- n 1))))

(define (stream-map proc s)
  (if (stream-null? s)
      '()
      (cons-stream (proc (stream-car s))
                   (stream-map proc (stream-cdr s)))))

(define (stream-filter pred s)
  (cond
    ((stream-null? s) '())
    ((pred (stream-car s))
     (cons-stream (stream-car s)
                  (stream-filter pred (stream-cdr s))))
    (else (stream-filter pred (stream-cdr s)))))

(define (stream-take s n)
  (if (or (stream-null? s) (= n 0))
      '()
      (cons (stream-car s)
            (stream-take (stream-cdr s) (- n 1)))))

(define (stream-for-each proc s)
  (if (stream-null? s)
      #f
      (begin (proc (stream-car s))
             (stream-for-each proc (stream-cdr s)))))

;; ----- infinite stream generators -----

(define (integers-from n)
  (cons-stream n (integers-from (+ n 1))))

;; ----- set operations -----

(define (set-member x set)
  (cond
    ((null? set) #f)
    ((equal? x (car set)) #t)
    (else (set-member x (cdr set)))))

(define (set-adjoin x set)
  (if (set-member x set)
      set
      (cons x set)))

(define (set-union s1 s2)
  (cond
    ((null? s1) s2)
    ((set-member (car s1) s2) (set-union (cdr s1) s2))
    (else (cons (car s1) (set-union (cdr s1) s2)))))

(define (set-intersection s1 s2)
  (cond
    ((null? s1) '())
    ((set-member (car s1) s2)
     (cons (car s1) (set-intersection (cdr s1) s2)))
    (else (set-intersection (cdr s1) s2))))

(define (set-difference s1 s2)
  (cond
    ((null? s1) '())
    ((set-member (car s1) s2)
     (set-difference (cdr s1) s2))
    (else (cons (car s1) (set-difference (cdr s1) s2)))))

;; ----- misc utilities -----

(define (list-of? pred)
  (lambda (lst)
    (let loop ((l lst))
      (cond
        ((null? l) #t)
        ((not (pred (car l))) #f)
        (else (loop (cdr l)))))))