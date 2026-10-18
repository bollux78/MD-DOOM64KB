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
    if(end>30720UL)I_Error("SRAM MAP STATE TOO LARGE");
    line_base=cells*4;side_base=line_base+lines*sizeof(linedata_t);node_base=(uint16_t)end;
    node_capacity=(30720UL-end)/
#if defined(DOOM_R24_EPISODE)
    12u;
#else
    sizeof(msecnode_t);
#endif
    node_used=0;node_free=NULL;end=32768UL;
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
#if defined(DOOM_R24_EPISODE)
static uint32_t node_address(const void *p){return R22_SRAM_BASE+1+2UL*(node_base+(((uintptr_t)p-0x230000UL)/sizeof(msecnode_t))*12u);}
static uint16_t node_u16(uint32_t a){return ((uint16_t)R22_SRAM_BYTE(a)<<8)|R22_SRAM_BYTE(a+2);}
static uint32_t node_read(const void *p,uint16_t off){
    uint32_t a=node_address(p);
    if(off==offsetof(msecnode_t,m_sector)){uint8_t i=R22_SRAM_BYTE(a);return i==255?0:(uint32_t)(uintptr_t)&_g_sectors[i];}
    if(off==offsetof(msecnode_t,m_thing)){uint16_t v=node_u16(a+2);return v?0xE0FF0000UL|v:0;}
    if(off==offsetof(msecnode_t,visited))return R22_SRAM_BYTE(a+22);
    uint16_t field=(off-offsetof(msecnode_t,m_tprev))/sizeof(((msecnode_t*)0)->m_tprev);
    uint16_t i=node_u16(a+6+field*4);return i?0x230000UL+(uint32_t)(i-1)*sizeof(msecnode_t):0;
}
static void node_write(void *p,uint16_t off,uint32_t value){
    uint32_t a=node_address(p);uint16_t v;
    if(off==offsetof(msecnode_t,m_sector)){R22_SRAM_BYTE(a)=value?(sector_t*)(uintptr_t)value-_g_sectors:255;return;}
    if(off==offsetof(msecnode_t,visited)){R22_SRAM_BYTE(a+22)=value;return;}
    if(off==offsetof(msecnode_t,m_thing)){a+=2;v=(uint16_t)value;}
    else{uint16_t field=(off-offsetof(msecnode_t,m_tprev))/sizeof(((msecnode_t*)0)->m_tprev);a+=6+field*4;v=value?1+(value-0x230000UL)/sizeof(msecnode_t):0;}
    R22_SRAM_BYTE(a)=v>>8;R22_SRAM_BYTE(a+2)=v;
}
#endif
uint32_t R23_MapRead(const void *p,uint16_t offset,uint16_t size){
#if defined(DOOM_R24_EPISODE)
    if((uintptr_t)p>=0x230000UL)return node_read(p,offset);
#endif
    uint32_t a=address(p,offset),v=0;while(size--){v=(v<<8)|R22_SRAM_BYTE(a);a+=2;}return v;
}
void R23_MapWrite(void *p,uint16_t offset,uint16_t size,uint32_t value){
#if defined(DOOM_R24_EPISODE)
    if((uintptr_t)p>=0x230000UL){node_write(p,offset,value);return;}
#endif
    uint32_t a=address(p,offset)+2UL*(size-1);while(size--){R22_SRAM_BYTE(a)=value;value>>=8;a-=2;}
}
void *R23_NodeAlloc(void){
    if(node_free){msecnode_t *p=node_free;node_free=(msecnode_t*)(uintptr_t)R23_GET(p,m_tnext);return p;}
    if(node_used>=node_capacity)I_Error("SRAM CONTACT NODES FULL");
    return (void*)(uintptr_t)(0x230000UL+(uint32_t)node_used++*sizeof(msecnode_t));
}
void R23_NodeFree(void *v){msecnode_t *p=v;R23_SET(p,m_tnext,node_free);node_free=p;}
#endif
