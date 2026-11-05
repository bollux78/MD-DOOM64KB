#!/usr/bin/env python3
"""R134: verify three Freedoom map WADs in SSF2 extra pages on Doom startup."""
from pathlib import Path

p=Path('src/d_main.c')
s=p.read_text()
anchor="static void R133_TestAndShow(void)"
assert s.count(anchor)==1
func=r'''
/* R134 small raw PWAD inspector: reads only the remapped slot 7,
   no allocations, no modifications to SRAM, no retained pointers. */
static uint32_t R134_LE32(const volatile uint8_t *p)
{
    return (uint32_t)p[0]|((uint32_t)p[1]<<8)|
           ((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);
}
static uint16_t R134_CheckWad(uint8_t page, uint32_t bank_offset,
                               uint32_t expected_size, const char *marker)
{
    R133_MAPREG=page;
    const volatile uint8_t *base=(const volatile uint8_t *)(0x380000ul+bank_offset);
    uint32_t n=R134_LE32(base+4), dir=R134_LE32(base+8);
    if (base[0]!='P' || base[1]!='W' || base[2]!='A' || base[3]!='D')
        return 0;
    if (!n || n>2048 || dir>=expected_size ||
        n*16ul>expected_size-dir)
        return 0;
    for(uint32_t i=0;i<n;i++)
    {
        const volatile uint8_t *ent=base+dir+16ul*i;
        uint16_t equal=1;
        for(uint16_t j=0;j<4;j++)
            if(ent[8u+j]!=(uint8_t)marker[j])equal=0;
        if(equal && ent[12]==0)return 1;
    }
    return 0;
}
'''
s=s.replace(anchor,func+anchor)
needle="    uint32_t old_word=*(volatile uint32_t *)(0x380100ul);"
assert s.count(needle)==1
s=s.replace(needle,needle+"""
    uint16_t r134_e1m1=R134_CheckWad(8,0x1000ul,142093ul,"E1M1");
    uint16_t r134_e1m2=R134_CheckWad(8,0x24000ul,261418ul,"E1M2");
    uint16_t r134_e1m3=R134_CheckWad(9,0x1000ul,220329ul,"E1M3");
    R133_MAPREG=7;""")
needle2='    VDP_drawText("STARTING DOOM...",10,22);'
assert s.count(needle2)==1
s=s.replace(needle2,'''    VDP_drawText("FREEDOOM MAPS IN EXTRA ROM",2,20);
    VDP_drawText(r134_e1m1?"E1M1: PASS":"E1M1: FAIL",2,21);
    VDP_drawText(r134_e1m2?"E1M2: PASS":"E1M2: FAIL",15,21);
    VDP_drawText(r134_e1m3?"E1M3: PASS":"E1M3: FAIL",28,21);
    VDP_drawText("STORED ONLY - NOT PLAYABLE",2,24);
    VDP_drawText("STARTING DOOM...",10,26);''')
p.write_text(s)
print('R134 source mapped-read inspector attached')
