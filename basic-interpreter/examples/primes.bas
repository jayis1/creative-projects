5 REM =============================================
10 REM Prime Number Sieve (Sieve of Eratosthenes)
15 REM =============================================
20 PRINT "Prime numbers up to 100:"
30 PRINT ""
40 DIM P(100)
50 FOR I = 2 TO 100
60   LET P(I) = 1
70 NEXT I
80 LET S = 0
90 FOR I = 2 TO 100
100   IF P(I) = 0 THEN GOTO 150
110   LET S = S + 1
120   PRINT I; " ";
130   FOR J = I * 2 TO 100 STEP I
140     LET P(J) = 0
145   NEXT J
150 NEXT I
160 PRINT ""
170 PRINT ""
180 PRINT "Total primes found: "; S