\ Array operations demo
\ Demonstrates ARRAY, []!, []@, ARRAY-SIZE, ERASE, FILL, MOVE

\ Create an array of 10 elements
ARRAY DATA 10

\ Fill with values using a loop
: INIT 10 0 DO I 3 * I DATA []! LOOP ;
INIT

\ Print the array
: PRINT-ARR 10 0 DO I DATA []@ 5 .R LOOP CR ;
." Initial array: " PRINT-ARR

\ Get array size
." Array size: " DATA ARRAY-SIZE . CR

\ FILL: set first 5 elements to 99
DATA 5 99 FILL
." After FILL 99: " PRINT-ARR

\ ERASE: zero out all elements
DATA 10 ERASE
." After ERASE:   " PRINT-ARR

\ MOVE: copy from one array to another
ARRAY SRC 5
ARRAY DST 5
10 0 SRC []! 20 1 SRC []! 30 2 SRC []! 40 3 SRC []! 50 4 SRC []!
SRC DST 5 MOVE
: PRINT-MOVED 5 0 DO I DST []@ 5 .R LOOP CR ;
." Moved array:   " PRINT-MOVED