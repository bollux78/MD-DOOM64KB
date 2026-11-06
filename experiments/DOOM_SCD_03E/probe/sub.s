    .section .text
    .long 0x00080000, entry
    .rept 62
    .long fault
    .endr
entry:
    move.w #0x2700,%sr
    clr.w 0xff8026
    clr.w 0xff8028
    clr.w 0xff802a
    move.w #4,%d4
    move.w %d4,0xff8002
    move.w #0x5343,0xff8020
wait_probe:
    move.w 0xff8018,%d0
    beq.s wait_probe
    move.w %d0,0x0c0000
    eori.w #1,%d4
    move.w %d4,0xff8002
    move.w %d0,0xff8028
    move.w %d0,0xff8026
    move.w %d0,%d2

/* Acknowledge ownership immediately, then draw in the received bank.
   The next request returns this batch and makes the other bank available. */
wait_packet:
    move.w 0xff8018,%d0
    cmp.w %d2,%d0
    beq.s wait_packet
    moveq #0,%d2
    move.w %d0,%d2
    eori.w #1,%d4
    move.w %d4,0xff8002
    move.w %d2,0xff8026
    move.l %d2,-(%sp)
    move.l #0x000c0000,-(%sp)
    move.w 0xff800c,%d3
    jsr scd_render_world
    addq.l #8,%sp
    move.w %d0,0xff802a
    move.w 0xff800c,%d1
    sub.w %d3,%d1
    andi.w #0x0fff,%d1
    move.w %d1,0xff8024
    move.w %d2,0xff8028
    bra.w wait_packet
fault:
    move.w #0xdead,0xff8020
    bra.s fault
