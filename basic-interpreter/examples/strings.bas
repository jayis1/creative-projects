10 REM *** String Functions Demo ***
20 LET A$ = "Hello, World!"
30 PRINT "Original: "; A$
40 PRINT "Length: "; LEN(A$)
50 PRINT "Left 5: "; LEFT$(A$, 5)
60 PRINT "Right 6: "; RIGHT$(A$, 6)
70 PRINT "Mid 8,5: "; MID$(A$, 8, 5)
80 PRINT "ASC of 'H': "; ASC(A$)
90 PRINT "CHR$(65): "; CHR$(65)
100 LET B$ = STR$(42)
110 PRINT "STR$(42): '"; B$; "'"
120 LET C = VAL("3.14")
130 PRINT "VAL('3.14'): "; C
140 PRINT "INSTR: "; INSTR(A$, "World")