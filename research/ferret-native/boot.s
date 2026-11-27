    .section .vectors,"a"
    .long 0x00fffffc
    .long _start
    .irp n,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29
    .long vec\n
    .endr
    .long fr_vblank_isr       | vector 30: level-6 (VBlank) autovector; only fires when a build unmasks it (FR_ASYNC)
    .irp n,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63
    .long vec\n
    .endr
    .section .header,"a"
    .space 256
    .section .text.start,"ax"
    .global _start
_start:
    move.w #0x2700,%sr
    lea __bss_start,%a0
    lea __bss_end,%a1
    moveq #0,%d0
1:
    cmpa.l %a1,%a0
    bcc.s 2f
    move.l %d0,(%a0)+
    bra.s 1b
2:
    jsr md_main
    move.l #0x80000100,0xfff008
3:
    bra.s 3b

    .irp n,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63
vec\n:
    move.w #\n,0xfff0a0
    bra.w vcommon
    .endr
vcommon:
    move.w #0x2700,%sr
    lea 0xfff0a4,%a0
    moveq #11,%d0
1:  move.l (%sp)+,(%a0)+
    dbra %d0,1b
    moveq #0,%d0
    move.w 0xfff0a0,%d0
    ori.l #0x80000200,%d0
    move.l %d0,0xfff008
2:  bra.s 2b

| VBlank interrupt: acknowledge, call the C service routine (it may clobber d0-d1/a0-a1, saved here), return.
    .globl fr_vblank_isr
    .even
fr_vblank_isr:
    movem.l %d0-%d1/%a0-%a1,-(%sp)
    move.w 0xc00004,%d0
    jsr fr_vblank_c
    movem.l (%sp)+,%d0-%d1/%a0-%a1
    rte
