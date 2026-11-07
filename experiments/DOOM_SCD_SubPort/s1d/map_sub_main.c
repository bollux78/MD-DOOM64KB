/* S1d-Z1: validate the actual converted E1M1 map lumps on Sega CD 68000.
 * Uses the same W_* callbacks as the future P_SetupLevel, from remote MD WAD.
 * Intentionally not P_SetupLevel and not G_Ticker: no gameplay on sub yet.
 * No map data or copyrighted assets are embedded in this source.
 */
#include <stdint.h>
#include "doomdata.h"
#include "r_defs.h"
#include "w_wad.h"
#include "z_zone.h"
#include "i_system.h"
#include "scd_proto.h"

#define REG16(a) (*(volatile uint16_t *)(uintptr_t)(a))
extern void SCD_SubTransportReset(void);
extern uint32_t SCD_SubRequests(void), SCD_SubBytes(void);
extern void W_FlushCache(void);
extern uint32_t SCD_WadCachePeak(void);
static uint32_t crc32_sample(uint32_t crc, const uint8_t *p, uint16_t n)
{
    while (n--) {
        crc ^= *p++;
        for (uint16_t j=0;j<8;j++)
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
    uint8_t *probe=(uint8_t *)Z_MallocStatic(256);
    if (!probe) I_Error("S1D Z1 ZONE");
    for (uint16_t j=0;j<256;j++) probe[j]=(uint8_t)(j^0xA5u);
    for (uint16_t j=0;j<256;j++)
        if (probe[j]!=(uint8_t)(j^0xA5u)) I_Error("S1D Z1 ZONE CORRUPT");
    Z_Free(probe);
    Z_CheckHeap();
    W_Init();

    const int16_t map=W_GetNumForName("E1M1");
    /* Converted map order comes from src/p_setup.c, ML_THINGS..ML_BLOCKMAP.
       Sizes are computed before fetching, so cache can be flushed after each
       lump without invalidating any pointers still in use. */
    const uint16_t width[10]={
        0,sizeof(mapthing_t),sizeof(line_t),sizeof(mapsidedef_t),
        sizeof(seg_t),sizeof(mapsubsector_t),sizeof(mapnode_t),
        sizeof(mapsector_t),1,sizeof(uint16_t)
    };
    uint16_t count[10]={0}, size[10]={0};
    for (uint16_t k=1;k<=9;k++) {
        size[k]=W_LumpLength(map+(int16_t)k);
        if (!size[k] || (k<=7 && size[k]%width[k]) ||
            (k==9 && (size[k]<8u || (size[k]&1u))))
            I_Error("S1D Z1 MAP LUMP FORMAT");
        count[k]=size[k]/width[k];
    }
    if (count[2]>2048u || count[3]>2048u ||
        count[7]==0 || count[7]>255u || count[4]==0 || count[5]==0)
        I_Error("S1D Z1 MAP LIMITS");

    uint32_t crc=0xFFFFFFFFUL;
    for (uint16_t k=1;k<=9;k++) {
        const uint8_t *p=(const uint8_t *)W_GetLumpByNum(map+(int16_t)k);
        REG16(0xFF8024UL)=(uint16_t)(0x5500u | k); /* last validated lump */
        crc=crc32_sample(crc,p,size[k]);

        if (k==2) {
            const line_t *lines=(const line_t *)p;
            for (uint16_t j=0;j<count[k];j++)
                if (lines[j].sidenum[0]>=count[3] ||
                    (lines[j].sidenum[1]!=NO_INDEX &&
                     lines[j].sidenum[1]>=count[3]))
                    I_Error("S1D Z1 LINE SIDE INDEX");
        }
        if (k==3) {
            const mapsidedef_t *sides=(const mapsidedef_t *)p;
            for (uint16_t j=0;j<count[k];j++)
                if (sides[j].sector>=count[7])
                    I_Error("S1D Z1 SIDE SECTOR INDEX");
        }
        if (k==4) {
            const seg_t *segs=(const seg_t *)p;
            for (uint16_t j=0;j<count[k];j++)
                if (segs[j].linenum>=count[2] ||
                    (segs[j].sidenum!=NO_INDEX &&
                     (segs[j].sidenum>=count[3] ||
                      segs[j].frontsectornum>=count[7] ||
                      (segs[j].backsectornum!=NO_INDEX8 &&
                       segs[j].backsectornum>=count[7]))))
                    I_Error("S1D Z1 SEG REFERENCE");
        }
        if (k==5) {
            const mapsubsector_t *ss=(const mapsubsector_t *)p;
            for (uint16_t j=0;j<count[k];j++)
                if (ss[j].numsegs<1 || ss[j].firstseg<0 ||
                    (uint32_t)ss[j].firstseg+(uint32_t)ss[j].numsegs>count[4])
                    I_Error("S1D Z1 SUBSECTOR RANGE");
        }
        if (k==6) {
            const mapnode_t *nodes=(const mapnode_t *)p;
            for (uint16_t j=0;j<count[k];j++)
                for (uint16_t side=0;side<2;side++) {
                    const uint16_t child=nodes[j].children[side];
                    if (child&NF_SUBSECTOR) {
                        if ((child&~NF_SUBSECTOR)>=count[5])
                            I_Error("S1D Z1 NODE LEAF");
                    } else if (child>=count[6])
                        I_Error("S1D Z1 NODE BRANCH");
                }
        }
        if (k==9) {
            const int16_t *bm=(const int16_t *)p;
            if (bm[2]<=0 || bm[3]<=0)
                I_Error("S1D Z1 BLOCKMAP");
        }
        /* The full engine cannot flush here because it retains pointers.
           For this format test, a one-lump-at-a-time streaming pass bounds
           storage without pretending to solve the P_SetupLevel cache budget. */
        W_FlushCache();
    }
    crc ^= 0xFFFFFFFFUL;
    Z_CheckHeap();
    if (SCD_SubRequests()!=10u || !SCD_SubBytes() ||
        SCD_WadCachePeak()>65536UL)
        I_Error("S1D Z1 TRANSPORT OR CACHE");
    REG16(0xFF802AUL)=(uint16_t)(crc>>16);
    REG16(0xFF802CUL)=(uint16_t)crc;
    REG16(0xFF8024UL)=0x5A2Du;
    REG16(0xFF8020UL)=0x51B1u;
    for (;;) {}
}
