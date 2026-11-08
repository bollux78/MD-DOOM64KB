/* N0 cell image probe, sub side: writes a LINEAR 4bpp bitmap (256x128 px, stride 256 bytes,
 * the hardware's 64x16-cell view layout) at bank offset 0x10000, in both 1M banks.
 * Same swap protocol as FrameDelivery (request id echoed in bank word 0, $A12018 never DMNA). */
    .text
    .globl subcpu_vectors
subcpu_vectors:
    .long 0x00080000, entry
    .rept 62
    .long fault
    .endr
entry:
    move.w #0x2700,%sr
    clr.w 0xff8026
    move.w #4,%d4
    move.w %d4,0xff8002
    bsr.s fill
    move.w #0x5343,0xff8020
    moveq #0,%d2
1:
    move.w 0xff8018,%d0
    cmp.w %d2,%d0
    beq.s 1b
    move.w %d0,%d2
    move.w %d2,0x0c0000
    eori.w #1,%d4
    move.w %d4,0xff8002
    move.w %d2,0xff8026
    cmpi.w #1,%d2
    bne.s 1b
    bsr.s fill
    bra.s 1b
/* byte(x,y) = (x*5 + y*3 + (y>>3)) & 0xff, x = 0..127 bytes, y = 0..127 lines */
fill:
    lea 0x0d0000,%a1
    moveq #0,%d1              /* y */
2:
    move.w %d1,%d3
    mulu.w #3,%d3
    move.w %d1,%d5
    lsr.w #3,%d5
    add.w %d5,%d3             /* y*3 + y>>3 */
    moveq #0,%d0              /* x */
    movea.l %a1,%a0
3:
    move.w %d0,%d5
    mulu.w #5,%d5
    add.w %d3,%d5
    move.b %d5,(%a0)+
    addq.w #1,%d0
    cmpi.w #128,%d0
    bne.s 3b
    lea 256(%a1),%a1
    addq.w #1,%d1
    cmpi.w #128,%d1
    bne.s 2b
    rts
fault:
    move.w #0xdead,0xff8020
    bra.s fault
