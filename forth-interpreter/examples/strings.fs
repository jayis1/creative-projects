\ String operations demo
\ Demonstrates STRLEN, STRCAT, CMP-STR, SUBSTR, CHAR, [CHAR], ."

: GREET
    ." Hello, "        \ print greeting prefix
    ." World!"         \ print greeting suffix
    CR ;

GREET

\ String length
." Length of 'hello': " "hello" STRLEN . CR

\ String concatenation
"world" "hello " STRCAT ." Concatenated: " TYPE CR

\ String comparison
"foo" "foo" CMP-STR ." 'foo' == 'foo': " . CR
"foo" "bar" CMP-STR ." 'foo' == 'bar': " . CR

\ Substring: extract "llo" from "hello" (start=2, len=3)
2 3 "hello" SUBSTR ." Substr: " TYPE CR

\ CHAR — push ASCII value of next token's first char
CHAR A ." ASCII of A: " . CR

\ [CHAR] in compiled definitions
: PRINT-X [CHAR] X EMIT ;
." Compiled [CHAR]: " PRINT-X CR

\ .( — immediate string output (even in compile mode)
: TEST .( compiling...) ." inside word" CR ;
TEST