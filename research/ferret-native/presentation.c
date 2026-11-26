/* Independent VDP presentation and compact texture expansion.
 * Logical framebuffer: 160x72 bytes, each byte holds two 4-bit pixels.
 * Display mode: 320x144, vertical duplication, 40x18 VDP tiles.
 * Tile layout is row-major; this is a proposed target backend, not yet an
 * exact recreation of the Alpha2 DMA ordering.
 */
#include <stdint.h>
#include <stddef.h>
#define W 160u
#define H 72u
#define TILE_BYTES 23040u
size_t fr_tiles(const uint8_t *fb,uint8_t *tiles,size_t cap){
    if(!fb||!tiles||cap<TILE_BYTES)return 0;
#ifdef __m68k__
    if(((uintptr_t)fb|(uintptr_t)tiles)&1u){ /* unaligned caller: portable byte path */
#else
    { /* host reference: byte order and alignment independent */
#endif
        for(unsigned ty=0;ty<18;ty++)for(unsigned tx=0;tx<40;tx++){
            uint8_t *dst=tiles+(ty*40+tx)*32;
            for(unsigned ry=0;ry<8;ry++){unsigned y=ty*4+ry/2;
                for(unsigned k=0;k<4;k++){unsigned x=tx*4+k;dst[ry*4+k]=fb[(x/2)*144+(x&1)+2*y];}}
        }
        return TILE_BYTES;
    }
#ifdef __m68k__
    /* Same mapping as the byte path. For tile column tx the four bytes of a tile row come from
     * fb[(2tx)*144+2y .. +1] and fb[(2tx+1)*144+2y .. +1], i.e. two aligned 16-bit words, and each
     * logical row is shown twice. 68000: 2 word reads + 2 long writes per tile row. */
    uint32_t *dst=(uint32_t *)tiles;
    for(unsigned ty=0;ty<18;ty++){
        const uint16_t *c0=(const uint16_t *)(fb+ty*8);   /* 2*y with y=ty*4 */
        for(unsigned tx=0;tx<40;tx++){
            const uint16_t *a=c0,*b=(const uint16_t *)((const uint8_t *)c0+144);
            for(unsigned r=0;r<4;r++){
                uint32_t v=((uint32_t)a[r]<<16)|b[r];
                *dst++=v;*dst++=v;
            }
            c0=(const uint16_t *)((const uint8_t *)c0+288);
        }
        (void)0;
    }
    return TILE_BYTES;
#endif
}
/* 4-bit packed source -> duplicated-nibble texture bytes. Each texture
 * remains in ROM as 4096 bytes; expand a working texture on demand.
 * Three guard copies used only by the reference rasterizer, not stored in ROM.
 */
size_t fr_expand_texture(const uint8_t *src,size_t n,uint8_t *dst,size_t cap){
    if(!src||!dst||n!=4096||cap<24576)return 0;
    for(unsigned i=0;i<4096;i++){
        uint8_t a=(uint8_t)((src[i]>>4)*17),b=(uint8_t)((src[i]&15)*17);
        for(unsigned j=0;j<3;j++){dst[j*8192+2*i]=a;dst[j*8192+2*i+1]=b;}
    }
    return 24576;
}
