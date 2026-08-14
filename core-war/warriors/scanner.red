;Scanner.red - A warrior that scans core looking for non-empty cells,
;              then bombs them. More intelligent than a simple bomber.

        ORG     scan

scan    ADD     step, ptr      ; Move scan pointer forward
ptr     JMZ     scan, 100      ; If location is zero, keep scanning; else fall through
        MOV     bomb, @ptr      ; Drop a bomb on the target
        SUB     step, ptr       ; Back up pointer
        JMP     scan            ; Resume scanning
step    DAT     #10, #10        ; Scan interval
bomb    DAT     #0, #0          ; The bomb