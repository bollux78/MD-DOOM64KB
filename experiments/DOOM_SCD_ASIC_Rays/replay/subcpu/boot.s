    .text
    .globl subcpu_vectors
subcpu_vectors:
    .long 0x00080000, entry
    .rept 62
    .long fault
    .endr
entry:
    move.w #0x2700,%sr
    clr.w 0xff8028
    move.w #0x5343,0xff8020
1:
    cmpi.w #1,0xff8018
    bne.s 1b
    move.w 0xff8002,%d0
    andi.w #7,%d0
    cmpi.w #2,%d0
    bne.s fault
    jsr ray_bench
    move.w #1,0xff8002
    move.w #1,0xff8028
2:
    bra.s 2b
fault:
    move.w #0xdead,0xff8020
    bra.s fault

    .section .rodata
    .balign 2
    .globl ray_assets
ray_assets:
    .incbin "build/ray-assets.bin"
