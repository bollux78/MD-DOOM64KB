    .text
    .align 2
    .globl scd_wall
scd_wall:
    movem.l %d2-%d7/%a2,-(%sp)
    movea.l 32(%sp),%a0
    movea.l 36(%sp),%a1
    movea.l 40(%sp),%a2
    move.l 44(%sp),%d0
    move.l 48(%sp),%d1
    move.l 52(%sp),%d2
    move.l 56(%sp),%d3
    btst #1,%d3
    bne.s 1f
    andi.w #1,%d3
    bsr.w wall60
    bra.s 2f
1:
    andi.w #1,%d3
    bsr.w wall113
2:
    movem.l (%sp)+,%d2-%d7/%a2
    rts
wall60:
    .incbin "build/R60_WallColumn.bin"
wall113:
    .incbin "build/R113_WallColumn.bin"

    .section .rodata
    .balign 4
    .globl scd_fixture
scd_fixture:
    .incbin "build/fixture.bin"
