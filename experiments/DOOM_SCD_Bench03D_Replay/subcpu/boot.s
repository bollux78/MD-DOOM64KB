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
    clr.w   0xff8026         /* acknowledged swap */
    clr.w   0xff8028         /* completed frame */
    moveq   #0, %d1
    moveq   #4, %d4          /* 1M, RET = 0 */
    move.w  %d4, 0xff8002
    move.w  #0x5343, 0xff8020
loop:
    move.w  0xff8010, %d2
    cmp.w   %d1, %d2
    beq.s   loop
    move.w  %d2, %d5
    moveq   #0, %d0
    cmpi.w  #8, %d5
    shi     %d0
    eori.b  #0xff, %d0     /* verify flag for IDs 1 through 8 */
    moveq   #0, %d1
    move.w  %d5, %d1
    subq.w  #1, %d1
    andi.w  #7, %d1
    move.w  0xff800c, %d6
    move.l  %d0, -(%sp)
    move.l  #0x000c0020, -(%sp)
    move.l  %d1, -(%sp)
    jsr     scd_replay
    lea     12(%sp), %sp
    move.w  %d0, 0xff802a
    move.w  0xff800c, %d0
    sub.w   %d6, %d0
    andi.w  #0x0fff, %d0
    move.w  %d0, 0xff8024
    move.w  %d5, %d2
    move.w  %d2, 0x000c0000
    move.w  %d2, 0xff8028
wait_swap:
    btst    #1, 0xff8003     /* Main requests swap by clearing DMNA */
    beq.s   wait_swap
    eori.w  #1, %d4         /* Sub toggles RET to change both banks */
    move.w  %d4, 0xff8002
    move.w  %d2, 0xff8026
    move.w  %d2, %d1
    bra.s   loop
fault:
    move.w  #0xdead, 0xff8020
    bra.s   fault
