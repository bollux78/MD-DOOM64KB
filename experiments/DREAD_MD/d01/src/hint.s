/* Row-doubling H-interrupt (row-doubled modes).
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

/* hint_b: one H-int every 2 lines (counter 1), each one row further down: no registers, no V counter
   (hint_a placed the first row from the V counter; nothing delays the H-int inside the view since the
   VBlank DMA ends above it).  After the last row the H-int is turned off until the VBlank. */
hint_b:
        move.l  #0x40000010,0xC00004
        subq.w  #1,hint_v
        move.w  hint_v,0xC00000
        cmpi.w  #-VIEW_H,hint_v
        beq.s   1f
        rte
1:      move.w  #0x8004,0xC00004
        rte

        .bss
        .even
hint_v: .space  2
