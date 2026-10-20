/* M3B: deterministic native display diagnostic. No VDP/heap/global WRAM.
 * The top two packed sample rows remain black and all 798 visual tiles
 * have at least two different horizontal samples. */
#if defined(DOOM_R46_M2C)
#include "r46_m3b_pattern.h"
#include "r46_pixel4_raster.h"
#include "r22_pixel4.h"
#if !defined(DOOM_R46_M2B) || defined(DOOM_R22_PIXEL4)
#error M3B pattern needs dual-linked R39f/pixel4 environment
#endif
uint16_t R46_M3B_MakePattern(uint8_t *pixels,uint16_t capacity)
{
    if(!pixels||capacity<R46_P4_RASTER_BYTES)return 0;
    if(!R46_P4_ClearTarget(pixels,capacity,0,0))return 0;
    for(uint16_t y=2;y<44;y++)
        for(uint16_t x=0;x<76;x++) {
            const uint8_t c=(uint8_t)((((x>>1)+(y>>1))&15u) ^ (x&1u));
            R22_Put(pixels,x,y,c);
        }
    return 1;
}
typedef struct {uint16_t (*make)(uint8_t*,uint16_t);} r46_m3b_pattern_ops_t;
static const r46_m3b_pattern_ops_t pattern_ops={R46_M3B_MakePattern};
__attribute__((noinline))
const r46_m3b_pattern_ops_t *R46_M3B_PatternOps(void){return &pattern_ops;}
__attribute__((noinline))
uint16_t R46_M3B_PatternValidate(void)
{
    const r46_m3b_pattern_ops_t *o=R46_M3B_PatternOps();
    return (uint16_t)(o && o->make && R46_P4_RASTER_BYTES==1672);
}
#endif
