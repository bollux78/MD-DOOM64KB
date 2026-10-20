/* R46 P2F: native 76x44 sprite column iteration, pure callback bridge.
 * Do not connect this to R39f or a live pixel4 renderer before M3/M4.
 */
#if defined(DOOM_R46_M2C)
#include "r46_pixel4_sprite_runs.h"
#if !defined(DOOM_R46_M2B) || defined(DOOM_R22_PIXEL4)
#error P2F requires co-linked M2B while the 8x8 renderer remains active
#endif
uint16_t R46_P4_EmitSpritePosts(const r46_p4_sprite_rect_t *sprite,
    const int16_t ceilingclip[76],const int16_t floorclip[76],
    const uint8_t solid[76],const uint16_t wall_depth[76],
    r46_p4_sprite_post_emit_t emit,void *ctx)
{
    if(!sprite || !ceilingclip || !floorclip || !solid || !wall_depth ||
       !emit || sprite->x1<0 || sprite->x2>=76 ||
       sprite->x1>sprite->x2 || sprite->y1<0 ||
       sprite->y2>=44 || sprite->y1>sprite->y2 ||
       !sprite->depth_units)return 0;
    uint16_t emitted=0;
    for(uint16_t x=(uint16_t)sprite->x1;x<=(uint16_t)sprite->x2;x++){
        r46_p4_sprite_post_t post;
        if(R46_P4_SpriteVisiblePost(x,sprite,ceilingclip,floorclip,
                                    solid,wall_depth,&post)){
            emit(x,post.top,post.bottom,ctx);
            emitted++;
        }
    }
    return emitted;
}
typedef struct {
    uint16_t (*emit)(const r46_p4_sprite_rect_t*,const int16_t*,
      const int16_t*,const uint8_t*,const uint16_t*,
      r46_p4_sprite_post_emit_t,void*);
} r46_p4_sprite_runs_ops_t;
static const r46_p4_sprite_runs_ops_t runs_ops={R46_P4_EmitSpritePosts};
__attribute__((noinline))
const r46_p4_sprite_runs_ops_t *R46_P4_SpriteRunsOps(void)
{
    return &runs_ops;
}
__attribute__((noinline))
uint16_t R46_P4_SpriteRunsValidate(void)
{
    const r46_p4_sprite_runs_ops_t *ops=R46_P4_SpriteRunsOps();
    return (uint16_t)(ops&&ops->emit);
}
#endif
