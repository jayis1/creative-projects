;;; stdlib.scm — Standard library for the Scheme interpreter.
;;; Auto-loaded on interpreter startup.
;;; Provides commonly used utility procedures, higher-order functions,
;;; stream operations, and set operations.

;; ---------------------------------------------------------------------------
;; Composition and higher-order utilities
;; ---------------------------------------------------------------------------

(define (compose . procs)
  "Return a procedure that is the composition of PROCS.
  (compose f g h) returns a function x -> f(g(h(x)))."
  (if (null? procs)
      (lambda (x) x)
      (let loop ((ps procs))
        (if (null? (cdr ps))
            (car ps)
            (let ((rest (loop (cdr ps))))
              (lambda (x) ((car ps) (rest x))))))))

(define (negate pred)
  "Return a procedure that negates the result of PRED."
  (lambda args (not (apply pred args))))

(define (conjoin . preds)
  "Return a predicate that is true when all PREDS are true."
  (lambda args
    (let loop ((ps preds))
      (cond
        ((null? ps) #t)
        ((apply (car ps) args) (loop (cdr ps)))
        (else #f)))))

(define (disjoin . preds)
  "Return a predicate that is true when any PREDS is true."
  (lambda args
    (let loop ((ps preds))
      (cond
        ((null? ps) #f)
        ((apply (car ps) args) #t)
        (else (loop (cdr ps)))))))

;; ---------------------------------------------------------------------------
;; Numeric utilities
;; ---------------------------------------------------------------------------

(define (square x) (* x x))
(define (cube x) (* x x x))
(define (average . args) (/ (apply + args) (length args)))
(define (inc x) (+ x 1))
(define (dec x) (- x 1))

;; ---------------------------------------------------------------------------
;; String utilities
;; ---------------------------------------------------------------------------

(define (string-prefix? prefix str)
  "Check if STR starts with PREFIX."
  (and (>= (string-length str) (string-length prefix))
       (string=? (substring str 0 (string-length prefix)) prefix)))

(define (string-suffix? suffix str)
  "Check if STR ends with SUFFIX."
  (let ((slen (string-length str))
        (flen (string-length suffix)))
    (and (>= slen flen)
         (string=? (substring str (- slen flen) slen) suffix))))

(define (string-trim str)
  "Remove leading and trailing whitespace from STR."
  (let loop-forward ((i 0))
    (if (and (< i (string-length str))
             (char-whitespace? (string-ref str i)))
        (loop-forward (+ i 1))
        (let loop-backward ((j (string-length str)))
          (if (and (> j i)
                   (char-whitespace? (string-ref str (- j 1))))
              (loop-backward (- j 1))
              (substring str i j))))))

(define (string-reverse str)
  "Reverse the characters in STR."
  (list->string (reverse (string->list str))))

;; Stream utilities (lazy sequences via delay/force)
;; cons-stream is defined via syntax-rules macro

(define-syntax cons-stream
  (syntax-rules ()
    ((cons-stream a b)
     (cons a (delay b)))))

(define (stream-car s) (car s))
(define (stream-cdr s) (force (cdr s)))

(define (stream-map proc s)
  (if (null? s)
      '()
      (cons-stream (proc (stream-car s))
                   (stream-map proc (stream-cdr s)))))

(define (stream-filter pred s)
  (if (null? s)
      '()
      (let ((head (stream-car s)))
        (if (pred head)
            (cons-stream head (stream-filter pred (stream-cdr s)))
            (stream-filter pred (stream-cdr s))))))

(define (stream-take s n)
  (if (or (null? s) (= n 0))
      '()
      (cons (stream-car s) (stream-take (stream-cdr s) (- n 1)))))

(define (stream-for-each proc s)
  (if (null? s)
      #f
      (begin
        (proc (stream-car s))
        (stream-for-each proc (stream-cdr s)))))

(define (stream-ref s n)
  (if (= n 0)
      (stream-car s)
      (stream-ref (stream-cdr s) (- n 1))))

;; ---------------------------------------------------------------------------
;; Set operations on lists
;; ---------------------------------------------------------------------------

(define (set-member x lst)
  "Check if X is in LST (using equal?)."
  (cond
    ((null? lst) #f)
    ((equal? x (car lst)) #t)
    (else (set-member x (cdr lst)))))

(define (set-adjoin x lst)
  "Add X to LST if not already present."
  (if (set-member x lst)
      lst
      (cons x lst)))

(define (set-union lst1 lst2)
  "Return the union of two sets (as lists)."
  (cond
    ((null? lst1) lst2)
    (else (set-adjoin (car lst1) (set-union (cdr lst1) lst2)))))

(define (set-intersection lst1 lst2)
  "Return the intersection of two sets (as lists)."
  (cond
    ((null? lst1) '())
    ((set-member (car lst1) lst2)
     (cons (car lst1) (set-intersection (cdr lst1) lst2)))
    (else (set-intersection (cdr lst1) lst2))))

(define (set-difference lst1 lst2)
  "Return elements in LST1 that are not in LST2."
  (cond
    ((null? lst1) '())
    ((set-member (car lst1) lst2)
     (set-difference (cdr lst1) lst2))
    (else (cons (car lst1) (set-difference (cdr lst1) lst2)))))

;; ---------------------------------------------------------------------------
;; List utilities
;; ---------------------------------------------------------------------------

(define (list-of? pred)
  "Return a predicate that checks if a value is a list of elements all satisfying PRED."
  (lambda (lst)
    (let loop ((l lst))
      (cond
        ((null? l) #t)
        ((and (pair? l) (pred (car l))) (loop (cdr l)))
        (else #f)))))

(define (iota count . start-step)
  "Return a list of COUNT integers starting from START (default 0) with step STEP (default 1)."
  (let ((start (if (null? start-step) 0 (car start-step)))
        (step (if (or (null? start-step) (null? (cdr start-step))) 1 (cadr start-step))))
    (let loop ((i 0) (acc '()))
      (if (>= i count)
          (reverse acc)
          (loop (+ i 1) (cons (+ start (* i step)) acc))))))

(define (list-tabulate n proc)
  "Return a list of N elements, each produced by (PROC i)."
  (let loop ((i (- n 1)) (acc '()))
    (if (< i 0)
        acc
        (loop (- i 1) (cons (proc i) acc)))))

(define (any pred lst)
  "Return #t if any element of LST satisfies PRED, #f otherwise."
  (cond
    ((null? lst) #f)
    ((pred (car lst)) #t)
    (else (any pred (cdr lst)))))

(define (every pred lst)
  "Return #t if every element of LST satisfies PRED, #f otherwise."
  (cond
    ((null? lst) #t)
    ((not (pred (car lst))) #f)
    (else (every pred (cdr lst)))))

;; ---------------------------------------------------------------------------
;; Association list utilities
;; ---------------------------------------------------------------------------

(define (alist-cons key datum alist)
  "Add (KEY . DATUM) to the front of ALIST."
  (cons (cons key datum) alist))

(define (alist-copy alist)
  "Make a fresh copy of ALIST."
  (map (lambda (pair) (cons (car pair) (cdr pair))) alist))

(define (alist-delete key alist)
  "Remove all entries with KEY from ALIST."
  (filter (lambda (pair) (not (equal? (car pair) key))) alist))