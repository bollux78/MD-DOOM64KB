    .text
    .globl subcpu_vectors
subcpu_vectors:
    .long 0x00080000, entry
    .rept 62
    .long fault
    .endr
entry:
    move.w #0x2700,%sr
    clr.w 0xff8026
    move.w #4,%d4
    move.w %d4,0xff8002
    bsr.s fill
    move.w #0x5343,0xff8020
    moveq #0,%d2
1:
    move.w 0xff8018,%d0
    cmp.w %d2,%d0
    beq.s 1b
    move.w %d0,%d2
    move.w %d2,0x0c0000
    eori.w #1,%d4
    move.w %d4,0xff8002
    move.w %d2,0xff8026
    /* After the first handoff populate the second bank, then keep both resident. */
    cmpi.w #1,%d2
    bne.s 1b
    bsr.s fill
    bra.s 1b
fill:
    lea frame_data(%pc),%a0
    lea 0x0c0020,%a1
    move.w #835,%d0
2:
    move.l (%a0)+,(%a1)+
    dbra %d0,2b
    clr.w (%a1)
    /* M1: same frame already in VDP plane pitch (64 words/row), rows 1..21,
       plane A block then plane B block, at bank offset 0x4000. */
    lea 0x0c0020+152,%a0
    lea 0x0c4000,%a1
    lea 0x0c4000+21*128,%a2
    moveq #20,%d1
3:
    moveq #18,%d0
4:
    move.l (%a0)+,(%a1)+
    dbra %d0,4b
    moveq #18,%d0
5:
    move.l (%a0)+,(%a2)+
    dbra %d0,5b
    moveq #12,%d0
6:
    clr.l (%a1)+
    clr.l (%a2)+
    dbra %d0,6b
    dbra %d1,3b
    rts
fault:
    move.w #0xdead,0xff8020
    bra.s fault
    .balign 2
frame_data:
    .incbin "build/e1m1-frame.bin"
