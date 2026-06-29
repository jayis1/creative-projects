# Forth Interpreter — Word Reference

Complete list of all built-in words organized by category.

## Stack Manipulation

| Word | Stack Effect | Description |
|------|-------------|-------------|
| `DUP` | `( x -- x x )` | Duplicate top |
| `DROP` | `( x -- )` | Remove top |
| `?DUP` | `( x -- x x \| x )` | Dup if nonzero |
| `SWAP` | `( x y -- y x )` | Swap top two |
| `OVER` | `( x y -- x y x )` | Copy second to top |
| `ROT` | `( x y z -- y z x )` | Rotate top three |
| `-ROT` | `( x y z -- z x y )` | Rotate top three (reverse) |
| `NIP` | `( x y -- y )` | Remove second item |
| `TUCK` | `( x y -- y x y )` | Dup top, insert under second |
| `DEPTH` | `( -- n )` | Push stack depth |
| `PICK` | `( n -- item[n] )` | Copy nth stack item to top |
| `ROLL` | `( n -- )` | Rotate nth stack item to top |
| `2DUP` | `( x y -- x y x y )` | Duplicate top two |
| `2DROP` | `( x y -- )` | Remove top two |
| `2SWAP` | `( x y z w -- z w x y )` | Swap top two pairs |
| `2OVER` | `( x y z w -- x y z w x y )` | Copy third/fourth to top |
| `WITHIN` | `( n lo hi -- flag )` | True if lo ≤ n < hi |
| `BOUNDS` | `( addr len -- addr+len addr )` | Convert to address range |

## Return Stack

| Word | Stack Effect | Description |
|------|-------------|-------------|
| `>R` | `( x -- )` | Push to return stack |
| `R>` | `( -- x )` | Pop from return stack |
| `R@` | `( -- x )` | Copy return stack top |

## Arithmetic

| Word | Stack Effect | Description |
|------|-------------|-------------|
| `+` | `( a b -- a+b )` | Addition |
| `-` | `( a b -- a-b )` | Subtraction |
| `*` | `( a b -- a*b )` | Multiplication |
| `/` | `( a b -- q )` | Integer division (truncate toward zero) |
| `MOD` | `( a b -- r )` | Modulo (sign follows dividend) |
| `/MOD` | `( a b -- r q )` | Division with remainder |
| `NEGATE` | `( n -- -n )` | Negate |
| `ABS` | `( n -- |n| )` | Absolute value |
| `MIN` | `( a b -- min )` | Minimum |
| `MAX` | `( a b -- max )` | Maximum |
| `**` | `( base exp -- base^exp )` | Power |
| `1+` | `( n -- n+1 )` | Add 1 |
| `1-` | `( n -- n-1 )` | Subtract 1 |
| `2+` | `( n -- n+2 )` | Add 2 |
| `2-` | `( n -- n-2 )` | Subtract 2 |
| `2*` | `( n -- n*2 )` | Multiply by 2 |
| `2/` | `( n -- n/2 )` | Divide by 2 (shift right) |

## Floating Point

| Word | Stack Effect | Description |
|------|-------------|-------------|
| `F+` | `( a b -- a+b )` | Float add |
| `F-` | `( a b -- a-b )` | Float subtract |
| `F*` | `( a b -- a*b )` | Float multiply |
| `F/` | `( a b -- a/b )` | Float divide |
| `FSQRT` | `( f -- sqrt(f) )` | Float sqrt |
| `FSIN` | `( f -- sin(f) )` | Float sin |
| `FCOS` | `( f -- cos(f) )` | Float cos |
| `FTAN` | `( f -- tan(f) )` | Float tan |
| `FLOG` | `( f -- log(f) )` | Float natural log |
| `FEXP` | `( f -- exp(f) )` | Float exp |
| `FLOOR` | `( f -- floor(f) )` | Floor |
| `CEIL` | `( f -- ceil(f) )` | Ceiling |
| `ROUND` | `( f -- round(f) )` | Round |
| `FABS` | `( f -- |f| )` | Float absolute value |
| `FNEGATE` | `( f -- -f )` | Float negate |
| `FATAN` | `( f -- atan(f) )` | Float arctan |
| `FASIN` | `( f -- asin(f) )` | Float arcsin |
| `FACOS` | `( f -- acos(f) )` | Float arccos |
| `FATAN2` | `( y x -- atan2(y,x) )` | Float atan2 |
| `F**` | `( base exp -- base^exp )` | Float power |
| `PI` | `( -- pi )` | Push pi |
| `E` | `( -- e )` | Push Euler's number |

## Comparison

| Word | Stack Effect | Description |
|------|-------------|-------------|
| `=` | `( a b -- flag )` | Equal |
| `<>` | `( a b -- flag )` | Not equal |
| `<` | `( a b -- flag )` | Less than |
| `>` | `( a b -- flag )` | Greater than |
| `<=` | `( a b -- flag )` | Less or equal |
| `>=` | `( a b -- flag )` | Greater or equal |
| `0=` | `( n -- flag )` | Top == 0? |
| `0<>` | `( n -- flag )` | Top != 0? |
| `0<` | `( n -- flag )` | Top < 0? |
| `0>` | `( n -- flag )` | Top > 0? |

## Bitwise

| Word | Stack Effect | Description |
|------|-------------|-------------|
| `AND` | `( a b -- a&b )` | Bitwise AND |
| `OR` | `( a b -- a|b )` | Bitwise OR |
| `XOR` | `( a b -- a^b )` | Bitwise XOR |
| `INVERT` | `( n -- ~n )` | Bitwise NOT |
| `LSHIFT` | `( a b -- a<<b )` | Left shift |
| `RSHIFT` | `( a b -- a>>b )` | Right shift |
| `NOT` | `( n -- flag )` | Logical NOT |

## I/O

| Word | Stack Effect | Description |
|------|-------------|-------------|
| `.` | `( n -- )` | Print top + space |
| `.R` | `( n width -- )` | Print right-justified |
| `U.` | `( n -- )` | Print unsigned |
| `EMIT` | `( char -- )` | Print char |
| `CR` | `( -- )` | Newline |
| `SPACE` | `( -- )` | Space |
| `SPACES` | `( n -- )` | Print n spaces |
| `BL` | `( -- 32 )` | Blank char code |
| `.S` | `( -- )` | Show stack |
| `.S!` | `( -- )` | Show stack with types |
| `TYPE` | `( str -- )` | Print top as string |
| `DUMP` | `( -- )` | Hex dump of stack |

## Memory / Variables

| Word | Stack Effect | Description |
|------|-------------|-------------|
| `!` | `( val addr -- )` | Store to variable |
| `@` | `( addr -- val )` | Fetch from variable |
| `+!` | `( n addr -- )` | Add to variable |
| `SP@` | `( -- depth )` | Push stack depth |
| `CELLS` | `( -- )` | Cell size (no-op) |
| `CELL+` | `( n -- n+1 )` | Add 1 cell |
| `ERASE` | `( addr len -- )` | Zero array cells |
| `FILL` | `( addr len val -- )` | Fill array cells |
| `MOVE` | `( src dst len -- )` | Copy array cells |

## Defining Words

| Word | Stack Effect | Description |
|------|-------------|-------------|
| `:` `;` | `( -- )` | Start/end colon definition |
| `VARIABLE` | `( -- )` | Create a variable |
| `CONSTANT` | `( val -- )` | Create a constant |
| `VALUE` | `( val -- )` | Create a value |
| `TO` | `( val -- )` | Set a value |
| `CREATE` | `( -- )` | Create a named cell |
| `2VARIABLE` | `( -- )` | Create a 2-cell variable |

## Control Flow

| Word | Stack Effect | Description |
|------|-------------|-------------|
| `IF` | `( flag -- )` | Conditional (immediate) |
| `ELSE` | `( -- )` | Else branch (immediate) |
| `THEN` | `( -- )` | End if (immediate) |
| `BEGIN` | `( -- )` | Begin loop (immediate) |
| `UNTIL` | `( flag -- )` | Loop until true (immediate) |
| `WHILE` | `( flag -- )` | Loop while true (immediate) |
| `REPEAT` | `( -- )` | End while loop (immediate) |
| `AGAIN` | `( -- )` | Infinite loop (immediate) |
| `DO` | `( limit start -- )` | Do loop (immediate) |
| `LOOP` | `( -- )` | End do loop (immediate) |
| `+LOOP` | `( inc -- )` | End do loop with increment (immediate) |
| `LEAVE` | `( -- )` | Exit loop (immediate) |
| `EXIT` | `( -- )` | Return from word |
| `RECURSE` | `( -- )` | Recursive self-call (immediate) |
| `UNLOOP` | `( -- )` | Remove innermost loop state |
| `I` | `( -- index )` | Loop index |
| `J` | `( -- index )` | Outer loop index |

## Case

| Word | Stack Effect | Description |
|------|-------------|-------------|
| `CASE` | `( n -- )` | Start case statement (immediate) |
| `OF` | `( test -- )` | OF clause (immediate) |
| `ENDOF` | `( -- )` | End OF clause (immediate) |
| `ENDCASE` | `( -- )` | End case (immediate) |

## Arrays

| Word | Stack Effect | Description |
|------|-------------|-------------|
| `ARRAY` | `( size -- )` | Create array (defining word) |
| `[]!` | `( val idx addr -- )` | Array store |
| `[]@` | `( idx addr -- val )` | Array fetch |
| `ARRAY-SIZE` | `( addr -- size )` | Get array size |

## Strings

| Word | Stack Effect | Description |
|------|-------------|-------------|
| `."` | `( -- )` | Print string at runtime (immediate) |
| `.( ` | `( -- )` | Print string immediately (immediate) |
| `C"` | `( -- str )` | Compile counted string (immediate) |
| `STRLEN` | `( str -- len )` | String length |
| `STRCAT` | `( str2 str1 -- result )` | String concatenation |
| `CMP-STR` | `( str2 str1 -- flag )` | String compare |
| `SUBSTR` | `( start len str -- substr )` | Extract substring |
| `CHAR` | `( -- char )` | Push ASCII of next token's first char |
| `[CHAR]` | `( -- )` | Compile char literal (immediate) |
| `TYPE` | `( str -- )` | Print string |

## Exceptions

| Word | Stack Effect | Description |
|------|-------------|-------------|
| `THROW` | `( code -- )` | Throw exception |
| `CATCH` | `( -- code )` | Catch exception (defining word) |
| `ABORT` | `( -- )` | Abort, clear stack |
| `ABORT"` | `( flag "msg" -- )` | Abort if flag true (immediate) |

## Utility

| Word | Stack Effect | Description |
|------|-------------|-------------|
| `WORDS` | `( -- )` | List all words |
| `WORDS-COUNT` | `( -- n )` | Push number of words |
| `SEE` | `( -- )` | Decompile word |
| `FORGET` | `( -- )` | Remove word |
| `BYE` | `( -- )` | Exit |
| `TRUE` | `( -- -1 )` | Push true |
| `FALSE` | `( -- 0 )` | Push false |
| `RESET` | `( -- )` | Clear all stacks |
| `VERSION` | `( -- )` | Print version |
| `TIME` | `( -- f )` | Push Unix epoch time |
| `CLOCK` | `( -- n )` | Push millisecond clock |
| `SEED` | `( n -- )` | Set random seed |
| `RANDOM` | `( n -- rand )` | Push random int [0, n) |

## File Operations

| Word | Stack Effect | Description |
|------|-------------|-------------|
| `INCLUDE` | `( "filename" -- )` | Load and evaluate a file (defining word) |