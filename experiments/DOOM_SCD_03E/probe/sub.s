    .section .text
    .long 0x00080000, entry
    .rept 62
    .long fault
    .endr
entry:
    move.w #0x2700,%sr
    clr.w 0xff8026
    move.w #4,0xff8002
    move.w #0x5343,0xff8020
wait:
    move.w 0xff8018,%d0
    beq.s wait
    move.w %d0,0x0c0000
    move.w #5,0xff8002
    move.w %d0,0xff8026
idle:
    bra.s idle
fault:
    move.w #0xdead,0xff8020
    bra.s fault
