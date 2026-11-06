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
    clr.w   0xff8024         /* command result */
    clr.w   0xff8026         /* acknowledged sequence */
    move.w  #0, %d1
    move.w  #1, 0xff8002    /* start in 2M mode with Word RAM on Main */
    move.w  #0x5343, 0xff8020
loop:
    move.w  0xff8010, %d2
    cmp.w   %d1, %d2
    beq.s   loop
wait_word_ram:
    btst    #1, 0xff8003    /* wait for DMNA before touching Word RAM */
    beq.s   wait_word_ram
    move.w  0xff8012, %d3
    move.w  0xff800c, %d4
    move.l  #8192, -(%sp)
    move.l  %d3, -(%sp)
    move.l  #0x00080000, -(%sp)
    jsr     scd_generate_tiles
    lea     12(%sp), %sp
    move.w  0xff800c, %d3
    sub.w   %d4, %d3
    andi.w  #0x0fff, %d3
    move.w  %d3, 0xff8024  /* Sub generation time */
    move.w  #1, 0xff8002   /* return Word RAM before publishing ACK */
    move.w  %d2, 0xff8026
    move.w  %d2, %d1
    bra.s   loop
fault:
    move.w  #0xdead, 0xff8020
    bra.s   fault
