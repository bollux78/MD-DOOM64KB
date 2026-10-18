#include "compiler.h"
#include "r_defs.h"
#include "r22_blocklinks.h"
#include "i_system.h"
#if defined(DOOM_R23_MAPMEM)
#if !defined(DOOM_R22_SRAM_BLOCKLINKS)
#error R23 map memory requires SRAM blocklinks
#endif
static uint16_t line_base,side_base,node_base,node_capacity,node_used;
static msecnode_t *node_free;
void R23_MapMemoryInit(uint16_t lines,uint16_t sides,uint16_t cells){
    uint32_t end=(uint32_t)cells*4+(uint32_t)lines*sizeof(linedata_t)+(uint32_t)sides*sizeof(side_t);
    if(end>32768UL)I_Error("SRAM MAP STATE TOO LARGE");
    line_base=cells*4;side_base=line_base+lines*sizeof(linedata_t);node_base=(uint16_t)end;
    node_capacity=(32768UL-end)/sizeof(msecnode_t);node_used=0;node_free=NULL;end=32768UL;
    R22_SRAM_ENABLE();
    uint16_t pos[18],n=0;uint8_t saved[18];
    pos[n++]=0;for(uint32_t bit=1;bit<end;bit<<=1)pos[n++]=(uint16_t)bit;
    pos[n++]=(uint16_t)(end-1);
    for(uint16_t i=0;i<n;i++)saved[i]=R22_SRAM_BYTE(R22_SRAM_BASE+1+2UL*pos[i]);
    int ok=1;
    for(uint16_t pass=0;pass<2;pass++){
        for(uint16_t i=0;i<n;i++)R22_SRAM_BYTE(R22_SRAM_BASE+1+2UL*pos[i])=(uint8_t)((pass?0x5A:0xA5)^i);
        for(uint16_t i=0;i<n;i++)if(R22_SRAM_BYTE(R22_SRAM_BASE+1+2UL*pos[i])!=(uint8_t)((pass?0x5A:0xA5)^i))ok=0;
    }
    for(uint16_t i=0;i<n;i++)R22_SRAM_BYTE(R22_SRAM_BASE+1+2UL*pos[i])=saved[i];
    if(!ok)I_Error("SRAM MAP STATE UNAVAILABLE");
}
static uint32_t address(const void *p,uint16_t offset){
    uintptr_t v=(uintptr_t)p;
    return R22_SRAM_BASE+1+2UL*(v>=0x230000UL?node_base+v-0x230000UL+offset:v>=0x220000UL?side_base+v-0x220000UL+offset:line_base+v-0x210000UL+offset);
}
uint32_t R23_MapRead(const void *p,uint16_t offset,uint16_t size){
    uint32_t a=address(p,offset),v=0;while(size--){v=(v<<8)|R22_SRAM_BYTE(a);a+=2;}return v;
}
void R23_MapWrite(void *p,uint16_t offset,uint16_t size,uint32_t value){
    uint32_t a=address(p,offset)+2UL*(size-1);while(size--){R22_SRAM_BYTE(a)=value;value>>=8;a-=2;}
}
void *R23_NodeAlloc(void){
    if(node_free){msecnode_t *p=node_free;node_free=(msecnode_t*)(uintptr_t)R23_GET(p,m_tnext);return p;}
    if(node_used>=node_capacity)I_Error("SRAM CONTACT NODES FULL");
    return (void*)(uintptr_t)(0x230000UL+(uint32_t)node_used++*sizeof(msecnode_t));
}
void R23_NodeFree(void *v){msecnode_t *p=v;R23_SET(p,m_tnext,node_free);node_free=p;}
#endif
