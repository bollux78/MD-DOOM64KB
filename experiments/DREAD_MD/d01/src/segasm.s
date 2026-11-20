/* DREAD-MD D01: per-seg column preparation in 68000 asm (called from draw_seg in render.c)
 *
 * void seg_rows2(int16_t *a, int16_t *b, int32_t Ya, int32_t dYa, int32_t Yb, int32_t dYb, int16_t n)
 * void seg_rows1(int16_t *a, int32_t Ya, int32_t dYa, int16_t n)
 *      a[k] = ceil16(Ya + k*dYa) (and b), n > 0
 * void seg_anchors(SegA *p)
 *      perspective-correct u and texel step (zq) every 2^r_ash columns, linear in between,
 *      written to a_u[] / a_zpp[] for columns xs..xe-1 (see seg_anchors_c in render.c)      */
        .text
        .globl  seg_rows2
        .globl  seg_rows1
        .globl  seg_anchors

seg_rows2:
        movem.l %d2-%d4,-(%sp)
        movem.l 16(%sp),%a0-%a1             /* a, b */
        movem.l 24(%sp),%d0-%d3             /* Ya dYa Yb dYb */
        move.l  40(%sp),%d4                 /* n (int16 promoted) */
        addi.l  #0xFFFF,%d0
        addi.l  #0xFFFF,%d2
        subq.w  #1,%d4
1:      swap    %d0
        move.w  %d0,(%a0)+
        swap    %d0
        add.l   %d1,%d0
        swap    %d2
        move.w  %d2,(%a1)+
        swap    %d2
        add.l   %d3,%d2
        dbra    %d4,1b
        movem.l (%sp)+,%d2-%d4
        rts

seg_rows1:
        move.l  4(%sp),%a0
        movem.l 8(%sp),%d0-%d1
        move.l  %d2,%a1
        move.l  16(%sp),%d2
        addi.l  #0xFFFF,%d0
        subq.w  #1,%d2
1:      swap    %d0
        move.w  %d0,(%a0)+
        swap    %d0
        add.l   %d1,%d0
        dbra    %d2,1b
        move.l  %a1,%d2
        rts

#define IZ    0
#define UZ    4
#define DIZ   8
#define DUZ   12
#define DIZ8  16
#define DUZ8  20
#define XS    24
#define XE    26
#define HAVEB 28
#define UB    30
#define QB    32

/* calc_uq: d0 = iz (>= 1), d1 = uz (>= 0)  ->  d4.w = u = (uz << 8) / iz (saturated),
   d5.l = zq << 16, zq = min(32767, (2^24/iz) * r_zppk >> 14).  clobbers d0, d1 */
calc_uq:
        lsl.l   #8,%d1                      /* uz8 (wraps like the C version) */
        cmpi.l  #65536,%d0
        bcs.s   2f
        move.l  %d0,%d4
        lsr.l   #5,%d4                      /* d = iz >> 5 */
        lsr.l   #5,%d1
        move.l  %d4,%d5
        swap    %d5
        clr.w   %d5
        cmp.l   %d5,%d1
        bcc.s   3f
        divu.w  %d4,%d1
        move.w  %d1,%d4
        bra.s   4f
2:      move.l  %d0,%d5
        swap    %d5
        clr.w   %d5
        cmp.l   %d5,%d1
        bcc.s   3f
        divu.w  %d0,%d1
        move.w  %d1,%d4
        bra.s   4f
3:      move.w  #0xFFFF,%d4
4:      cmpi.l  #65536,%d0                  /* z4 = 2^24 / iz */
        bcs.s   5f
        move.l  %d0,%d1
        lsr.l   #8,%d1
        move.l  #65536,%d5
        divu.w  %d1,%d5
        bra.s   7f
5:      cmpi.l  #257,%d0
        bcc.s   6f
        move.w  #0xFFFF,%d5
        bra.s   7f
6:      move.l  #0x1000000,%d5
        divu.w  %d0,%d5
7:      mulu.w  r_zppk,%d5
        lsr.l   #8,%d5
        lsr.l   #6,%d5
        cmpi.l  #32767,%d5
        bls.s   8f
        move.l  #32767,%d5
8:      swap    %d5
        clr.w   %d5
        rts

/* sdiv16: d0 = signed value (|d0| < 65536), d6 = n (1..15)  ->  d0 = (d0 << 16) / n, truncated
   toward zero.  clobbers d1 */
sdiv16:
        move.l  %d0,%d1
        bpl.s   1f
        neg.l   %d0
1:      divu.w  %d6,%d0                     /* r : q1 */
        move.w  %d0,-(%sp)
        clr.w   %d0                         /* r << 16 */
        divu.w  %d6,%d0                     /* q2 */
        swap    %d0
        move.w  (%sp)+,%d0
        swap    %d0                         /* q1 << 16 | q2 */
        tst.l   %d1
        bpl.s   2f
        neg.l   %d0
2:      rts

/* registers: d2 U (16.16) / uA, d3 Z (16.16), d4 dU, d5 dZ, d6 n, d7 k, a0 &a_u[k], a1 &a_zpp[k],
   a2 SegA, a4 = anchor span (columns) */
seg_anchors:
        movem.l %d2-%d7/%a2-%a4,-(%sp)
        move.l  40(%sp),%a2
        move.w  r_ash,%d0
        moveq   #1,%d1
        lsl.w   %d0,%d1
        move.w  %d1,%a4
        move.w  XS(%a2),%d7
        move.w  %d7,%d0
        add.w   %d0,%d0
        lea     a_u,%a0
        adda.w  %d0,%a0
        lea     a_zpp,%a1
        adda.w  %d0,%a1
        clr.w   HAVEB(%a2)
.Lan:
        cmp.w   XE(%a2),%d7
        bge     .Landone
        move.w  XE(%a2),%d6
        subq.w  #1,%d6
        sub.w   %d7,%d6                     /* n = xe - 1 - k */
        cmp.w   %a4,%d6
        ble.s   1f
        move.w  %a4,%d6
1:      addq.w  #1,rstats+10                /* rstats.anchors */
        tst.w   HAVEB(%a2)
        beq.s   2f
        move.w  UB(%a2),%d2
        move.l  QB(%a2),%d3
        bra.s   3f
2:      move.l  IZ(%a2),%d0
        moveq   #1,%d1
        cmp.l   %d1,%d0
        bge.s   4f
        move.l  %d1,%d0
4:      move.l  UZ(%a2),%d1
        bpl.s   5f
        moveq   #0,%d1
5:      bsr     calc_uq
        move.w  %d4,%d2
        move.l  %d5,%d3
3:      clr.w   HAVEB(%a2)
        moveq   #0,%d4
        moveq   #0,%d5
        tst.w   %d6
        ble     .Lstore
        cmp.w   %a4,%d6
        bne.s   6f
        move.l  IZ(%a2),%d0
        add.l   DIZ8(%a2),%d0
        move.l  UZ(%a2),%d1
        add.l   DUZ8(%a2),%d1
        bra.s   7f
6:      move.w  %d6,%d4                     /* iz + diz*n, uz + duz*n (n < 16) */
        subq.w  #1,%d4
        move.l  IZ(%a2),%d0
        move.l  UZ(%a2),%d1
8:      add.l   DIZ(%a2),%d0
        add.l   DUZ(%a2),%d1
        dbra    %d4,8b
7:      moveq   #1,%d4
        cmp.l   %d4,%d0
        bge.s   9f
        move.l  %d4,%d0
9:      tst.l   %d1
        bpl.s   10f
        moveq   #0,%d1
10:     bsr     calc_uq                     /* d4.w = uB, d5 = ZB */
        move.w  %d4,UB(%a2)
        move.l  %d5,QB(%a2)
        moveq   #0,%d0
        move.w  %d4,%d0
        moveq   #0,%d1
        move.w  %d2,%d1
        sub.l   %d1,%d0                     /* du = uB - uA */
        move.l  %d5,%d1
        sub.l   %d3,%d1                     /* (qB - qA) << 16 */
        cmp.w   %a4,%d6
        bne.s   11f
        moveq   #16,%d4
        sub.w   r_ash,%d4
        lsl.l   %d4,%d0                     /* dU = du << (16 - ash) */
        move.w  r_ash,%d4
        asr.l   %d4,%d1                     /* dZ */
        move.l  %d0,%d4
        move.l  %d1,%d5
        move.w  #1,HAVEB(%a2)
        bra.s   .Lstore
11:     move.l  %d0,%d4                     /* last, shorter span: exact divides */
        move.l  %d1,%d0
        swap    %d0
        ext.l   %d0
        bsr     sdiv16
        move.l  %d0,%d5
        move.l  %d4,%d0
        bsr     sdiv16
        move.l  %d0,%d4
.Lstore:
        move.w  %d6,%d0                     /* cnt = min(max(n, 1), xe - k) */
        bgt.s   1f
        moveq   #1,%d0
1:      move.w  XE(%a2),%d1
        sub.w   %d7,%d1
        cmp.w   %d1,%d0
        ble.s   2f
        move.w  %d1,%d0
2:      add.w   %d0,%d7
        swap    %d2
        clr.w   %d2                         /* U = uA << 16 */
        subq.w  #1,%d0
3:      swap    %d2
        move.w  %d2,(%a0)+
        swap    %d2
        add.l   %d4,%d2
        swap    %d3
        move.w  %d3,(%a1)+
        swap    %d3
        add.l   %d5,%d3
        dbra    %d0,3b
        cmp.w   %a4,%d6                     /* advance iz, uz by m columns */
        bne.s   4f
        move.l  DIZ8(%a2),%d0
        add.l   %d0,IZ(%a2)
        move.l  DUZ8(%a2),%d0
        add.l   %d0,UZ(%a2)
        bra     .Lan
4:      move.w  %d6,%d0
        bgt.s   5f
        moveq   #1,%d0
5:      subq.w  #1,%d0
6:      move.l  DIZ(%a2),%d1
        add.l   %d1,IZ(%a2)
        move.l  DUZ(%a2),%d1
        add.l   %d1,UZ(%a2)
        dbra    %d0,6b
        bra     .Lan
.Landone:
        movem.l (%sp)+,%d2-%d7/%a2-%a4
        rts
