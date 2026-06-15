10 REM =============================================
20 REM Quadratic Equation Solver
30 REM Solves ax^2 + bx + c = 0
40 REM ==============================================
50 PRINT "Quadratic Equation Solver"
60 PRINT "========================="
70 PRINT "Solving ax^2 + bx + c = 0"
80 PRINT ""
90 PRINT "Enter a: "; : INPUT A
100 PRINT "Enter b: "; : INPUT B
110 PRINT "Enter c: "; : INPUT C
120 LET D = B * B - 4 * A * C
130 PRINT ""
140 PRINT "Discriminant = "; D
150 IF D > 0 THEN GOTO 200
160 IF D = 0 THEN GOTO 260
170 REM D < 0: complex roots
180 LET REAL = -B / (2 * A)
190 PRINT "Complex roots: "; REAL; " +/- "; SQR(ABS(D)) / (2 * A); "i"
195 GOTO 280
200 REM D > 0: two real roots
210 LET X1 = (-B + SQR(D)) / (2 * A)
220 LET X2 = (-B - SQR(D)) / (2 * A)
230 PRINT "Root 1 = "; X1
240 PRINT "Root 2 = "; X2
250 GOTO 280
260 REM D = 0: one real root
270 LET X1 = -B / (2 * A)
275 PRINT "Repeated root = "; X1
280 PRINT ""