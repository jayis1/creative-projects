\ Fibonacci sequence using DO/LOOP and recursion
\ Also demonstrates .R for formatted output

: FIB
    DUP 2 < IF EXIT THEN
    DUP 1 - RECURSE SWAP 2 - RECURSE + ;

\ Print a table of Fibonacci numbers
: .FIB-TABLE
    ." n  fib(n)" CR
    ." -------" CR
    20 0 DO
        I 3 .R 2 SPACES
        I FIB 10 .R CR
    LOOP ;

.FIB-TABLE

\ Iterative Fibonacci (more efficient)
: FIB-ITER
    0 1 ROT 0 DO
        OVER + SWAP
    LOOP
    SWAP DROP ;

." Iterative fib(30): " 30 FIB-ITER . CR