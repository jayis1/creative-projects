\ Bubble sort using ARRAY support
\ Demonstrates arrays, loops, variables, and conditionals

ARRAY DATA 10

\ Initialize array with some values
42 0 DATA []!
17 1 DATA []!
99 2 DATA []!
5 3 DATA []!
73 4 DATA []!
28 5 DATA []!
56 6 DATA []!
3 7 DATA []!
81 8 DATA []!
34 9 DATA []!

VARIABLE TEMP

\ BUBBLE-PASS: one pass of bubble sort
: BUBBLE-PASS
    9 0 DO
        I DATA []@
        I 1+ DATA []@
        > IF
            I DATA []@ TEMP !
            I 1+ DATA []@ I DATA []!
            TEMP @ I 1+ DATA []!
        THEN
    LOOP ;

\ BUBBLE: full bubble sort (9 passes)
: BUBBLE
    9 0 DO
        BUBBLE-PASS
    LOOP ;

BUBBLE

\ Print sorted array
: PRINT-ARRAY
    10 0 DO
        I DATA []@ . CR
    LOOP ;

PRINT-ARRAY
\ Expected output: 3 5 17 28 34 42 56 73 81 99 (each on its own line)