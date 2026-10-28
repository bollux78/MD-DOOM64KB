/* R60 P1: Pair-V Fast wall column, composed LUT path only.
 * a0 dst, a1 src, a2 LUT, d0.w phase, d1.w step, d2.w count, d3.w odd.
 * Clobbers d0-d7, a0 and condition codes. */
.text
.align 2
.globl R60_WallColumn
.type R60_WallColumn,@function
R60_WallColumn:
 move.w %d0,%d4
 lsl.w #7,%d4
 lsr.w #8,%d0
 lsr.w #1,%d0
 move.w %d1,%d6
 lsl.w #7,%d6
 lsr.w #8,%d1
 lsr.w #1,%d1
 moveq #127,%d7
 moveq #0,%d5
 tst.w %d3
 beq.s 2f
 move.b (%a1,%d0.w),%d5
 move.b (%a2,%d5.w),%d5
 move.b (%a0),%d3
 and.b #0xf0,%d3
 or.b %d5,%d3
 move.b %d3,(%a0)
 lea 152(%a0),%a0
 add.w %d6,%d4
 addx.w %d1,%d0
 and.w %d7,%d0
 subq.w #1,%d2
 beq.s 9f
2:
 moveq #0,%d3
 lsr.w #1,%d2
 scs %d7
 swap %d7
 move.w #127,%d7
 subq.w #1,%d2
 bmi.s 4f
3:
 move.b (%a1,%d0.w),%d5
 add.w %d6,%d4
 addx.w %d1,%d0
 and.w %d7,%d0
 move.b (%a1,%d0.w),%d3
 add.w %d6,%d4
 addx.w %d1,%d0
 and.w %d7,%d0
 move.b (%a2,%d5.w),%d5
 move.b (%a2,%d3.w),%d3
 lsl.b #4,%d5
 or.b %d3,%d5
 move.b %d5,(%a0)
 lea 152(%a0),%a0
 dbra %d2,3b
4:
 swap %d7
 tst.b %d7
 beq.s 9f
 move.b (%a1,%d0.w),%d5
 move.b (%a2,%d5.w),%d5
 lsl.b #4,%d5
 move.b (%a0),%d3
 and.b #0x0f,%d3
 or.b %d5,%d3
 move.b %d3,(%a0)
9:
 rts
.size R60_WallColumn,.-R60_WallColumn
