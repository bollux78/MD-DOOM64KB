/* R46 M2C/P2G stable bounded sprite depth ordering. NOT active gameplay. */
#if defined(DOOM_R46_M2C)
#include "r46_pixel4_sprite_order.h"
#if !defined(DOOM_R46_M2B) || defined(DOOM_R22_PIXEL4)
#error P2G order helper requires M2B coexistence
#endif
uint16_t R46_P4_SortSprites(const uint16_t *depth,
    uint16_t count,uint8_t *indices)
{
    if(!depth||!indices||!count||count>128)return 0;
    for(uint16_t i=0;i<count;i++)
        if(!depth[i])return 0;
    for(uint16_t i=0;i<count;i++){
        uint16_t j=i;
        while(j && depth[indices[j-1]]<depth[i]){
            indices[j]=indices[j-1];j--;
        }
        indices[j]=(uint8_t)i;
    }
    return count;
}
typedef struct {
    uint16_t (*sort)(const uint16_t*,uint16_t,uint8_t*);
} r46_p4_order_ops_t;
static const r46_p4_order_ops_t r46_p4_order_ops={R46_P4_SortSprites};
__attribute__((noinline))
const r46_p4_order_ops_t *R46_P4_SpriteOrderOps(void)
{
    return &r46_p4_order_ops;
}
__attribute__((noinline))
uint16_t R46_P4_SpriteOrderValidate(void)
{
    const r46_p4_order_ops_t *o=R46_P4_SpriteOrderOps();
    return (uint16_t)(o&&o->sort);
}
#endif
