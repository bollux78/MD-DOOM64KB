/* Sega CD Sub-CPU 68000 code, loaded at PRG RAM address 0.
   ROM vectors occupy the first 0x100 bytes. */
    .section .text
    .globl subcpu_vectors
subcpu_vectors:
    .long 0x00080000, entry
    .rept 62
    .long fault
    .endr

entry:
    move.w  #0x2700, %sr
    clr.w   0xff8022         /* heartbeat */
    clr.w   0xff8024         /* command result */
    clr.w   0xff8026         /* acknowledged sequence */
    move.w  #0, %d0
    move.w  #0, %d1
    move.w  #0x5343, 0xff8020 /* publish readiness last */
loop:
    addq.w  #1, %d0
    move.w  %d0, 0xff8022
    move.w  0xff8010, %d2 /* command sequence */
    cmp.w   %d1, %d2
    beq.s   loop
    move.w  %d2, %d1
    move.w  0xff8012, %d3 /* payload */
    eori.w  #0x5a5a, %d3
    move.w  %d3, 0xff8024
    move.w  %d1, 0xff8026 /* ACK written last */
    bra.s   loop
fault:
    move.w  #0xdead, 0xff8020
    bra.s   fault
