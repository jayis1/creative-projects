10 REM *** WHILE/WEND Demo: Collatz Sequence ***
20 PRINT "Collatz Conjecture - Starting from 27"
30 LET N = 27
40 LET S = 0
50 WHILE N <> 1
60   PRINT N;
70   LET S = S + 1
80   IF N / 2 <> INT(N / 2) THEN LET N = 3 * N + 1 : GOTO 100
90   LET N = N / 2
100 WEND
110 PRINT 1
120 PRINT "Steps: "; S