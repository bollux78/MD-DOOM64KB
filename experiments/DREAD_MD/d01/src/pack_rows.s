#ifdef DREAD_PACKED_ROWS
        .text
        .globl DreadPackRows
/* Each input tile has eight 32-bit rows, producing two contiguous output
 * tiles. All source and destination tiles are in column-major order. */
DreadPackRows:
        movea.l 4(%sp),%a0
        movea.l 8(%sp),%a1
        move.l 12(%sp),%d1
        subq.w #1,%d1
1:
        .rept 8
        move.l (%a0)+,%d0
        move.l %d0,(%a1)+
        move.l %d0,(%a1)+
        .endr
        dbra %d1,1b
        rts
#endif
