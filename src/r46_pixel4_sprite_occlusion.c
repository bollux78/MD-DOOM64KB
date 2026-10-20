/* R46 M2C/P2E: pure visibility test for one projected sprite column.
 * No VDP, WAD, engine global memory, allocation or active 8x8 calls.
 */
#if defined(DOOM_R46_M2C)
#include "r46_pixel4_sprite_occlusion.h"
#if !defined(DOOM_R46_M2B) || defined(DOOM_R22_PIXEL4)
#error P2E native sprite visibility requires M2B coexistence
#endif
uint16_t R46_P4_SpriteVisiblePost(uint16_t x,
    const r46_p4_sprite_rect_t *sprite,
    const int16_t ceilingclip[76],const int16_t floorclip[76],
    const uint8_t solid[76],const uint16_t wall_depth[76],
    r46_p4_sprite_post_t *out)
{
    if(!sprite||!ceilingclip||!floorclip||!solid||!wall_depth||!out||
       x>=76||sprite->depth_units==0||sprite->x1<0||sprite->x2>=76||
       sprite->x1>sprite->x2||sprite->y1<0||sprite->y2>=44||
       sprite->y1>sprite->y2||x<(uint16_t)sprite->x1||
       x>(uint16_t)sprite->x2)return 0;
    if(solid[x] && wall_depth[x] && wall_depth[x]<sprite->depth_units)
        return 0;
    int16_t top=sprite->y1;
    int16_t bottom=sprite->y2;
    if(top<=ceilingclip[x])top=(int16_t)(ceilingclip[x]+1);
    if(bottom>=floorclip[x])bottom=(int16_t)(floorclip[x]-1);
    if(top<0)top=0;
    if(bottom>43)bottom=43;
    if(top>bottom)return 0;
    const r46_p4_sprite_post_t candidate={top,bottom};
    *out=candidate;
    return 1;
}
typedef struct {
    uint16_t (*visible)(uint16_t,const r46_p4_sprite_rect_t *,
        const int16_t *,const int16_t *,const uint8_t *,
        const uint16_t *,r46_p4_sprite_post_t *);
} r46_p4_sprite_occlusion_ops_t;
static const r46_p4_sprite_occlusion_ops_t occlusion_ops={
    R46_P4_SpriteVisiblePost
};
__attribute__((noinline))
const r46_p4_sprite_occlusion_ops_t *R46_P4_SpriteOcclusionOps(void)
{
    return &occlusion_ops;
}
__attribute__((noinline))
uint16_t R46_P4_SpriteOcclusionValidate(void)
{
    const r46_p4_sprite_occlusion_ops_t *ops=R46_P4_SpriteOcclusionOps();
    return (uint16_t)(ops && ops->visible &&
        sizeof(r46_p4_sprite_post_t)==4);
}
#endif
