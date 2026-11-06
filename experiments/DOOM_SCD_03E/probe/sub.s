    .section .text
    .long 0x00080000, entry
    .rept 62
    .long fault
    .endr
entry:
    move.w #0x2700,%sr
    clr.w 0xff8026
    clr.w 0xff802a
    move.w #4,0xff8002
    move.w #0x5343,0xff8020
wait_probe:
    move.w 0xff8018,%d0
    beq.s wait_probe
    move.w %d0,0x0c0000
    move.w #5,0xff8002
    move.w %d0,0xff8026
    move.w %d0,%d2

/* Both CPUs know RET=1 when a packet is submitted. Take the packet bank,
   draw into it, then give the same bank back before acknowledging. */
wait_packet:
    move.w 0xff8018,%d0
    cmp.w %d2,%d0
    beq.s wait_packet
    moveq #0,%d2
    move.w %d0,%d2
    move.w #4,0xff8002
    move.l %d2,-(%sp)
    move.l #0x000c0000,-(%sp)
    jsr scd_render_world
    addq.l #8,%sp
    move.w %d0,0xff802a
    move.w #5,0xff8002
    move.w %d2,0xff8026
    bra.s wait_packet
fault:
    move.w #0xdead,0xff8020
    bra.s fault
