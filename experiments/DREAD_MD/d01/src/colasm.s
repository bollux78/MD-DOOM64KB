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
#define J_UP 64
#define J_LO 88
#define J_CPAL 112
#define J_FPAL 116
#define PT_VT0 16                           /* Part: v at the part's top edge row (texels, in [0,H)) */
#define PT_EOFF 18                          /* Part: ColRec offset of the raw top-edge row (0 = yc, 6 = ybf) */
#define J_TSH 122                           /* log2 of an upper bound of the texels per row (this seg) */
#define REC 12                              /* ColRec size (J_YC = base of the records) */
#define PT_VLIM 20                          /* Part: last texel the scalers may reach (stored - 2) */

seg_columns:
        movem.l %d2-%d7/%a2-%a6,-(%sp)
        move.l  48(%sp),%a6
        move.l  r_clipbuf,%a5
        lea     128(%a5),%a5                /* a5 = clip + 128: ceiling at CEIL_D, floor at FLOOR_D (8-bit displacements) */
        move.w  J_C0(%a6),%d7
        bra     .Lseta3
.Lcol:
        cmp.w   J_XE(%a6),%d7
        bge     .Ldone
#ifndef DREAD_OPT_COLPTR_INCREMENTAL
        moveq   #0,%d0
        move.b  CEIL_D(%a5,%d7.w),%d0       /* top */
        moveq   #0,%d1
        move.b  FLOOR_D(%a5,%d7.w),%d1      /* bot */
#endif
        move.w  %d7,%d6
        add.w   %d6,%d6
        lea     r_colofs,%a0
        move.l  J_FB(%a6),%a2
        adda.w  0(%a0,%d6.w),%a2            /* column pointer */
#ifdef DREAD_OPT_COLPTR_INCREMENTAL
.Lcol_ptrready:                              /* adjacent row columns reuse a2 only */
        /* Every column MUST refresh clipping and d6 (sky offset index).
         * Previous A1 skipped these and displayed corrupt/black tiles. */
        moveq   #0,%d0
        move.b  CEIL_D(%a5,%d7.w),%d0
        moveq   #0,%d1
        move.b  FLOOR_D(%a5,%d7.w),%d1
        move.w  %d7,%d6
        add.w   %d6,%d6
#endif
        movem.w (%a3),%d2-%d3               /* raw yc, yf of this column (ColRec) */
        cmp.w   %d0,%d2                     /* yc = clamp(yc, top, bot) */
        bge.s   1f
        move.w  %d0,%d2
1:      cmp.w   %d1,%d2
        ble.s   1f
        move.w  %d1,%d2
1:      cmp.w   %d2,%d3                     /* yf = clamp(yf, yc, bot) */
        bge.s   1f
        move.w  %d2,%d3
1:      cmp.w   %d1,%d3
        ble.s   1f
        move.w  %d1,%d3
1:
        move.w  %d2,%d4                     /* ceiling: top .. yc */
        sub.w   %d0,%d4
        ble.s   1f
        btst    #4,J_FLAGS+1(%a6)
        beq.s   2f
        /* sky ceiling: rows top..yc of the sky column of this screen column, through the scalers */
        lea     r_skyoff,%a0
        move.w  0(%a0,%d6.w),%d5
        lea     sky_blob,%a1
        adda.w  %d5,%a1
        move.w  r_ssh,%d4
        move.w  %d0,%d5
        lsr.w   %d4,%d5                     /* sky row of the top (column-doubled: rows are halved) */
        adda.w  %d5,%a1
        move.w  %d0,%d5
        add.w   %d5,%d5
        add.w   %d5,%d5
        lea     -4(%a2,%d5.w),%a0
        move.w  %d2,%d4
        sub.w   %d0,%d4                     /* n */
        add.w   %d4,%d4
        move.w  %d4,%d5
        add.w   %d4,%d4
        add.w   %d5,%d4                     /* n * 6 */
        move.w  r_ssh,%d5
        lsl.w   %d5,%d4
        move.l  r_skyend,%a4
        suba.w  %d4,%a4
        jsr     (%a4)
        bra.s   1f
2:      move.w  %d0,%d5
        add.w   %d5,%d5                     /* fill inline: a0 = column + y0*4 - 4, jump into the core */
        add.w   %d5,%d5
        lea     -4(%a2,%d5.w),%a0
        move.w  J_CPAL+2(%a6),%d5
        add.w   %d4,%d4
        add.w   %d4,%d4
        move.l  r_fill_end,%a1
        suba.w  %d4,%a1
        jsr     (%a1)
1:      move.w  %d1,%d4                     /* floor: yf .. bot */
        sub.w   %d3,%d4
        ble.s   1f
        move.w  %d3,%d5
        add.w   %d5,%d5                     /* fill inline: a0 = column + y0*4 - 4, jump into the core */
        add.w   %d5,%d5
        lea     -4(%a2,%d5.w),%a0
        move.w  J_FPAL+2(%a6),%d5
        add.w   %d4,%d4
        add.w   %d4,%d4
        move.l  r_fill_end,%a1
        suba.w  %d4,%a1
        jsr     (%a1)
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
        bsr     tex_fast
.Lclose:
        clr.b   CEIL_D(%a5,%d7.w)
        clr.b   FLOOR_D(%a5,%d7.w)
        move.l  r_nxt,%a0
        move.w  %d7,%d4
        addq.w  #1,%d4
        move.b  %d4,0(%a0,%d7.w)
        addq.w  #1,J_CLOSED(%a6)
        bra.s   .Lnext
.Lportal:
        move.w  %d2,%d0                     /* ntop = yc, nbot = yf */
        move.w  %d3,%d1
        btst    #2,%d4
        beq.s   .Lnoup
        move.w  4(%a3),%d5                  /* ybc = clamp(ybc, yc, yf) */
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
        movem.w %d0-%d1/%d3,-(%sp)
        bsr     tex_fast
        movem.w (%sp)+,%d0-%d1/%d3
.Lnoup:
        btst    #3,J_FLAGS+1(%a6)
        beq.s   .Lnolo
        move.w  6(%a3),%d5                  /* ybf = clamp(ybf, ntop, yf) */
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
        movem.w %d0-%d1,-(%sp)
        bsr     tex_fast
        movem.w (%sp)+,%d0-%d1
.Lnolo:
        cmp.w   %d1,%d0
        bge     .Lclose
        move.b  %d0,CEIL_D(%a5,%d7.w)
        move.b  %d1,FLOOR_D(%a5,%d7.w)
.Lnext:
        addq.w  #1,%d7                      /* c = find_open(c + 1), path halving */
        move.l  r_nxt,%a0
        moveq   #0,%d4
        move.b  0(%a0,%d7.w),%d4
        cmp.w   %d4,%d7
        bne.s   .Lskip
        lea     REC(%a3),%a3                /* next column, next record */
#ifdef DREAD_OPT_COLPTR_INCREMENTAL
        /* Fast H40/H32 row-doubled path.  A consecutive column starts one
         * byte later, except at the 4-byte tile-column boundary (288-3=285).
         * Keep the original r_colofs lookup for column-doubled modes and
         * jumps across already-closed columns. Pixel math is unchanged. */
        cmp.w   J_XE(%a6),%d7
        bge     .Ldone
        cmpi.w  #1,r_colb
        bne     .Lcol
        move.w  %d7,%d4
        andi.w  #3,%d4
        beq.s   .Lcolptr_wrap
        addq.l  #1,%a2
        bra     .Lcol_ptrready
.Lcolptr_wrap:
        adda.w  #285,%a2
        bra     .Lcol_ptrready
#else
        bra     .Lcol
#endif
.Lskip:
        move.b  0(%a0,%d4.w),%d5
        move.b  %d5,0(%a0,%d7.w)
        moveq   #0,%d7
        move.b  %d5,%d7
        moveq   #0,%d4
        move.b  0(%a0,%d7.w),%d4
        cmp.w   %d4,%d7
        bne.s   .Lskip
.Lseta3:                                    /* a3 = &rec[c] (12 bytes per column) */
        move.w  %d7,%d4
        add.w   %d4,%d4
        add.w   %d7,%d4
        add.w   %d4,%d4
        add.w   %d4,%d4
        move.l  J_YC(%a6),%a3
        adda.w  %d4,%a3
        bra     .Lcol
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

/* Exact texture origin and wrap decision, matching d4f9f4b's framebuffer.
 * Keep the sequential column records and return directly through the scaler.
 * a3 is the ColRec, a4 is Part, d5 is top row, d4 is span length. */
tex_fast:
        moveq   #0,%d6
        move.w  8(%a3),%d6                  /* u from this column's sequential record */
        move.w  10(%a3),%d3                 /* zq, same 16.16 calculation as d4f9f4b */
        and.w   4(%a4),%d6                  /* & wmask */
#ifdef DREAD_EPISODE
        lsl.w   #2,%d6
        movea.l (%a4),%a1
        movea.l 0(%a1,%d6.w),%a1            /* shared column */
#else
        move.w  6(%a4),%d1
        lsl.l   %d1,%d6                     /* << hs2 */
        move.l  (%a4),%a1
        adda.l  %d6,%a1                     /* a1 = texture column */
#endif
        move.w  r_horizon,%d1               /* v top = vbase - zq * (HORIZON - y0) * 64 */
        sub.w   %d5,%d1
        muls.w  %d3,%d1
        lsl.l   #6,%d1
        move.l  12(%a4),%d2
        sub.l   %d1,%d2                     /* d2 = v of the top row (16.16) */
#ifdef DREAD_EPISODE
        move.w  6(%a4),%d0                  /* episode: stored texels per column */
        swap    %d0
#endif
        move.w  8(%a4),%d0                  /* hmask */
        add.w   %d5,%d5
        add.w   %d5,%d5
        lea     -4(%a2,%d5.w),%a0           /* a0 = top - 4 */
        move.w  %d4,%a4                     /* a4 = n (the Part is no longer needed) */
#ifdef DREAD_EXACT_SPAN_REFERENCE
        subq.w  #1,%d4
        move.w  %d3,%d1
        mulu.w  %d4,%d1                     /* d1 = span * 1024 */
        cmpi.w  #32767,%d3
        beq     .Ltex_exact_slow                    /* 32 texels per row or more: no scaler */
        move.l  %d2,%d6
        addi.l  #0x8000,%d6                 /* nearest texel: v = -0.3 must not wrap to H - 1 */
        swap    %d6
        and.w   %d0,%d6                     /* d6 = v top, integer, in [0, H) */
        move.l  %d1,%d4
        lsr.l   #8,%d4
        lsr.l   #2,%d4                      /* d4 = span (integer texels) */
        move.w  %d4,%d5
        lsr.w   #5,%d4
        add.w   %d5,%d4
        add.w   %d6,%d4
        addq.w  #1,%d4                      /* v + span * 33/32 + 1 (quantisation margin) */
#ifdef DREAD_EPISODE
        swap    %d0                         /* high word: texels stored per column (H + pad) */
        move.w  %d0,%d5
        swap    %d0
        subq.w  #2,%d5
#else
        move.w  %d0,%d5
        add.w   %d5,%d5
#endif
        cmp.w   %d5,%d4
        bgt     .Ltex_exact_slow                    /* would leave the stored texels */
#else
        cmpi.w  #32767,%d3
        beq     .Ltex_exact_slow
        move.l  %d2,%d6
        addi.l  #0x8000,%d6                 /* identical nearest-texel rounding */
        swap    %d6
        and.w   %d0,%d6
#ifdef DREAD_EPISODE
        swap    %d0
        move.w  %d0,%d5
        swap    %d0
        subq.w  #2,%d5                     /* stored texels - 2 */
#else
        move.w  %d0,%d5
        add.w   %d5,%d5
#endif
        move.w  %a4,%d1
        move.w  J_TSH(%a6),%d4
        lsl.w   %d4,%d1                    /* conservative bound: n * power-of-two step */
        add.w   %d6,%d1
        cmp.w   %d5,%d1
        ble.s   .Ltex_span_ready
        move.w  %a4,%d1                    /* exact original bound when the quick one fails */
        subq.w  #1,%d1
        mulu.w  %d3,%d1
        move.l  %d1,%d4
        lsr.l   #8,%d4
        lsr.l   #2,%d4
        move.w  %d4,%d1
        lsr.w   #5,%d4
        add.w   %d1,%d4
        add.w   %d6,%d4
        addq.w  #1,%d4
        cmp.w   %d5,%d4
        bgt     .Ltex_exact_slow
.Ltex_span_ready:
#endif
        move.w  r_tsh,%d5
        lsl.w   %d5,%d6
        adda.w  %d6,%a1                     /* a1 = first texel */
        move.w  %a4,%d5                     /* n * 6 */
        add.w   %d5,%d5
        move.w  %d5,%d6
        add.w   %d5,%d5
        add.w   %d6,%d5
        move.w  r_ssh,%d6
        lsl.w   %d6,%d5                     /* n * 12 in column-doubled modes (two byte moves per row) */
        lea     scal_q,%a4
        moveq   #0,%d4
        move.b  0(%a4,%d3.w),%d4            /* scaler level */
        add.w   %d4,%d4
        add.w   %d4,%d4
        move.l  r_scal,%a4
        move.l  0(%a4,%d4.w),%a4            /* end of the scaler */
        suba.w  %d5,%a4
        jmp     (%a4)
.Ltex_exact_slow:
#ifndef DREAD_EXACT_SPAN_REFERENCE
        move.w  %a4,%d1
        subq.w  #1,%d1
        mulu.w  %d3,%d1
#endif
        lsl.l   #6,%d1                      /* span 16.16 */
        add.l   %d1,%d2                     /* v of the bottom row; the core steps up by -zpp */
        moveq   #0,%d4
        move.w  %d3,%d4
        lsl.l   #6,%d4
        neg.l   %d4                         /* step = -zpp (16.16) */
        move.w  %d0,%d5                     /* hmask */
        move.l  %d4,%d3
        swap    %d3                         /* d3.w step int, d4.w step frac */
        move.l  %d2,%d1
        swap    %d1                         /* d1.w v int, d2.w v frac */
        move.w  %a4,%d6
        mulu.w  r_tmk_sz,%d6
        move.l  r_tmk_end,%a4
        suba.w  %d6,%a4
        jmp     (%a4)


/* void spr_scale(uint8_t *dst_m4, const uint8_t *src, int16_t n, uint16_t zq): n rows of a sprite post
   through the byte scalers (row k at k*4(dst_m4), texel round((k-1)*z) of src) */
        .globl  spr_scale
spr_scale:
        move.l  %a2,-(%sp)
        movem.l 8(%sp),%a0-%a1
        move.w  18(%sp),%d0                 /* n */
        move.w  22(%sp),%d1                 /* zq */
        lea     scal_q,%a2
        move.b  0(%a2,%d1.w),%d1
        andi.w  #0xFF,%d1
        add.w   %d1,%d1
        add.w   %d1,%d1
        move.l  r_scal,%a2
        move.l  0(%a2,%d1.w),%a2
        add.w   %d0,%d0
        move.w  %d0,%d1
        add.w   %d0,%d0
        add.w   %d1,%d0                     /* n * 6 */
        move.w  r_ssh,%d1
        lsl.w   %d1,%d0                     /* n * 12 in column-doubled modes */
        suba.w  %d0,%a2
        jsr     (%a2)
        move.l  (%sp)+,%a2
        rts

/* masked cores: entry = end - n*size, bottom-up from k = n; d1/d2 v, d3/d4 step, d5 hmask, a0 = top - 4, a1 texels */
        .globl  tmkb_start
tmkb_start:
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
        .globl  tmkw_start
tmkw_start:
        .set    k,VH_MAX
        .rept   VH_MAX
        move.w  %d1,%d6
        and.w   %d5,%d6
        move.b  0(%a1,%d6.w),k*4(%a0)
        move.b  0(%a1,%d6.w),k*4+1(%a0)
        add.w   %d4,%d2
        addx.w  %d3,%d1
        .set    k,k-1
        .endr
        .globl  tmkw_end
tmkw_end:
        rts
