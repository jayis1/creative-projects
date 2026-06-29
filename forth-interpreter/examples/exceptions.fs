\ Exception handling demo
\ Demonstrates CATCH, THROW, ABORT

\ A word that always throws
: DANGER 42 THROW ;

\ CATCH executes the word; if it throws, pushes the code instead of propagating
." Catching a throw: " CATCH DANGER . CR

\ A word that does NOT throw
: SAFE 99 . ;
." Catching safe word: " CATCH SAFE . CR    \ prints 99 then 0 (no throw)

\ ABORT clears the stack and raises an error
: MAYBE-ABORT
    0> IF
        ." aborting!" CR ABORT
    ELSE
        ." ok" CR
    THEN ;

\ This will abort
\ -1 MAYBE-ABORT  \ uncomment to see abort behavior

\ This is fine
0 MAYBE-ABORT