10 REM =============================================
20 REM Tower of Hanoi Solver
30 REM =============================================
40 PRINT "Tower of Hanoi - 3 Disks"
50 PRINT "========================"
60 LET N = 3
70 GOSUB 100
80 PRINT ""
90 PRINT "Done!"; : END
100 REM HANOI(N, FROM, TO, VIA)
110 RETURN