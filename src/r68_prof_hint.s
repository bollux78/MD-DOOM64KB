/* R68: HInt PC sampler into the heap ring. Same stack-layout assumption and
 * validation as R21_ProfHInt: SGDK >= 1.80 jumps to this callback from hintCaller,
 * so on entry (sp) = SR and 2(sp) = interrupted PC; after saving 12 bytes they are
 * at 12(sp) and 14(sp). Block layout (r68_block_t, DOOM_R68_RING = 128, ring first):
 *   ring[RING] @0 (words), head @2*RING (word), samples @2*RING+4 (long), bad @2*RING+8 (long).
 * Built unconditionally; the linker drops it when R68 is off. */
    .equ R68_RING,     128
    .equ R68_OFF_HEAD, 2*R68_RING
    .equ R68_OFF_SAMP, 2*R68_RING+4
    .equ R68_OFF_BAD,  2*R68_RING+8
    .text
    .align 2
    .globl R68_HInt
    .type R68_HInt,@function
R68_HInt:
    movem.l %d0-%d1/%a0,-(%sp)
    move.l  r68_ptr,%d0
    beq.s   9f                         /* block not allocated yet */
    movea.l %d0,%a0
    addq.l  #1,R68_OFF_SAMP(%a0)
    move.w  12(%sp),%d1
    and.w   #0x2700,%d1
    sub.w   #0x2000,%d1
    cmp.w   #0x0300,%d1
    bhi.s   8f                         /* not supervisor code with IPL 0..3 */
    move.w  R68_OFF_HEAD(%a0),%d1
    cmp.w   #R68_RING,%d1
    bcc.s   9f                         /* ring full: counted in samples, not stored */
    move.l  14(%sp),%d0
    lsr.l   #3,%d0
    cmp.l   #0xFFFF,%d0
    bls.s   6f
    move.w  #0xFFFF,%d0
6:  add.w   %d1,%d1                    /* byte offset of the slot */
    move.w  %d0,(%a0,%d1.w)
    addq.w  #1,R68_OFF_HEAD(%a0)
9:  movem.l (%sp)+,%d0-%d1/%a0
    rte
8:  addq.l  #1,R68_OFF_BAD(%a0)
    bra.s   9b
    .size R68_HInt,.-R68_HInt
