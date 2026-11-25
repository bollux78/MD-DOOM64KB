    .section .vectors,"a"
    .long 0x00fffffc
    .long _start
    .rept 62
    .long trap
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
