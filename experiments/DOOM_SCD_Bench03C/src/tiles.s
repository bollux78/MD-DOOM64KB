    .text
    .globl scd_generate_tiles
/* void scd_generate_tiles(void *dst, unsigned int seed, unsigned int words)
 * words is in 1..65536. Identical machine code runs on both CPUs.
 */
scd_generate_tiles:
    movea.l 4(%sp), %a0
    move.l  8(%sp), %d0
    move.l  12(%sp), %d1
    subq.w  #1, %d1
1:
    rol.w   #3, %d0
    eori.w  #0x5a69, %d0
    addi.w  #0x1113, %d0
    move.w  %d0, (%a0)+
    dbra    %d1, 1b
    rts
