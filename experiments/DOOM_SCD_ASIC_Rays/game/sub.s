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
    cmpi.w #0x37e1,0xff8018
    bne.s 1b
    move.w 0xff8002,%d0
    andi.w #7,%d0
    cmpi.w #2,%d0
    bne.w fault
    jsr load_ray_map
    move.w #4,0xff8002
    move.w #0x37e1,0xff8026
    move.w #0x37e1,%d2
2:
    moveq #0,%d0
    move.w 0xff8018,%d0
    cmp.w %d2,%d0
    beq.s 2b
    move.w %d0,%d2
    move.w 0xff800c,%d3
    clr.w 0xff8002
    move.w 0xff8002,%d1
    andi.w #7,%d1
    cmpi.w #2,%d1
    bne.s fault
    move.w 0xff800c,%d4
    sub.w %d3,%d4
    move.l %d2,-(%sp)
    jsr run_ray_batch
    addq.l #4,%sp
    tst.l %d0
    bne.s fault
    move.w 0xff800c,%d3
    move.w #4,0xff8002
    move.w 0xff800c,%d0
    sub.w %d3,%d0
    add.w %d4,%d0
    andi.w #0x0fff,%d0
    move.w %d0,0xff8024
    move.w %d2,0xff8028
    bra.s 2b
fault:
    move.w #0xdead,0xff8020
    bra.s fault

    .section .rodata
    .balign 2
    .globl ray_assets
ray_assets:
    .incbin "build/ray-assets.bin"
