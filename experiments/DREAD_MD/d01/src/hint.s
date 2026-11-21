/* Row-doubling H-interrupt (row-doubled modes).
   hint_a: before the view; places the first row from the V counter, turns the display on, arms hint_b.
   hint_b: minimal handler, one row per call (see below).
   The VBlank (main.c) resets VSRAM, turns the display off above the view, re-arms hint_a.   */
#define VTOP    16
#define VIEW_H  72
        .text
        .globl  hint_a
        .globl  hint_b
hint_a:
        move.l  %d0,-(%sp)
        moveq   #0,%d0
        move.b  0xC00008,%d0
        addq.w  #1,%d0                      /* L = next line */
        cmpi.w  #224,%d0
        bcc.s   9f                          /* pending H-int raised in the VBlank */
        subi.w  #VTOP-1,%d0
        bmi.s   9f                          /* above the view */
        lsr.w   #1,%d0                      /* row of the next line */
        cmpi.w  #VIEW_H,%d0
        bcs.s   1f
        moveq   #VIEW_H,%d0                 /* (very late: past the view) */
1:      neg.w   %d0                         /* v = -row */
        move.w  hint_r1on,0xC00004          /* display on (the VBlank turned it off for lines 0..15) */
        move.l  #0x40000010,0xC00004
        move.w  %d0,0xC00000
        move.w  %d0,hint_v
        cmpi.w  #-VIEW_H,%d0
        bne.s   2f
        move.w  #0x8004,0xC00004            /* nothing left of the view: H-int off */
        bra.s   9f
2:      movem.l %d1/%a0-%a1,-(%sp)
        pea     hint_b
        jsr     SYS_setHIntCallback
        addq.l  #4,%sp
        movem.l (%sp)+,%d1/%a0-%a1
9:      move.l  (%sp)+,%d0
        rte

/* hint_b: one H-int every 2 lines. The V counter indexes a table of scroll values (one read, no
   branch on the normal path), so a late or lost H-int cannot shift the rest of the view.
   After the last row the H-int is turned off until the VBlank. */
hint_b:
        move.l  %d0,-(%sp)
        moveq   #0,%d0
        move.b  0xC00008,%d0                /* current line */
        add.w   %d0,%d0
        move.l  #0x40000010,0xC00004
        move.w  hint_tab(%pc,%d0.w),%d0     /* -row of the next line */
        move.w  %d0,0xC00000
        cmpi.w  #-VIEW_H,%d0
        beq.s   1f
        move.l  (%sp)+,%d0
        rte
1:      move.w  #0x8004,0xC00004
        move.l  (%sp)+,%d0
        rte
hint_tab:                                   /* line L -> -min(max((L + 1 - (VTOP - 1)) >> 1, 0), VIEW_H) */
        .set    L,0
        .rept   256
        .set    r,(L + 1 - (VTOP - 1)) >> 1
        .if     L + 1 - (VTOP - 1) < 0
        .set    r,0
        .endif
        .if     r > VIEW_H
        .set    r,VIEW_H
        .endif
        .if     L >= 224
        .set    r,0
        .endif
        .word   -r
        .set    L,L+1
        .endr

        .bss
        .even
hint_v: .space  2
