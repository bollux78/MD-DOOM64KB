#include "compiler.h"
#include "r22_blocklinks.h"
#if defined(DOOM_R22_SRAM_BLOCKLINKS)
#include "i_system.h"
uint16_t r22_block_cells;
void R22_BlockInit(uint16_t w,uint16_t h){
    uint32_t cells=(uint32_t)w*h;
    if(!w||!h||cells>R22_SRAM_CAPACITY/4u)I_Error("SRAM BLOCKMAP TOO LARGE");
    uint16_t bytes=(uint16_t)(cells*4u),pos[16],count=1;
    uint8_t saved[16];pos[0]=0;
    for(uint16_t bit=1;bit<bytes;bit<<=1)pos[count++]=bit;
    pos[count++]=bytes-1;
    R22_SRAM_ENABLE();
    for(uint16_t i=0;i<count;i++)saved[i]=R22_SRAM_BYTE(R22_SRAM_BASE+1+(uint32_t)pos[i]*2);
    int ok=1;
    for(uint16_t pass=0;pass<2;pass++){
        for(uint16_t i=0;i<count;i++)R22_SRAM_BYTE(R22_SRAM_BASE+1+(uint32_t)pos[i]*2)=(uint8_t)((pass?0x5A:0xA5)^i);
        for(uint16_t i=0;i<count;i++)if(R22_SRAM_BYTE(R22_SRAM_BASE+1+(uint32_t)pos[i]*2)!=(uint8_t)((pass?0x5A:0xA5)^i))ok=0;
    }
    for(uint16_t i=0;i<count;i++)R22_SRAM_BYTE(R22_SRAM_BASE+1+(uint32_t)pos[i]*2)=saved[i];
    if(!ok)I_Error("SRAM ABSENT OR TOO SMALL");
    r22_block_cells=(uint16_t)cells;
    for(uint16_t i=0;i<r22_block_cells;i++)R22_SramWrite32(R22_SRAM_BASE+((uint32_t)i<<3),0);
}
#endif
