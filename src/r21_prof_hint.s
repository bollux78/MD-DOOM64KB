/* R21 N7b: HInt PC sampler. SGDK >= 1.80 points the HInt vector at
 * hintCaller, a JMP to the callback, so on entry (sp) = SR and 2(sp) = PC
 * of the interrupted code. After saving 12 bytes: SR at 12(sp), PC at 14(sp).
 * A frame whose SR does not look like supervisor code with IPL 0..3 is
 * counted in r21_prof_bad (wrong SGDK version / stack layout).
 * Bucket b is a big-endian 16-bit counter at SRAM bytes 32+2b, i.e. CPU
 * addresses 0x200041+4b (hi) and 0x200043+4b (lo). Saturates at 0xFFFF.
 * Built unconditionally; linker GC drops it when DOOM_R21_PROF is off. */
    .equ R21_PROF_BASE,    0x00000200
    .equ R21_PROF_SHIFT,   5
    .equ R21_PROF_BUCKETS, 16368
    .text
    .align 2
    .globl R21_ProfHInt
    .type R21_ProfHInt,@function
R21_ProfHInt:
    movem.l %d0-%d1/%a0,-(%sp)
    move.w  12(%sp),%d1
    and.w   #0x2700,%d1
    sub.w   #0x2000,%d1
    cmp.w   #0x0300,%d1
    bhi.s   9f
    move.l  14(%sp),%d0
    sub.l   #R21_PROF_BASE,%d0
    bcs.s   8f
    lsr.l   #R21_PROF_SHIFT,%d0
    cmp.l   #R21_PROF_BUCKETS,%d0
    bcc.s   8f
    lsl.l   #2,%d0
    movea.l #0x200041,%a0
    adda.l  %d0,%a0
    move.b  (%a0),%d1
    lsl.w   #8,%d1
    move.b  2(%a0),%d1
    addq.w  #1,%d1
    beq.s   7f
    move.b  %d1,2(%a0)
    lsr.w   #8,%d1
    move.b  %d1,(%a0)
7:  addq.l  #1,r21_prof_samples
    movem.l (%sp)+,%d0-%d1/%a0
    rte
8:  addq.l  #1,r21_prof_out
    bra.s   7b
9:  addq.l  #1,r21_prof_bad
    bra.s   7b
    .size R21_ProfHInt,.-R21_ProfHInt
