10 REM *** GOSUB/RETURN Demo ***
20 PRINT "Main program start"
30 GOSUB 100
40 PRINT "Back in main"
50 GOSUB 200
60 PRINT "Main program end"
70 END
100 REM *** Subroutine 1 ***
110 PRINT "  In subroutine 1"
120 GOSUB 300
130 RETURN
200 REM *** Subroutine 2 ***
210 PRINT "  In subroutine 2"
220 RETURN
300 REM *** Nested subroutine ***
310 PRINT "    Nested subroutine"
320 RETURN