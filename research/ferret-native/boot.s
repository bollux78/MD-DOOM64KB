    .section .vectors,"a"
    .long 0x00fffffc
    .long _start
    .irp n,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63
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
trap:
    move.l #0x800000ff,0xfff008
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
    move.l #0x800000ff,0xfff008
2:  bra.s 2b
