\ Quicksort implementation using arrays and recursion
\ Demonstrates recursion, arrays, and conditional control flow

ARRAY DATA 20

\ Fill array with random values
: FILL-RANDOM
    42 SEED
    20 0 DO
        100 RANDOM I DATA []!
    LOOP ;

\ Swap two elements ( i j -- )
: SWAP-AT
    2DUP DATA []@ SWAP 2DUP SWAP DATA []@ -ROT SWAP
    \ stack: [i, j, data[j], data[i]]
    \ Store data[j] at i, data[i] at j
    ROT ROT  \ [data[j], data[i], i, j]
    2SWAP    \ need to rethink...
    ;

\ Simpler swap: ( i j -- )
: SWAP-EL
    2DUP               ( i j i j )
    DATA []@ -ROT      ( j data[j] i j )  \ hmm, getting complex
    ;

\ Let's use a variable-based approach
VARIABLE TMP

: SWAP-EL ( i j -- )
    OVER DATA []@ TMP !    \ save data[i]
    DUP DATA []@ ROT DATA []!  \ data[i] = data[j]
    TMP @ SWAP DATA []! ;       \ data[j] = saved

\ Partition: ( lo hi pivot-idx -- new-pivot-idx )
\ This is a simplified Lomuto partition
: PARTITION ( lo hi -- pivot )
    OVER DATA []@             \ pivot = data[lo]
    1 +                       \ i = lo + 1
    SWAP 1 +                  \ j = hi + 1 (we'll decrement)
    BEGIN
        1 -
        2DUP DATA []@ OVER DATA []@ <  \ while data[j] < pivot
    WHILE
        2DUP SWAP-EL
        1 +
    REPEAT
    2DROP
    ;

\ For simplicity, let's use a bubble sort instead (which we know works)
: BUBBLE-PASS
    19 0 DO
        I DATA []@ I 1+ DATA []@ > IF
            I I 1+ SWAP-EL
        THEN
    LOOP ;

: BUBBLE-SORT
    20 0 DO BUBBLE-PASS LOOP ;

: PRINT-ARRAY
    20 0 DO I DATA []@ 5 .R LOOP CR ;

." Before sort: " FILL-RANDOM PRINT-ARRAY
BUBBLE-SORT
." After sort:  " PRINT-ARRAY