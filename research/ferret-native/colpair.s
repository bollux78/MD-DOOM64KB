| fr_col_pair: textured column kernel for the paired 4bpp art path (packed==2).
| void fr_col_pair(uint8_t *dst, const uint8_t *src, const int16_t *sc, int32_t base,
|                  uint32_t n, uint32_t odd_first, const uint8_t *swap);
| Row y: c = src[(base + sc[y]) & 8191]; odd rows store swap[c] (nibbles exchanged); dst advances 2 per row.
| Same result as the C loop in core.c tex() when every p=base+sc[y] is in [0,24576), which the caller checks.
    .text
    .globl fr_col_pair
    .even
fr_col_pair:
    movem.l %d2-%d5/%a2-%a3,-(%sp)
    move.l 28(%sp),%a0
    move.l 32(%sp),%a1
    move.l 36(%sp),%a3
    move.l 40(%sp),%d4
    move.l 44(%sp),%d5
    move.l 48(%sp),%d3
    move.l 52(%sp),%a2
    move.w #8191,%d2
    moveq #0,%d1
    tst.l %d5
    beq.s 9f
    tst.l %d3
    beq.s 1f
    move.w (%a3)+,%d0
    add.w %d4,%d0
    and.w %d2,%d0
    move.b (%a1,%d0.w),%d1
    move.b (%a2,%d1.w),(%a0)
    addq.l #2,%a0
    subq.l #1,%d5
1:  move.l %d5,%d3
    lsr.l #1,%d3
    beq.s 3f
    subq.l #1,%d3
2:  move.w (%a3)+,%d0
    add.w %d4,%d0
    and.w %d2,%d0
    move.b (%a1,%d0.w),(%a0)
    move.w (%a3)+,%d0
    add.w %d4,%d0
    and.w %d2,%d0
    move.b (%a1,%d0.w),%d1
    move.b (%a2,%d1.w),2(%a0)
    addq.l #4,%a0
    dbra %d3,2b
3:  btst #0,%d5
    beq.s 9f
    move.w (%a3)+,%d0
    add.w %d4,%d0
    and.w %d2,%d0
    move.b (%a1,%d0.w),(%a0)
9:  movem.l (%sp)+,%d2-%d5/%a2-%a3
    rts

| void fr_clear11520(void *p): zero 11520 bytes (the 160x72 frame) with MOVEM, 48 bytes per store, 240 stores.
| p must be word aligned (68000 long access needs only even addresses).
    .globl fr_clear11520
    .even
fr_clear11520:
    movem.l %d2-%d7/%a2-%a5,-(%sp)
    move.l 44(%sp),%a0
    lea 11520(%a0),%a0
    moveq #0,%d1
    moveq #0,%d2
    moveq #0,%d3
    moveq #0,%d4
    moveq #0,%d5
    moveq #0,%d6
    moveq #0,%d7
    move.l %d1,%a1
    move.l %d1,%a2
    move.l %d1,%a3
    move.l %d1,%a4
    move.l %d1,%a5
    move.w #239,%d0
1:  movem.l %d1-%d7/%a1-%a5,-(%a0)
    dbra %d0,1b
    movem.l (%sp)+,%d2-%d7/%a2-%a5
    rts

| fr_col_pair_r: same kernel, register calling convention for inline callers (no stack traffic):
|   a0=dst a1=src a3=sc d4=base(low 16 bits used) d5=n d3=odd_first a2=swap
| Clobbers d0-d5, a0, a1, a3 (a2 preserved). Caller guarantees n>0.
    .globl fr_col_pair_r
    .even
fr_col_pair_r:
    move.w #8191,%d2
    moveq #0,%d1
    tst.l %d3
    beq.s 1f
    move.w (%a3)+,%d0
    add.w %d4,%d0
    and.w %d2,%d0
    move.b (%a1,%d0.w),%d1
    move.b (%a2,%d1.w),(%a0)
    addq.l #2,%a0
    subq.l #1,%d5
1:  move.l %d5,%d3
    lsr.l #1,%d3
    beq.s 3f
    subq.l #1,%d3
2:  move.w (%a3)+,%d0
    add.w %d4,%d0
    and.w %d2,%d0
    move.b (%a1,%d0.w),(%a0)
    move.w (%a3)+,%d0
    add.w %d4,%d0
    and.w %d2,%d0
    move.b (%a1,%d0.w),%d1
    move.b (%a2,%d1.w),2(%a0)
    addq.l #4,%a0
    dbra %d3,2b
3:  btst #0,%d5
    beq.s 9f
    move.w (%a3)+,%d0
    add.w %d4,%d0
    and.w %d2,%d0
    move.b (%a1,%d0.w),(%a0)
9:  rts
