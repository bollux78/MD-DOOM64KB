    .section .text.vectors,"ax"
    .globl subcpu_vectors
subcpu_vectors:
    .long 0x00080000, entry
    .rept 62
    .long fault
    .endr
entry:
    move.w #0x2700,%sr
    lea __bss_start,%a0
    lea _end,%a1
1:  cmp.l %a1,%a0
    bcc.s 2f
    clr.b (%a0)+
    bra.s 1b
2:  jsr sub_main
3:  bra.s 3b
fault:
    move.w #0xdead,0xff8020
    bra.s fault
