/* DREAD-MD D01 column inner loops (68000). Framebuffer column stride = 4 bytes. */
/* */
/* void col_fill(uint8_t *p, uint16_t n, uint16_t c)      12 cycles / pixel */
/* void col_tex(uint8_t *p, uint16_t n, const uint8_t *tc, int32_t vbot, int32_t negstep, uint16_t hmask) */
/*      draws bottom-up: pixel n-1 first with v = vbot, then v += negstep      34 cycles / pixel (14 bytes of code) */
/* Both jump into a fully unrolled sequence (max VIEW_H = 128 rows). */

        .text
        .globl  col_fill
        .globl  col_tex
        .globl  col_tex_nm
        .globl  seg_columns

col_fill:
        move.l  4(%sp),%a0
        move.l  8(%sp),%d1    /* n (low word) */
        move.l  12(%sp),%d0    /* colour byte */
        subq.l  #4,%a0    /* displacements below are (k+1)*4 */
        add.w   %d1,%d1
        add.w   %d1,%d1    /* n*4 bytes of code */
        lea     fill_end(%pc),%a1
        suba.w  %d1,%a1
        jmp     (%a1)
        .set    k,128
        .rept   128
        move.b  %d0,k*4(%a0)
        .set    k,k-1
        .endr
fill_end:
        rts

col_tex:
        movem.l %d2-%d6/%a2,-(%sp)
        move.l  28(%sp),%a0    /* p */
        move.l  32(%sp),%d0    /* n */
        move.l  36(%sp),%a1    /* texture column */
        move.l  40(%sp),%d2    /* v (16.16) */
        move.l  44(%sp),%d4    /* step (16.16, negative) */
        move.l  48(%sp),%d5    /* hmask */
        subq.l  #4,%a0
        move.l  %d2,%d1
        swap    %d1    /* d1.w = integer v, d2.w = fraction */
        move.l  %d4,%d3
        swap    %d3    /* d3.w = integer step, d4.w = fraction */
        /* entry = tex_end - n*14 (14 bytes of code per pixel) */
        add.w   %d0,%d0    /* n*2 */
        move.w  %d0,%d6
        lsl.w   #3,%d0    /* n*16 */
        sub.w   %d6,%d0    /* n*14 */
        lea     tex_end(%pc),%a2
        suba.w  %d0,%a2
        jmp     (%a2)
        .set    k,128
        .rept   128
        move.w  %d1,%d6
        and.w   %d5,%d6
        move.b  0(%a1,%d6.w),k*4(%a0)
        add.w   %d4,%d2
        addx.w  %d3,%d1
        .set    k,k-1
        .endr
tex_end:
        movem.l (%sp)+,%d2-%d6/%a2
        rts

/* void col_tex_nm(uint8_t *p, uint16_t n, const uint8_t *tc, int32_t vbot, int32_t negstep)
   same as col_tex without the wrap mask (caller guarantees 0 <= v < 2H): 26 cycles / pixel, 10 bytes */
col_tex_nm:
        movem.l %d2-%d4/%a2,-(%sp)
        move.l  20(%sp),%a0         /* p */
        move.l  24(%sp),%d0         /* n */
        move.l  28(%sp),%a1         /* texture column (stored twice) */
        move.l  32(%sp),%d2         /* v 16.16 */
        move.l  36(%sp),%d4         /* step 16.16 (negative) */
        subq.l  #4,%a0
        move.l  %d2,%d1
        swap    %d1                 /* d1.w = integer v, d2.w = fraction */
        move.l  %d4,%d3
        swap    %d3                 /* d3.w = integer step, d4.w = fraction */
        mulu.w  #10,%d0             /* 10 bytes of code per pixel */
        lea     texnm_end(%pc),%a2
        suba.w  %d0,%a2
        jmp     (%a2)
        .set    k,128
        .rept   128
        move.b  0(%a1,%d1.w),k*4(%a0)
        add.w   %d4,%d2
        addx.w  %d3,%d1
        .set    k,k-1
        .endr
texnm_end:
        movem.l (%sp)+,%d2-%d4/%a2
        rts

/* ======================================================================================
   void seg_columns(ColJob *j)   -- the per-column work of one seg (see ColJob in render.c)
   registers: d0 top/ntop  d1 bot/nbot  d2 yc  d3 yf  d6 c*2  d7 c
              a2 column pointer  a3 nxt[]  a5 clip[] (ceil at +0, floor at +VW_MAX)  a6 job
   The screen mode (row- or column-doubled, H32/H40) is read from r_* variables set by R_SetMode.
   ====================================================================================== */
#define VW_MAX 160
#define VH_MAX 144
#define NS_B 72                             /* row-doubled modes: 72 rows */
#define CEIL_D (-128)
#define FLOOR_D (VW_MAX - 128)
#define J_FB 0
#define J_YC 4
#define J_YF 8
#define J_YBC 12
#define J_YBF 16
#define J_U 20
#define J_ZPP 24
#define J_C0 28
#define J_XE 30
#define J_CCOL 32
#define J_FCOL 34
#define J_FLAGS 36
#define J_CLOSED 38
#define J_MID 40
#define J_UP 56
#define J_LO 72
#define J_CPAL 88
#define J_FPAL 92

seg_columns:
        movem.l %d2-%d7/%a2-%a6,-(%sp)
        move.l  48(%sp),%a6
        move.l  r_clipbuf,%a5
        lea     128(%a5),%a5                /* a5 = clip + 128: ceiling at CEIL_D, floor at FLOOR_D (8-bit displacements) */
        move.l  r_nxt,%a3
        move.w  J_C0(%a6),%d7
.Lcol:
        cmp.w   J_XE(%a6),%d7
        bge     .Ldone
        moveq   #0,%d0
        move.b  CEIL_D(%a5,%d7.w),%d0       /* top */
        moveq   #0,%d1
        move.b  FLOOR_D(%a5,%d7.w),%d1      /* bot */
        move.w  %d7,%d6
        add.w   %d6,%d6
        lea     r_colofs,%a0
        move.l  J_FB(%a6),%a2
        adda.w  0(%a0,%d6.w),%a2            /* column pointer */
        move.l  J_YC(%a6),%a0
        move.w  0(%a0,%d6.w),%d2            /* yc = clamp(yc, top, bot) */
        cmp.w   %d0,%d2
        bge.s   1f
        move.w  %d0,%d2
1:      cmp.w   %d1,%d2
        ble.s   1f
        move.w  %d1,%d2
1:      move.l  J_YF(%a6),%a0
        move.w  0(%a0,%d6.w),%d3            /* yf = clamp(yf, yc, bot) */
        cmp.w   %d2,%d3
        bge.s   1f
        move.w  %d2,%d3
1:      cmp.w   %d1,%d3
        ble.s   1f
        move.w  %d1,%d3
1:
        move.w  %d2,%d4                     /* ceiling: top .. yc */
        sub.w   %d0,%d4
        ble.s   1f
        move.w  %d0,%d5
        move.w  J_CPAL+2(%a6),%a4
        bsr     span_fill
1:      move.w  %d1,%d4                     /* floor: yf .. bot */
        sub.w   %d3,%d4
        ble.s   1f
        move.w  %d3,%d5
        move.w  J_FPAL+2(%a6),%a4
        bsr     span_fill
1:
        move.w  J_FLAGS(%a6),%d4
        btst    #0,%d4
        beq.s   .Lportal
        btst    #1,%d4                      /* solid wall */
        beq.s   .Lclose
        move.w  %d3,%d4
        sub.w   %d2,%d4
        ble.s   .Lclose
        move.w  %d2,%d5
        lea     J_MID(%a6),%a4
        bsr     tex_part
.Lclose:
        clr.b   CEIL_D(%a5,%d7.w)
        clr.b   FLOOR_D(%a5,%d7.w)
        move.w  %d7,%d4
        addq.w  #1,%d4
        move.b  %d4,0(%a3,%d7.w)
        addq.w  #1,J_CLOSED(%a6)
        bra.s   .Lnext
.Lportal:
        move.w  %d2,%d0                     /* ntop = yc, nbot = yf */
        move.w  %d3,%d1
        btst    #2,%d4
        beq.s   .Lnoup
        move.l  J_YBC(%a6),%a0
        move.w  0(%a0,%d6.w),%d5            /* ybc = clamp(ybc, yc, yf) */
        cmp.w   %d2,%d5
        bge.s   1f
        move.w  %d2,%d5
1:      cmp.w   %d3,%d5
        ble.s   1f
        move.w  %d3,%d5
1:      move.w  %d5,%d0
        move.w  %d5,%d4
        sub.w   %d2,%d4
        ble.s   .Lnoup
        move.w  %d2,%d5
        lea     J_UP(%a6),%a4
        bsr     tex_part
.Lnoup:
        move.w  J_FLAGS(%a6),%d4
        btst    #3,%d4
        beq.s   .Lnolo
        move.l  J_YBF(%a6),%a0
        move.w  0(%a0,%d6.w),%d5            /* ybf = clamp(ybf, ntop, yf) */
        cmp.w   %d0,%d5
        bge.s   1f
        move.w  %d0,%d5
1:      cmp.w   %d3,%d5
        ble.s   1f
        move.w  %d3,%d5
1:      move.w  %d5,%d1
        move.w  %d3,%d4
        sub.w   %d5,%d4
        ble.s   .Lnolo
        lea     J_LO(%a6),%a4
        bsr     tex_part
.Lnolo:
        cmp.w   %d1,%d0
        bge.s   .Lclose
        move.b  %d0,CEIL_D(%a5,%d7.w)
        move.b  %d1,FLOOR_D(%a5,%d7.w)
.Lnext:
        addq.w  #1,%d7                      /* c = find_open(c + 1), path halving */
.Lfind:
        moveq   #0,%d4
        move.b  0(%a3,%d7.w),%d4
        cmp.w   %d4,%d7
        beq     .Lcol
        move.b  0(%a3,%d4.w),%d5
        move.b  %d5,0(%a3,%d7.w)
        moveq   #0,%d7
        move.b  %d5,%d7
        bra.s   .Lfind
.Ldone:
        movem.l (%sp)+,%d2-%d7/%a2-%a6
        rts

/* span_fill: a4.w = colour (byte, or byte*0x101 in column-doubled modes), d5 = y0, d4 = n (> 0), a2 column.
   clobbers a0, a1, d4, d5 */
span_fill:
        add.w   %d5,%d5
        add.w   %d5,%d5
        lea     -4(%a2,%d5.w),%a0
        move.w  %a4,%d5
        add.w   %d4,%d4
        add.w   %d4,%d4
        move.l  r_fill_end,%a1
        suba.w  %d4,%a1
        jmp     (%a1)

        .set    k,NS_B
        .rept   NS_B
        move.b  %d5,k*4(%a0)
        .set    k,k-1
        .endr
        .globl  fillb_end
fillb_end:
        rts
        .set    k,VH_MAX
        .rept   VH_MAX
        move.w  %d5,k*4(%a0)
        .set    k,k-1
        .endr
        .globl  fillw_end
fillw_end:
        rts

/* tex_part: a2 column, a4 Part, d5 y0, d4 n (>0), d7 c, a6 job.  preserves d0-d3, d6, d7, a2, a3, a5, a6
   Part: 0 texels.l  4 wmask  6 hs2  8 hmask  10 pal  12 v at the horizon (16.16)
   Fast path (Dread's scalers): one unrolled routine per quantised texel step, every row a single
   move with constant offsets (16 cycles); a1 = column + v of the top row. Spans that would run past
   the twice-stored column use the masked interpolating core. */
tex_part:
        movem.l %d0-%d3/%d6-%d7/%a3,-(%sp)
        move.w  %d7,%d1
        add.w   %d1,%d1
        move.l  J_U(%a6),%a1
        moveq   #0,%d6
        move.w  0(%a1,%d1.w),%d6            /* u */
        add.w   %d1,%d1
        move.l  J_ZPP(%a6),%a1
        move.l  0(%a1,%d1.w),%d3            /* zpp (texels per row, 16.16, > 0) */
        and.w   4(%a4),%d6                  /* & wmask */
        move.w  6(%a4),%d1
        lsl.l   %d1,%d6                     /* << hs2 */
        move.l  (%a4),%a1
        adda.l  %d6,%a1                     /* a1 = texture column */
        move.w  r_horizon,%d0               /* k = HORIZON - y0 */
        sub.w   %d5,%d0
        move.w  %d0,%d2
        bpl.s   1f
        neg.w   %d2
1:      move.l  %d3,%d1                     /* d1 = zpp * |k| */
        swap    %d1
        mulu.w  %d2,%d1
        swap    %d1
        clr.w   %d1
        move.w  %d3,%d6
        mulu.w  %d2,%d6
        add.l   %d6,%d1
        tst.w   %d0
        bpl.s   1f
        neg.l   %d1
1:      move.l  12(%a4),%d2
        sub.l   %d1,%d2                     /* d2 = v of the top row (16.16) */
        move.w  %d4,%d7                     /* d7 = n */
        subq.w  #1,%d4                      /* d1 = zpp * (n - 1) */
        move.l  %d3,%d1
        swap    %d1
        mulu.w  %d4,%d1
        swap    %d1
        clr.w   %d1
        move.w  %d3,%d6
        mulu.w  %d4,%d6
        add.l   %d6,%d1
        move.w  8(%a4),%d0                  /* hmask */
        cmpi.l  #0x1FFFFF,%d3
        bhi.s   .Lmasked                    /* > 32 texels per row: no scaler */
        move.l  %d2,%d6
        addi.l  #0x8000,%d6                 /* nearest texel: v = -0.3 must not wrap to H - 1 */
        swap    %d6
        and.w   %d0,%d6                     /* d6 = v top, integer, in [0, H) */
        move.l  %d1,%d4
        swap    %d4                         /* d4 = span (integer texels) */
        move.w  %d4,%a3
        lsr.w   #5,%d4
        add.w   %a3,%d4
        add.w   %d6,%d4
        addq.w  #1,%d4                      /* v + span * 33/32 + 1 (quantisation margin) */
        add.w   %d0,%d0
        cmp.w   %d0,%d4
        bgt.s   .Lmasked2                   /* would leave the 2H stored texels */
        lsr.w   #1,%d0
        move.w  r_tsh,%d0
        lsl.w   %d0,%d6
        adda.w  %d6,%a1                     /* a1 = first texel */
        move.l  %d3,%d6
        lsr.l   #6,%d6                      /* zpp * 1024 -> scaler level */
        lea     scal_q,%a0
        moveq   #0,%d0
        move.b  0(%a0,%d6.w),%d0
        add.w   %d0,%d0
        add.w   %d0,%d0
        move.l  r_scal,%a0
        move.l  0(%a0,%d0.w),%a3            /* end of the scaler */
        move.w  %d7,%d0
        add.w   %d0,%d0
        move.w  %d0,%d6
        add.w   %d0,%d0
        add.w   %d6,%d0                     /* n * 6 */
        suba.w  %d0,%a3
        add.w   %d5,%d5
        add.w   %d5,%d5
        lea     -4(%a2,%d5.w),%a0           /* a0 = top - 4 */
        jsr     (%a3)
        movem.l (%sp)+,%d0-%d3/%d6-%d7/%a3
        rts
.Lmasked2:
        lsr.w   #1,%d0
.Lmasked:
        add.l   %d1,%d2                     /* v of the bottom row; the core steps up by -zpp */
        neg.l   %d3
        move.w  %d0,%d6                     /* hmask (kept in d5 by the core) */
        add.w   %d5,%d5
        add.w   %d5,%d5
        lea     -4(%a2,%d5.w),%a0
        move.w  %d6,%d5
        move.l  %d3,%d4
        swap    %d3                         /* d3.w step int, d4.w step frac */
        move.l  %d2,%d1
        swap    %d1                         /* d1.w v int, d2.w v frac */
        move.w  %d7,%d6
        mulu.w  r_tmk_sz,%d6
        move.l  r_tmk_end,%a3
        suba.w  %d6,%a3
        jsr     (%a3)
        movem.l (%sp)+,%d0-%d3/%d6-%d7/%a3
        rts

/* masked cores: entry = end - n*size, bottom-up from k = n; d1/d2 v, d3/d4 step, d5 hmask, a0 = top - 4, a1 texels */
        .set    k,NS_B
        .rept   NS_B
        move.w  %d1,%d6
        and.w   %d5,%d6
        move.b  0(%a1,%d6.w),k*4(%a0)
        add.w   %d4,%d2
        addx.w  %d3,%d1
        .set    k,k-1
        .endr
        .globl  tmkb_end
tmkb_end:
        rts
        .set    k,VH_MAX
        .rept   VH_MAX
        move.w  %d1,%d6
        and.w   %d5,%d6
        add.w   %d6,%d6
        move.w  0(%a1,%d6.w),k*4(%a0)
        add.w   %d4,%d2
        addx.w  %d3,%d1
        .set    k,k-1
        .endr
        .globl  tmkw_end
tmkw_end:
        rts
