10 REM *** Mandelbrot ASCII Art ***
20 PRINT "Mandelbrot Set (ASCII)"
30 FOR PY = -12 TO 12
40   FOR PX = -39 TO 19
50     LET X0 = PX / 20.0
60     LET Y0 = PY / 12.0
70     LET X = 0.0
80     LET Y = 0.0
90     LET I = 0
95     LET X2 = X * X
96     LET Y2 = Y * Y
100    WHILE X2 + Y2 <= 4.0 AND I < 32
110      LET Y = 2.0 * X * Y + Y0
120      LET X = X2 - Y2 + X0
130      LET I = I + 1
135      LET X2 = X * X
136      LET Y2 = Y * Y
140    WEND
150    IF I >= 32 THEN PRINT " "; : GOTO 170
160    LET C$ = CHR$(32 + I)
165    PRINT C$;
170  NEXT PX
180  PRINT
190 NEXT PY