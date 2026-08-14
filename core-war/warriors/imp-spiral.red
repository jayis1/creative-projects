;Imp-Spiral.red - An imp that uses SPL to create multiple imp processes,
;                 each running at different speeds. Hard to kill.

        ORG     start

start   SPL     1               ; Split to create a new process
        SPL     1               ; Split again
        MOV     0, 1            ; Imp: copy self forward
        JMP     -1              ; Loop back to SPL