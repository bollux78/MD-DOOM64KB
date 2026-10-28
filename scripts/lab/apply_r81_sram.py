#!/usr/bin/env python3
"""R81 SRAM layout: 6-byte lines + 8-byte sides; reserve upper 6 KiB."""
from pathlib import Path
p=Path('src/doomdata.h');s=p.read_text()
a='#define ML_MAPPED               256';assert s.count(a)==1
s=s.replace(a,'''#if defined(DOOM_R81_SAVE)
/* Runtime r_flags is separate from immutable line.flags (ML_DONTDRAW).
 * Its mapped bit can therefore use bit7 without changing ROM map flags. */
#define ML_MAPPED 128
#else
'''+a+'''
#endif''');p.write_text(s)
p=Path('src/r_defs.h');s=p.read_text()
a='    int16_t r_flags;\n    int16_t special;'
assert s.count(a)==1
s=s.replace(a,'''#if defined(DOOM_R81_SAVE)
    uint8_t r_flags; /* ML_MAPPED and RF_* fit in eight bits. */
    int8_t special;  /* Same signed range as immutable const_special. */
#else
'''+a+'''
#endif''')
a='    int8_t midtexture;\n} side_t;';assert s.count(a)==1
s=s.replace(a,'''    int8_t midtexture;
#if defined(DOOM_R81_SAVE)
    /* SRAM tokens advance 16 native bytes, physical records use eight.
     * This makes token -> SRAM mapping a shift, without division by 10. */
    uint8_t r81_token_padding[6];
#endif
} side_t;
#if defined(DOOM_R81_SAVE) && defined(__m68k__)
typedef char r81_side_size[(sizeof(side_t)==16)?1:-1];
#endif''')
p.write_text(s)
p=Path('src/r23_mapmem.c');s=p.read_text();s=s.replace('#include "r22_blocklinks.h"','#include "r22_blocklinks.h"\n#if defined(DOOM_R81_SAVE)\n#include "r81_save.h"\n#endif')
s=s.replace('void R23_MapMemoryInit(uint16_t lines,uint16_t sides,uint16_t cells){','void R23_MapMemoryInit(uint16_t lines,uint16_t sides,uint16_t cells){\n#if defined(DOOM_R81_SAVE) && defined(__m68k__)\n    typedef char r81_line_size[(sizeof(linedata_t)==6)?1:-1];\n#endif')
s=s.replace('+(uint32_t)sides*sizeof(side_t);','+(uint32_t)sides*\n#if defined(DOOM_R81_SAVE)\n    8u;\n#else\n    sizeof(side_t);\n#endif')
s=s.replace('if(end>30720UL)','if(end>\n#if defined(DOOM_R81_SAVE)\n    R81_SAVE_BASE\n#else\n    30720UL\n#endif\n    )')
s=s.replace('node_capacity=(30720UL-end)/','node_capacity=(\n#if defined(DOOM_R81_SAVE)\n    R81_SAVE_BASE\n#else\n    30720UL\n#endif\n    -end)/')
a='    return R22_SRAM_BASE+1+2UL*(v>=0x230000UL?node_base+v-0x230000UL+offset:v>=0x220000UL?side_base+v-0x220000UL+offset:line_base+v-0x210000UL+offset);';assert s.count(a)==1
s=s.replace(a,'''#if defined(DOOM_R81_SAVE)
    if(v>=0x220000UL && v<0x230000UL)
        return R22_SRAM_BASE+1+2UL*(side_base+((v-0x220000UL)>>1)+(offset>=4?offset-2:offset));
#endif
'''+a)
# Read helpers are inside a short SRAM-enabled scope.
a='    uint32_t a=address(p,offset),v=0;\n#if defined(DOOM_R39C_MOVEP_MAP)';assert s.count(a)==1
s=s.replace(a,'''    uint32_t a=address(p,offset),v=0;
#if defined(DOOM_R81_SAVE)
    uintptr_t token=(uintptr_t)p;
    if(token>=0x220000UL && token<0x230000UL && offset==0u && size==4u){
        uint16_t low=R39C_MovepRead16(a);
        v=low?(((uint32_t)(uintptr_t)_g_sectors&0xffff0000UL)|low):0;
        R25_SRAM_END();return v;
    }
    if(token>=0x210000UL && token<0x220000UL && offset==offsetof(linedata_t,r_validcount) && size==4u){
        v=R39C_MovepRead32(a);v=(v&0xffff0000UL)|((v>>8)&255u);
        R25_SRAM_END();return v;
    }
#endif
#if defined(DOOM_R39C_MOVEP_MAP)''')
a='void R23_MapWrite(void *p,uint16_t offset,uint16_t size,uint32_t value){\n    R25_SRAM_BEGIN();';assert s.count(a)==1
s=s.replace(a,a+'''
#if defined(DOOM_R81_SAVE)
    uintptr_t token=(uintptr_t)p;uint32_t packed=address(p,offset);
    if(token>=0x220000UL && token<0x230000UL && offset==0u && size==4u){
        R39C_MovepWrite16(packed,(uint16_t)value);R25_SRAM_END();return;
    }
    if(token>=0x210000UL && token<0x220000UL && offset==offsetof(linedata_t,r_validcount) && size==4u){
        R39C_MovepWrite16(packed,(uint16_t)(value>>16));
        R22_SRAM_BYTE(packed+4)=(uint8_t)value;R25_SRAM_END();return;
    }
#endif
''')
a='    uint32_t a=address(p,offset);uint8_t *d=out;';assert s.count(a)==1
s=s.replace(a,'''#if defined(DOOM_R81_SAVE)
    if((uintptr_t)p>=0x220000UL && (uintptr_t)p<0x230000UL &&
       !(offset>=4u && offset+size<=9u)){
        uint8_t *dst=out;
        for(uint16_t i=0;i<size;i++){
            uint16_t off=offset+i;
            if(off<4u)dst[i]=(uint8_t)(R23_MapRead(p,0,4)>>(24u-off*8u));
            else dst[i]=off<9u?(uint8_t)R23_MapRead(p,off,1):0;
        }
        return;
    }
#endif
'''+a)
a='    uint16_t value=R39C_MovepRead16(a);\n    value|=mask;R39C_MovepWrite16(a,value);';assert s.count(a)==1
s=s.replace(a,'''#if defined(DOOM_R81_SAVE)
    uint16_t value=R22_SRAM_BYTE(a);value|=mask;R22_SRAM_BYTE(a)=(uint8_t)value;
#else
'''+a+'''
#endif''')
s=s.replace('\nvoid R23_NodeFree(void *v)', '''
#if defined(DOOM_R81_SAVE)
void R81_ResetMapLinks(void){
    node_used=0;node_free=NULL;
    R25_SRAM_BEGIN();
    for(uint16_t i=0;i<line_base;i++)R22_SRAM_BYTE(R22_SRAM_BASE+1u+2UL*i)=0;
    R25_SRAM_END();
}
#endif
void R23_NodeFree(void *v)''')
p.write_text(s)
