/* Row-doubling H-interrupt (row-doubled modes), in two phases so the 72 per-frame writes cost
   ~180 cycles each instead of ~260 for the C version:
   hint_a: before the view; reads the V counter once, writes the first scroll value, arms hint_b.
   hint_b: one scroll step per call (every 2 lines); after the last row turns the H-int off.
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
        move.l  #0x40000010,0xC00004
        move.w  %d0,0xC00000
        subq.w  #1,%d0
        move.w  %d0,hint_v
        movem.l %d1/%a0-%a1,-(%sp)
        pea     hint_b
        jsr     SYS_setHIntCallback
        addq.l  #4,%sp
        movem.l (%sp)+,%d1/%a0-%a1
9:      move.l  (%sp)+,%d0
        rte

hint_b:
        move.l  #0x40000010,0xC00004
        move.w  hint_v,0xC00000
        subq.w  #1,hint_v
        cmpi.w  #-VIEW_H-1,hint_v
        ble.s   1f
        rte
1:      move.w  #0x8004,0xC00004            /* view done: H-int off until the VBlank */
        rte

        .bss
        .even
        .globl  hint_v
hint_v: .skip 2
