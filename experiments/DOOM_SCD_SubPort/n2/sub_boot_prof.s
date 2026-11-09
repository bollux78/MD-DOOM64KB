/* N2 sub vectors with a level-3 (timer) PC-sampling profiler. Bins of 64 bytes over the first
 * 256 KiB of PRG-RAM (4096 x u16 counters, saturating). */
    .section .text.vectors,"ax"
    .globl subcpu_vectors
subcpu_vectors:
    .long 0x00080000, entry
    .rept 25
    .long fault
    .endr
    .long prof_isr              /* vector 27: level 3 autovector (timer) */
    .rept 36
    .long fault
    .endr
entry:
    move.w #0x2700,%sr
    lea __bss_start,%a0
    lea _end,%a1
1:  cmp.l %a1,%a0
    bcc.s 2f
    clr.b (%a0)+
    bra.s 1b
2:  jsr sub_main
3:  bra.s 3b
prof_isr:
    movem.l %d0/%a0,-(%sp)
    move.l 10(%sp),%d0          /* stacked PC (after SR word, under the two saved longs) */
    cmpi.l #0x40000,%d0
    bcc.s 4f
    lsr.l #6,%d0
    add.l %d0,%d0
    lea scd_prof_bins,%a0
    addq.w #1,0(%a0,%d0.l)
    bcc.s 4f
    subq.w #1,0(%a0,%d0.l)
4:  movem.l (%sp)+,%d0/%a0
    rte
fault:
    move.w #0xdead,0xff8020
    bra.s fault
