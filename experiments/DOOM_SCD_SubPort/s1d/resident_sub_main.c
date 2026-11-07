/* S1d-Z2/Z3: resident E1M1 map and native PRG-RAM geometry on sub 68000.
 * Uses the same W_* callbacks as the future P_SetupLevel, from remote MD WAD.
 * Does not execute P_SetupLevel or G_Ticker. MD gameplay fallback remains.
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
extern uint32_t SCD_WadCachePeak(void), SCD_WadCacheCurrent(void);
extern uint16_t SCD_WadCacheMisses(void);
static uint32_t crc32_sample(uint32_t crc, const uint8_t *p, uint16_t n)
{
    while (n--) {
        crc ^= *p++;
        for (uint16_t j=0;j<8;j++)
            crc=(crc>>1)^((crc&1u)?0xEDB88320UL:0);
    }
    return crc;
}

#if defined(SCD_Z3_CONSTRUCT)
/* Runtime geometry allocations in native PRG RAM. This is not P_SetupLevel:
 * game thinkers, specials, texture and sound systems are NOT initialized. */
static void construct_geometry(const uint8_t *const lumps[10],const uint16_t count[10])
{
    const line_t *maplines=(const line_t *)lumps[2];
    const mapsidedef_t *mapsides=(const mapsidedef_t *)lumps[3];
    const seg_t *mapsegs=(const seg_t *)lumps[4];
    const mapsubsector_t *mapss=(const mapsubsector_t *)lumps[5];
    const mapsector_t *mapsectors=(const mapsector_t *)lumps[7];
    uint32_t bytes[4]={
        (uint32_t)count[7]*sizeof(sector_t),
        (uint32_t)count[3]*sizeof(side_t),
        (uint32_t)count[2]*sizeof(linedata_t),
        (uint32_t)count[5]*sizeof(subsector_t)
    };
    for(uint16_t i=0;i<4;i++)if(bytes[i]>65535UL)
        I_Error("S1D Z3 ALLOCATION OVERFLOW");
    sector_t *sec=Z_CallocLevel((uint16_t)bytes[0]);
    side_t *sides=Z_CallocLevel((uint16_t)bytes[1]);
    linedata_t *ld=Z_CallocLevel((uint16_t)bytes[2]);
    subsector_t *ss=Z_CallocLevel((uint16_t)bytes[3]);
    for(uint16_t i=0;i<count[7];i++){
        sec[i].floorheight=(int32_t)mapsectors[i].floorheight*FRACUNIT;
        sec[i].ceilingheight=(int32_t)mapsectors[i].ceilingheight*FRACUNIT;
        sec[i].floorpic=mapsectors[i].floorpic;
        sec[i].ceilingpic=mapsectors[i].ceilingpic;
        sec[i].lightlevel=mapsectors[i].lightlevel;
        sec[i].special=mapsectors[i].special;
        sec[i].oldspecial=mapsectors[i].special;
    }
    for(uint16_t i=0;i<count[3];i++){
        sides[i].sector=sec+mapsides[i].sector;
        sides[i].textureoffset=mapsides[i].textureoffset;
        sides[i].midtexture=mapsides[i].midtexture;
        sides[i].toptexture=mapsides[i].toptexture;
        sides[i].bottomtexture=mapsides[i].bottomtexture;
    }
    uint32_t linked=0;
    for(uint16_t i=0;i<count[2];i++){
        const line_t *line=maplines+i;
        sector_t *front=sides[line->sidenum[0]].sector;
        sector_t *back=line->sidenum[1]==NO_INDEX?0:
            sides[line->sidenum[1]].sector;
        ld[i].special=line->const_special;
        front->linecount++;linked++;
        if(back && back!=front){back->linecount++;linked++;}
    }
    if(!linked || linked>65535UL/sizeof(line_t*))
        I_Error("S1D Z3 LINE PTR OVERFLOW");
    const line_t **lines=Z_CallocLevel((uint16_t)(linked*sizeof(line_t*)));
    const line_t **cursor=lines;
    for(uint16_t i=0;i<count[7];i++){
        sec[i].lines=cursor;
        cursor+=sec[i].linecount;
        sec[i].linecount=0;
    }
    if(cursor!=lines+linked)I_Error("S1D Z3 LINE COUNT");
    for(uint16_t i=0;i<count[2];i++){
        const line_t *line=maplines+i;
        sector_t *front=sides[line->sidenum[0]].sector;
        sector_t *back=line->sidenum[1]==NO_INDEX?0:
            sides[line->sidenum[1]].sector;
        front->lines[front->linecount++]=line;
        if(back && back!=front)back->lines[back->linecount++]=line;
    }
    for(uint16_t i=0;i<count[5];i++){
        uint16_t first=(uint16_t)mapss[i].firstseg;
        uint16_t end=first+(uint16_t)mapss[i].numsegs;
        sector_t *owner=0;
        for(uint16_t j=first;j<end;j++)
            if(mapsegs[j].sidenum!=NO_INDEX){
                owner=sides[mapsegs[j].sidenum].sector;
                break;
            }
        if(!owner)I_Error("S1D Z3 SUBSECTOR NO OWNER");
        ss[i].sector=owner;
    }
    const int16_t *bm=(const int16_t *)lumps[9];
    uint32_t cells=(uint32_t)(uint16_t)bm[2]*(uint16_t)bm[3];
    if(!cells || cells>16383UL)I_Error("S1D Z3 BLOCKMAP OVERFLOW");
    mobj_t **blockheads=Z_CallocLevel((uint16_t)(cells*sizeof(mobj_t*)));
    if(!sec || !sides || !ld || !ss || !blockheads ||
       ss[0].sector<sec || ss[0].sector>=sec+count[7] || blockheads[0])
        I_Error("S1D Z3 INVALID ALLOCATION");
    Z_CheckHeap();
}
#endif

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

    const uint8_t *held[10]={0};
    uint32_t crc=0xFFFFFFFFUL;
    for (uint16_t k=1;k<=9;k++) {
        const uint8_t *p=(const uint8_t *)W_GetLumpByNum(map+(int16_t)k);
        held[k]=p;
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
    }
    /* Verify every retained pointer and byte after the last bank exchange. */
    uint32_t verify=0xFFFFFFFFUL;
    for(uint16_t k=1;k<=9;k++){
        const uint8_t *again=(const uint8_t *)W_GetLumpByNum(map+(int16_t)k);
        if(!again || again!=held[k])I_Error("S1D Z2 POINTER NOT STABLE");
        verify=crc32_sample(verify,again,size[k]);
    }
    uint32_t resident_bytes=0;
    for(uint16_t k=1;k<=9;k++)resident_bytes+=size[k];
    /* Directory bytes count in transport, not in nine-lump arena. */
    if(verify!=crc){
        REG16(0xFF8024UL)=0x57A1u;
        I_Error("S1D Z2 CACHE CRC");
    }
    if(SCD_WadCacheMisses()!=9){
        REG16(0xFF8024UL)=0x57A2u;
        I_Error("S1D Z2 CACHE MISSES");
    }
    if(SCD_WadCachePeak()!=SCD_WadCacheCurrent() ||
       SCD_WadCacheCurrent()<resident_bytes){
        REG16(0xFF8024UL)=0x57A3u;
        I_Error("S1D Z2 CACHE ALLOCATION");
    }
#if defined(SCD_Z3_CONSTRUCT)
    REG16(0xFF8024UL)=0x5603u; /* currently building live geometry */
    construct_geometry(held,count);
#endif
    crc ^= 0xFFFFFFFFUL;
    Z_CheckHeap();
    if(SCD_SubRequests()!=10u || !SCD_SubBytes() ||
       SCD_WadCachePeak()>128UL*1024UL)
        I_Error("S1D Z2 TRANSPORT OR CACHE");
    REG16(0xFF802AUL)=(uint16_t)(crc>>16);
    REG16(0xFF802CUL)=(uint16_t)crc;
#if defined(SCD_Z3_CONSTRUCT)
    REG16(0xFF8024UL)=0x5A4Du;
#else
    REG16(0xFF8024UL)=0x5A3Du;
#endif
    REG16(0xFF8020UL)=0x51B1u;
    for (;;) {}
}
