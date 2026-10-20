/* R46 P2I: packed nibble 76x44 software raster into caller-owned memory.
 * No VDP, no global framebuffer, no heap, no writes until called by owner.
 */
#if defined(DOOM_R46_M2C)
#include "r46_pixel4_raster.h"
#if !defined(DOOM_R46_M2B) || defined(DOOM_R22_PIXEL4)
#error P2I requires secondary native geometry linked beside active 8x8
#endif
_Static_assert(R46_P4_RASTER_W*R46_P4_RASTER_H/2==R46_P4_RASTER_BYTES,
               "P2I packed pixel layout mismatch");
uint16_t R46_P4_ClearTarget(uint8_t *target,uint16_t capacity,
                            uint8_t color,uint16_t keep_rows)
{
    if(!target||capacity<R46_P4_RASTER_BYTES||color>15||
       keep_rows>R46_P4_RASTER_H)return 0;
    const uint8_t pair=(uint8_t)((color<<4)|color);
    const uint16_t first=(uint16_t)(keep_rows*R46_P4_RASTER_PITCH);
    for(uint16_t i=first;i<R46_P4_RASTER_BYTES;i++)target[i]=pair;
    return 1;
}
uint16_t R46_P4_FillRow(uint8_t *target,uint16_t capacity,
    uint16_t y,uint16_t first,uint16_t last,uint8_t color)
{
    if(!target||capacity<R46_P4_RASTER_BYTES||y>=R46_P4_RASTER_H||
       first>last||last>=R46_P4_RASTER_W||color>15)return 0;
    uint16_t offset=(uint16_t)(y*R46_P4_RASTER_PITCH+(first>>1));
    for(uint16_t x=first;x<=last;x++){
        uint8_t prior=target[offset];
        target[offset]=(uint8_t)((x&1u) ?
          ((prior&0xf0u)|color) : ((prior&0x0fu)|(color<<4)));
        if(x&1u)offset++;
    }
    return 1;
}
uint16_t R46_P4_FillColumn(uint8_t *target,uint16_t capacity,
    uint16_t x,uint16_t first,uint16_t last,uint8_t color)
{
    if(!target||capacity<R46_P4_RASTER_BYTES||x>=R46_P4_RASTER_W||
       first>last||last>=R46_P4_RASTER_H||color>15)return 0;
    uint16_t offset=(uint16_t)(first*R46_P4_RASTER_PITCH+(x>>1));
    for(uint16_t y=first;y<=last;y++,offset+=R46_P4_RASTER_PITCH){
        uint8_t prior=target[offset];
        target[offset]=(uint8_t)((x&1u) ?
          ((prior&0xf0u)|color) : ((prior&0x0fu)|(color<<4)));
    }
    return 1;
}
uint8_t R46_P4_ReadSample(const uint8_t *target,uint16_t capacity,
                          uint16_t x,uint16_t y)
{
    if(!target||capacity<R46_P4_RASTER_BYTES||x>=R46_P4_RASTER_W||
       y>=R46_P4_RASTER_H)return 0xffu;
    const uint8_t v=target[y*R46_P4_RASTER_PITCH+(x>>1)];
    return (uint8_t)((x&1u)?(v&15u):(v>>4));
}
typedef struct {
    uint16_t (*clear)(uint8_t*,uint16_t,uint8_t,uint16_t);
    uint16_t (*row)(uint8_t*,uint16_t,uint16_t,uint16_t,uint16_t,uint8_t);
    uint16_t (*column)(uint8_t*,uint16_t,uint16_t,uint16_t,uint16_t,uint8_t);
    uint8_t (*sample)(const uint8_t*,uint16_t,uint16_t,uint16_t);
} r46_p4_raster_ops_t;
static const r46_p4_raster_ops_t raster_ops={
    R46_P4_ClearTarget,R46_P4_FillRow,R46_P4_FillColumn,R46_P4_ReadSample
};
__attribute__((noinline))
const r46_p4_raster_ops_t *R46_P4_RasterOps(void){return &raster_ops;}
__attribute__((noinline))
uint16_t R46_P4_RasterValidate(void)
{
    const r46_p4_raster_ops_t *ops=R46_P4_RasterOps();
    return (uint16_t)(ops&&ops->clear&&ops->row&&ops->column&&ops->sample &&
        R46_P4_RASTER_W==76 && R46_P4_RASTER_H==44 &&
        R46_P4_RASTER_PITCH==38 && R46_P4_RASTER_BYTES==1672);
}
#endif
