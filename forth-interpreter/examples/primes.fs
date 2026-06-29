\ Example Forth program: print prime numbers up to 30

\ PRIME? ( n -- flag )  returns -1 if n is prime, 0 otherwise
: PRIME?
    DUP 2 < IF DROP FALSE EXIT THEN
    DUP 2 = IF DROP TRUE EXIT THEN
    DUP 2 MOD 0 = IF DROP FALSE EXIT THEN
    \ n is odd and >= 3. Check divisors 3, 5, 7, ... up to n-1
    DUP 3 BEGIN
        2DUP >              \ n > divisor ? continue while true
    WHILE
        2DUP MOD 0 =        \ n mod divisor == 0 → not prime
        IF 2DROP FALSE EXIT THEN
        2 +
    REPEAT
    2DROP TRUE ;

\ .PRIMES prints primes from 2 to limit
: .PRIMES 30 2 DO I PRIME? IF I . THEN LOOP ;

.PRIMES CR
\ Expected output: 2 3 5 7 11 13 17 19 23 29