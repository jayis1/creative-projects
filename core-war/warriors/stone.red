;Stone.red - A compact bomber that uses indirect addressing to
;            sweep bombs through core efficiently.

        ORG     start

start   MOV     bomb, @ptr     ; Drop bomb via pointer
        ADD     #6, ptr         ; Move pointer forward
        JMP     start          ; Repeat
ptr     DAT     #0, #0          ; Pointer (initially points near start)
bomb    DAT     #0, #0          ; The bomb