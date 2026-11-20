/* DREAD-MD D01 column inner loops (68000). Framebuffer column stride = 4 bytes. */
/* */
/* void col_fill(uint8_t *p, uint16_t n, uint16_t c)      12 cycles / pixel */
/* void col_tex(uint8_t *p, uint16_t n, const uint8_t *tc, int32_t vbot, int32_t negstep, uint16_t hmask) */
/*      draws bottom-up: pixel n-1 first with v = vbot, then v += negstep      34 cycles / pixel (14 bytes of code) */
/* Both jump into a fully unrolled sequence (max VIEW_H = 128 rows). */

        .text
        .globl  col_fill
        .globl  col_tex

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
