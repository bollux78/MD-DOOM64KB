/* Row-doubling H-interrupt (row-doubled modes), in two phases so the 72 per-frame writes cost
   ~180 cycles each instead of ~260 for the C version:
   hint_a: before the view; reads the V counter once, writes the first scroll value, arms hint_b.
   hint_b:
        /* recomputed from the V counter every time: a late or lost H-int (DMA, masked interrupts)
           can no longer shift the rest of the view by a row */
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

        .bss
        .even
        .globl  hint_v
hint_v: .skip 2
