/* S1d-Z4: invoke the ACTUAL R128 P_SetupLevel(1) on Sega CD sub-68000.
 * The build's explicit SCD_SUB_GEOM_ONLY stop occurs just after P_GroupLines;
 * monster, specials, demo, sound and rendering are deliberately NOT claimed.
 * Original R128 P_SetupLevel source is preserved in the repository.
 */
#include <stdint.h>
#include "doomdef.h"
#include "r_main.h"
#include "globdata.h"
#include "p_setup.h"
#include "w_wad.h"
#include "z_zone.h"
#include "i_system.h"
#include "scd_proto.h"
#define REG16(a) (*(volatile uint16_t *)(uintptr_t)(a))
extern void SCD_SubTransportReset(void);
extern uint32_t SCD_SubRequests(void), SCD_SubBytes(void);
extern uint32_t SCD_WadCacheCurrent(void), SCD_WadCachePeak(void);
extern uint16_t SCD_WadCacheMisses(void);
static uint32_t crc_sample(uint32_t crc,const uint8_t *p,uint16_t n)
{
    while(n--){
        crc^=*p++;
        for(uint16_t j=0;j<8;j++)
            crc=(crc>>1)^((crc&1u)?0xEDB88320UL:0);
    }
    return crc;
}
void sub_main(void)
{
    REG16(0xFF8002UL)=4;
    SCD_SubTransportReset();
    REG16(0xFF8020UL)=0x5343u;
    Z_Init();
    W_Init();
    _g_gamestate=GS_LEVEL;
    _g_gameskill=sk_medium;
    _g_gamemap=1;
    REG16(0xFF8024UL)=0x5701u; /* entering real P_SetupLevel */
    P_SetupLevel(1);
    REG16(0xFF8024UL)=0x5702u; /* returned after real P_GroupLines */
    if(_g_numsectors<=0 || _g_numlines<=0 || !_g_sectors ||
       !_g_sides || !_g_subsectors || !_g_maplines || !_g_blocklinks ||
       !nodes || numnodes<=0 || !_g_blockmaplump)
        I_Error("SCD SETUP GEOMETRY POINTERS");
    if(!_g_subsectors[0].sector || _g_sectors[0].linecount<=0 ||
       !_g_sectors[0].lines)
        I_Error("SCD SETUP SECTOR GROUPING");
    Z_CheckHeap();
    const int16_t label=W_GetNumForName("E1M1");
    uint32_t crc=0xFFFFFFFFUL;
    for(int16_t i=1;i<=9;i++){
        const int16_t lump=label+i;
        crc=crc_sample(crc,W_GetLumpByNum(lump),W_LumpLength(lump));
    }
    crc^=0xFFFFFFFFUL;
    if(SCD_SubRequests()!=10 || !SCD_SubBytes() ||
       SCD_WadCacheMisses()!=9 ||
       SCD_WadCachePeak()!=SCD_WadCacheCurrent())
        I_Error("SCD SETUP WAD CACHE");
    REG16(0xFF802AUL)=(uint16_t)(crc>>16);
    REG16(0xFF802CUL)=(uint16_t)crc;
    REG16(0xFF8024UL)=0x5A5Du;
    REG16(0xFF8020UL)=0x51B1u;
    for(;;){}
}
