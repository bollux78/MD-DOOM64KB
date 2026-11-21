/* Row-doubling H-interrupt (row-doubled modes).
   hint_a: before the view; first scroll value, then arms hint_b (one SYS call per frame).
   hint_b: every call recomputes the row from the V counter, so a late or lost H-int (DMA, masked
           interrupts) cannot shift the rest of the view; after the last row it turns the H-int off.
   The VBlank (main.c) resets VSRAM, re-arms hint_a and turns the H-int back on.          */
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
        lsr.w   #1,%d0
        neg.w   %d0                         /* v = -((L - VTOP + 1) >> 1) */
        move.w  hint_r1on,0xC00004          /* display on (the VBlank turned it off for lines 0..15) */
        move.l  #0x40000010,0xC00004
        move.w  %d0,0xC00000
        movem.l %d1/%a0-%a1,-(%sp)
        pea     hint_b
        jsr     SYS_setHIntCallback
        addq.l  #4,%sp
        movem.l (%sp)+,%d1/%a0-%a1
9:      move.l  (%sp)+,%d0
        rte

hint_b:
        move.l  %d0,-(%sp)
        moveq   #0,%d0
        move.b  0xC00008,%d0
        addq.w  #1,%d0                      /* L = next line */
        cmpi.w  #224,%d0
        bcc.s   8f                          /* in the VBlank: nothing to do */
        subi.w  #VTOP-1,%d0
        bmi.s   8f
        lsr.w   #1,%d0
        cmpi.w  #VIEW_H,%d0
        bcs.s   1f
        moveq   #VIEW_H,%d0
        move.w  #0x8004,0xC00004            /* view done: H-int off until the VBlank */
1:      neg.w   %d0
        move.l  #0x40000010,0xC00004
        move.w  %d0,0xC00000
8:      move.l  (%sp)+,%d0
        rte
