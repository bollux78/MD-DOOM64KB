/* MC68000: a0 dest, a1 source, a2 map, d0 frac, d1 step, d2 count-1.
 * Clobbers a0,d0-d7,cc,memory; preserves a1/a2 and all other address regs.
 * Build unconditionally; linker GC drops the kernel when unused. */
.text
.align 2
.globl R20_RegColumn
.type R20_RegColumn,@function
R20_RegColumn:
 move.w %d0,%d3
 lsl.w #7,%d3
 rol.w #7,%d0
 and.w #127,%d0
 move.w %d1,%d4
 lsl.w #7,%d4
 rol.w #7,%d1
 and.w #127,%d1
 moveq #127,%d5
1:
 moveq #0,%d6
 move.b (%a1,%d0.w),%d6
 add.w %d6,%d6
 move.w (%a2,%d6.w),(%a0)
 lea 76(%a0),%a0
 add.w %d4,%d3
 addx.w %d1,%d0
 and.w %d5,%d0
 dbra %d2,1b
 rts
.size R20_RegColumn,.-R20_RegColumn
