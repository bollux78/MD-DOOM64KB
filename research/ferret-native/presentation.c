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
    for(unsigned ty=0;ty<18;ty++){
        for(unsigned tx=0;tx<40;tx++){
            uint8_t *dst=tiles+(ty*40+tx)*32;
            for(unsigned ry=0;ry<8;ry++){
                unsigned y=ty*4+ry/2;
                for(unsigned k=0;k<4;k++){
                    unsigned x=tx*4+k;
                    dst[ry*4+k]=fb[(x/2)*144+(x&1)+2*y];
                }
            }
        }
    }
    return TILE_BYTES;
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
