/* R46 P2D world coordinates -> camera -> guarded projected sprite rect.
 * Exact visual equivalence with R_ProjectSprite remains to be validated
 * when this is integrated into the native 4x4 renderer.
 */
#if defined(DOOM_R46_M2C)
#include "r46_pixel4_sprite_world.h"
#include <limits.h>
#if !defined(DOOM_R46_M2B) || defined(DOOM_R22_PIXEL4)
#error P2D requires M2B coexistence; do not enable R22 pixel4
#endif
static uint16_t fits_s32(int64_t n)
{
    return (uint16_t)(n >= INT32_MIN && n <= INT32_MAX);
}
uint16_t R46_P4_WorldToCamera(int32_t actor_x,int32_t actor_y,
    int32_t view_x,int32_t view_y,int32_t viewcos,int32_t viewsin,
    r46_p4_sprite_camera_point_t *out)
{
    if(!out || viewcos < -65536 || viewcos > 65536 ||
       viewsin < -65536 || viewsin > 65536)return 0;
    const int64_t dx=(int64_t)actor_x-view_x;
    const int64_t dy=(int64_t)actor_y-view_y;
    /* Reject extreme inputs rather than risk multiplying 64-bit limits.
     * Doom playable ranges fit; this is a conservative contract. */
    if(!fits_s32(dx)||!fits_s32(dy))return 0;
    const int64_t depth=(dx*viewcos+dy*viewsin)/65536;
    const int64_t lateral=(dx*viewsin-dy*viewcos)/65536;
    if(!fits_s32(depth)||!fits_s32(lateral))return 0;
    r46_p4_sprite_camera_point_t candidate={(int32_t)depth,(int32_t)lateral};
    *out=candidate;
    return 1;
}
uint16_t R46_P4_ProjectWorldSprite(int32_t actor_x,int32_t actor_y,
    int32_t view_x,int32_t view_y,int32_t viewcos,int32_t viewsin,
    int32_t patch_left,int32_t patch_width,
    int32_t top_z,int32_t bottom_z,uint16_t gameplay,
    r46_p4_sprite_rect_t *out)
{
    if(!out)return 0;
    r46_p4_sprite_camera_point_t pos;
    if(!R46_P4_WorldToCamera(actor_x,actor_y,view_x,view_y,
                            viewcos,viewsin,&pos))return 0;
    const int64_t left=(int64_t)pos.lateral-patch_left;
    if(!fits_s32(left))return 0;
    return R46_P4_ProjectSpriteRect((int32_t)left,pos.depth,
        patch_width,top_z,bottom_z,gameplay,out);
}
typedef struct {
    uint16_t (*world)(int32_t,int32_t,int32_t,int32_t,int32_t,int32_t,
                      r46_p4_sprite_camera_point_t *);
    uint16_t (*project)(int32_t,int32_t,int32_t,int32_t,int32_t,int32_t,
        int32_t,int32_t,int32_t,int32_t,uint16_t,r46_p4_sprite_rect_t *);
} r46_p4_sprite_world_ops_t;
static const r46_p4_sprite_world_ops_t world_ops={
    R46_P4_WorldToCamera,R46_P4_ProjectWorldSprite
};
__attribute__((noinline))
const r46_p4_sprite_world_ops_t *R46_P4_WorldSpriteOps(void){return &world_ops;}
__attribute__((noinline))
uint16_t R46_P4_WorldSpriteValidate(void)
{
    const r46_p4_sprite_world_ops_t *ops=R46_P4_WorldSpriteOps();
    return (uint16_t)(ops && ops->world && ops->project &&
                      sizeof(r46_p4_sprite_camera_point_t)==8);
}
#endif
