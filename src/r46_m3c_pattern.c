/* Four diagonal palette phases, two 4x4 pixels per byte, no allocation.
 * Like M3B, every drawn tile is guaranteed non-solid by adjacent colors.
 */
#if defined(DOOM_R46_M2C)
#include "r46_m3c_pattern.h"
#include "r46_pixel4_raster.h"
#include "r22_pixel4.h"
#if !defined(DOOM_R46_M2B) || defined(DOOM_R22_PIXEL4)
#error M3C diagnostic pixels require the R39f/pixel4 coexistence build
#endif
uint16_t R46_M3C_MakePattern(uint8_t *pixels,uint16_t capacity,
                            uint16_t phase)
{
    if(!pixels||capacity<R46_P4_RASTER_BYTES||phase>3u)return 0;
    if(!R46_P4_ClearTarget(pixels,capacity,0,0))return 0;
    for(uint16_t y=2;y<44;y++)
        for(uint16_t x=0;x<76;x++){
            const uint8_t c=(uint8_t)((((x>>1)+(y>>1)+3u*phase)&15u)
                                      ^ (x&1u));
            R22_Put(pixels,x,y,c);
        }
    return 1;
}
typedef struct {
    uint16_t (*make)(uint8_t*,uint16_t,uint16_t);
} r46_m3c_pattern_ops_t;
static const r46_m3c_pattern_ops_t pattern_ops={R46_M3C_MakePattern};
__attribute__((noinline))
const r46_m3c_pattern_ops_t *R46_M3C_PatternOps(void){return &pattern_ops;}
__attribute__((noinline))
uint16_t R46_M3C_PatternValidate(void)
{
    const r46_m3c_pattern_ops_t *o=R46_M3C_PatternOps();
    return (uint16_t)(o&&o->make&&R46_P4_RASTER_BYTES==1672);
}
#endif
