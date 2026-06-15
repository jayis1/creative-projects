10 REM *** Guess the Number Game ***
20 PRINT "GUESS THE NUMBER!"
30 PRINT "I'm thinking of a number between 1 and 100"
40 LET N = INT(RND(1) * 100) + 1
50 LET T = 0
60 LET T = T + 1
70 INPUT "Your guess? "; G
80 IF G < N THEN PRINT "Too low!" : GOTO 60
90 IF G > N THEN PRINT "Too high!" : GOTO 60
100 PRINT "You got it in "; T; " tries!"