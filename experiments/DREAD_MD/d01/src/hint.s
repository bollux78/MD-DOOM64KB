/* Row-doubling H-interrupt (row-doubled modes).
   hint_a: before the view; places the first row from the V counter, turns the display on, arms hint_b.
   hint_b: V-counter lookup by default; arithmetic and minimal variants for A/B tests.
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

/* Sample the actual V counter to recover after delayed interrupts. The 512-byte table
   starts just 24 bytes from the indexed instruction, fitting the 68000 d8(PC,D0)
   displacement. The index can span the entire table. Stop at the bottom of the view.
   DREAD_HINT_MINIMAL retains the original incremental handler as a test control. */
#if defined(DREAD_HINT_MINIMAL)
hint_b:
        move.l  #0x40000010,0xC00004
        subq.w  #1,hint_v
        move.w  hint_v,0xC00000
        cmpi.w  #-VIEW_H,hint_v
        beq.s   1f
        rte
1:      move.w  #0x8004,0xC00004
        rte

#elif defined(DREAD_HINT_ROBUST)
hint_b:
        move.l  %d0,-(%sp)
        moveq   #0,%d0
        move.b  0xC00008,%d0
        addq.w  #1,%d0
        cmpi.w  #224,%d0
        bcc.s   8f
        subi.w  #VTOP-1,%d0
        bmi.s   8f
        lsr.w   #1,%d0
        cmpi.w  #VIEW_H,%d0
        bcs.s   1f
        moveq   #VIEW_H,%d0
        move.w  #0x8004,0xC00004
1:      neg.w   %d0
        move.l  #0x40000010,0xC00004
        move.w  %d0,0xC00000
8:      move.l  (%sp)+,%d0
        rte
#else
hint_b:
        move.l  %d0,-(%sp)
        moveq   #0,%d0
        move.b  0xC00008,%d0
        add.w   %d0,%d0
        move.l  #0x40000010,0xC00004
        move.w  hint_tab(%pc,%d0.w),0xC00000
        cmpi.w  #2*(VTOP+2*VIEW_H-2),%d0
        bcs.s   1f
        move.w  #0x8004,0xC00004
1:      move.l  (%sp)+,%d0
        rte

        .even
hint_tab:
        .word 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
        .word -1,-1,-2,-2,-3,-3,-4,-4,-5,-5,-6,-6,-7,-7,-8,-8
        .word -9,-9,-10,-10,-11,-11,-12,-12,-13,-13,-14,-14,-15,-15,-16,-16
        .word -17,-17,-18,-18,-19,-19,-20,-20,-21,-21,-22,-22,-23,-23,-24,-24
        .word -25,-25,-26,-26,-27,-27,-28,-28,-29,-29,-30,-30,-31,-31,-32,-32
        .word -33,-33,-34,-34,-35,-35,-36,-36,-37,-37,-38,-38,-39,-39,-40,-40
        .word -41,-41,-42,-42,-43,-43,-44,-44,-45,-45,-46,-46,-47,-47,-48,-48
        .word -49,-49,-50,-50,-51,-51,-52,-52,-53,-53,-54,-54,-55,-55,-56,-56
        .word -57,-57,-58,-58,-59,-59,-60,-60,-61,-61,-62,-62,-63,-63,-64,-64
        .word -65,-65,-66,-66,-67,-67,-68,-68,-69,-69,-70,-70,-71,-71,-72,-72
        .word -72,-72,-72,-72,-72,-72,-72,-72,-72,-72,-72,-72,-72,-72,-72,-72
        .word -72,-72,-72,-72,-72,-72,-72,-72,-72,-72,-72,-72,-72,-72,-72,-72
        .word -72,-72,-72,-72,-72,-72,-72,-72,-72,-72,-72,-72,-72,-72,-72,-72
        .word -72,-72,-72,-72,-72,-72,-72,-72,-72,-72,-72,-72,-72,-72,-72,-72
        .word -72,-72,-72,-72,-72,-72,-72,-72,-72,-72,-72,-72,-72,-72,-72,-72
        .word -72,-72,-72,-72,-72,-72,-72,-72,-72,-72,-72,-72,-72,-72,-72,-72
#endif

        .bss
        .even
hint_v: .space  2
