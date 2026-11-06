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
    clr.w 0xff8028
    move.w #4,0xff8002
    move.w #0x5343,0xff8020
1:
    cmpi.w #1,0xff8018
    bne.s 1b
    move.w #0x37e1,0x0c0000
    move.w #5,0xff8002
    move.w #1,0xff8026
2:
    cmpi.w #2,0xff8018
    bne.s 2b
    lea 0x0c0000,%a0
    bsr.w probe
    move.w %d0,0xff802a
    move.w %d1,0xff8024
    clr.w 0xff8002
    move.w #2,0xff8026
3:
    cmpi.w #3,0xff8018
    bne.s 3b
    move.w 0xff8002,%d0
    andi.w #7,%d0
    cmpi.w #2,%d0
    bne.w fault
    lea 0x080000,%a0
    bsr.w probe
    move.w %d0,0xff8022
    move.w %d1,0xff802c
    move.w %d2,0xff802e
    move.w #4,0xff8002
    move.w #3,0xff8028
4:
    cmpi.w #4,0xff8018
    bne.s 4b
    move.w #0xc81e,0x0c0000
    move.w #5,0xff8002
    move.w #4,0xff8026
5:
    bra.s 5b

/* 8x8 identity sampling from stamp 1, with the source row alternating words.
   d0 = 1 exact, 2 pixel mismatch, 3 busy timeout; d1 = ticks; d2 = first word. */
probe:
    lea 0x80(%a0),%a1
    lea 0x3000(%a0),%a2
    lea 0x4000(%a0),%a3
    move.w #1,0x2000(%a0)
    moveq #0,%d3
    moveq #7,%d4
6:
    move.l #0x12345678,(%a1)+
    clr.w (%a2)+
    move.w %d3,(%a2)+
    move.w #0x0800,(%a2)+
    clr.w (%a2)+
    move.l #0xdeadbeef,(%a3)+
    addq.w #8,%d3
    dbra %d4,6b
    clr.w 0xff8058
    move.w #0x0800,0xff805a
    clr.w 0xff805c
    move.w #0x1000,0xff805e
    clr.w 0xff8060
    move.w #8,0xff8062
    move.w #8,0xff8064
    move.w 0xff800c,%d1
    move.w #0x0c00,0xff8066
    move.w #8191,%d4
7:
    tst.w 0xff8058
    bpl.s 8f
    dbra %d4,7b
    moveq #3,%d0
    bra.s 10f
8:
    moveq #1,%d0
    lea 0x4000(%a0),%a3
    moveq #7,%d4
9:
    cmpi.l #0x12345678,(%a3)+
    dbne %d4,9b
    beq.s 10f
    moveq #2,%d0
10:
    move.w 0x4000(%a0),%d2
    neg.w %d1
    add.w 0xff800c,%d1
    andi.w #0x0fff,%d1
    rts
fault:
    move.w #0xdead,0xff8020
    bra.s fault
