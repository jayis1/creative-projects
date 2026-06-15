10 REM *** Fibonacci Sequence ***
20 PRINT "Fibonacci Sequence"
30 PRINT "=================="
40 LET A = 0
50 LET B = 1
60 FOR I = 1 TO 20
70 PRINT A;
80 LET C = A + B
90 LET A = B
100 LET B = C
110 NEXT I
120 PRINT
130 PRINT "Done!"