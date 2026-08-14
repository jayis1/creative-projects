;Dwarf.red - A classic bomber. Throws DAT bombs at regular intervals.
;            A staple of Core War strategy.

        ORG     start

step    EQU     4              ; Bombing interval (distance between bombs)

start   ADD     #step, bomb    ; Increment bomb pointer by step
        MOV     bomb, @bomb    ; Drop a bomb at the pointer
        JMP     start          ; Loop back to do it again
bomb    DAT     #0, #0         ; The bomb (DAT instruction)