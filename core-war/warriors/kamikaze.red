;Kamikaze.red - A fast bomber that bombs aggressively and then
;              self-destructs. High risk, high reward.

        ORG     start

start   MOV     bomb, @ptr      ; Drop bomb at pointer
        ADD     #3, ptr          ; Move pointer forward fast
        DJN     start, count     ; Decrement counter, loop if not zero
        DAT     #0, #0           ; Self-destruct when done
ptr     DAT     #0, #100         ; Bomb pointer
count   DAT     #0, #2000         ; Number of bombs to drop
bomb    DAT     #0, #0           ; The bomb