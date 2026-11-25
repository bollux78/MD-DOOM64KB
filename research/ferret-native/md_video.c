/* Mega Drive VDP/SRAM16 diagnostic backend.
 * Pure command planner is tested on host; MMIO functions only on m68k.
 * SRAM mapping is a cartridge-specific prerequisite, not enabled here.
 * No assumption of fitting a full 23 KiB DMA into a single VBlank.
 */
#include <stdint.h>
#include <stddef.h>
#define TILE_BYTES 23040u
#define VRAM_TILES 0x20u
#define VRAM_PLANE_A 0xc000u
#define SRAM16_STAGE 0x20a600u
typedef struct { uint16_t regs[5]; uint32_t command; } FRDma;
int fr_dma_plan(uint32_t src,uint32_t dst,uint32_t bytes,FRDma *p){
    if(!p||!bytes||(src|dst|bytes)&1u||src>=0x1000000u||bytes>0x1000000u-src||dst>=65536u||bytes>65536u-dst||bytes>131070u)return -1;
    /* VDP cannot cross a 128 KiB source boundary in a single transfer. */
    if((src>>17)!=((src+bytes-1)>>17))return -2;
    uint32_t w=src>>1,n=bytes>>1;
    p->regs[0]=(uint16_t)(0x9300u|(n&255u));
    p->regs[1]=(uint16_t)(0x9400u|(n>>8));
    p->regs[2]=(uint16_t)(0x9500u|(w&255u));
    p->regs[3]=(uint16_t)(0x9600u|((w>>8)&255u));
    p->regs[4]=(uint16_t)(0x9700u|((w>>16)&127u));
    p->command=0x40000080u|((dst&0x3fffu)<<16)|((dst&0xc000u)>>14);
    return 0;
}
size_t fr_plane_map(uint16_t *map,size_t cap,uint16_t base,uint16_t palette){
    if(!map||cap<64u*32u||base==0||base+719u>2047u||palette>3)return 0;
    for(unsigned i=0;i<64u*32u;i++)map[i]=0;
    for(unsigned y=0;y<18;y++)for(unsigned x=0;x<40;x++)map[(y+5)*64+x]=(uint16_t)((palette<<13)|(base+y*40+x));
    return 64u*32u;
}
#ifdef __m68k__
#define VDP_CTRL16 (*(volatile uint16_t *)0xc00004ul)
#define VDP_CTRL32 (*(volatile uint32_t *)0xc00004ul)
#define VDP_DATA16 (*(volatile uint16_t *)0xc00000ul)
static int wait_dma(void){
    for(uint32_t n=0;n<1000000u;n++)if(!(VDP_CTRL16&2u))return 0;
    return -1;
}
/* Caller owns interrupt exclusion, VDP register 1 DMA enable, SRAM mapping,
 * and display timing. Diagnostic transfer intended with display disabled.
 */
int fr_md_dma(uint32_t src,uint16_t dst,uint32_t bytes){
    FRDma p;int r=fr_dma_plan(src,dst,bytes,&p);if(r)return r;
    if(wait_dma())return -3;
    VDP_CTRL16=0x8f02;
    for(unsigned i=0;i<5;i++)VDP_CTRL16=p.regs[i];
    VDP_CTRL32=p.command;
    return wait_dma();
}
int fr_md_publish_sram16(void){return fr_md_dma(SRAM16_STAGE,VRAM_TILES,TILE_BYTES);}
#endif
