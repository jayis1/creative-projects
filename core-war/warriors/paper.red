;Paper.red - A replicating warrior. Copies itself to a new location
;            and splits to run the copy, creating an exponential spread.

        ORG     copy

copy    SPL     @copy          ; Split to run the new copy
        MOV     copy, <copy     ; Copy instruction forward
        ADD     #10, copy       ; Move target pointer
        MOV     copy, <copy      ; Copy another instruction
        JMP     copy, 0         ; Jump back to keep replicating