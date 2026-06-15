10 REM =============================================
20 REM 99 Bottles of Beer
30 REM =============================================
40 LET B = 99
50 DO WHILE B > 0
60   PRINT B; " bottle"; : IF B <> 1 THEN PRINT "s"; ELSE PRINT "";
70   PRINT " of beer on the wall,";
80   PRINT B; " bottle"; : IF B <> 1 THEN PRINT "s"; ELSE PRINT "";
90   PRINT " of beer."
100   PRINT "Take one down, pass it around,";
110   LET B = B - 1
120   IF B > 0 THEN PRINT B; " bottle"; : IF B <> 1 THEN PRINT "s"; ELSE PRINT "";
130   IF B = 0 THEN PRINT "No more bottles";
140   IF B > 0 THEN PRINT " of beer on the wall." ELSE PRINT " of beer on the wall."
150   PRINT ""
160 LOOP
170 PRINT "No more bottles of beer on the wall,"
180 PRINT "No more bottles of beer."
190 PRINT "Go to the store and buy some more,"
200 PRINT "99 bottles of beer on the wall!"