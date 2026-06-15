10 REM =============================================
20 REM Numeric Diamond Pattern
30 REM =============================================
40 PRINT "Enter size (odd number recommended): "; : INPUT N
50 IF N < 1 THEN LET N = 5
60 LET N = INT(N)
70 PRINT ""
80 REM Upper half
90 FOR I = 1 TO N
100   LET SPACES = N - I
110   FOR J = 1 TO SPACES
120     PRINT "  ";
130   NEXT J
140   FOR J = 1 TO (2 * I - 1)
150     PRINT I; " ";
160   NEXT J
170   PRINT ""
180 NEXT I
190 REM Lower half
200 FOR I = (N - 1) TO 1 STEP -1
210   LET SPACES = N - I
220   FOR J = 1 TO SPACES
230     PRINT "  ";
240   NEXT J
250   FOR J = 1 TO (2 * I - 1)
260     PRINT I; " ";
270   NEXT J
280   PRINT ""
290 NEXT I