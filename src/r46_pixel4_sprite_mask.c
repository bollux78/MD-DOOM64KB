/* R46 M2C/P2G: multi-window sprite clipping from supplied row mask.
 * Geometry only; a future renderer must generate occlusion from drawsegs.
 */
#if defined(DOOM_R46_M2C)
#include "r46_pixel4_sprite_mask.h"
#if !defined(DOOM_R46_M2B) || defined(DOOM_R22_PIXEL4)
#error P2G mask helper requires M2B coexistence
#endif
uint16_t R46_P4_EmitMaskedPosts(uint16_t x,
    const r46_p4_sprite_rect_t *sprite,uint64_t occluded_rows,
    r46_p4_mask_emit_t emit,void *ctx)
{
    if(!sprite||!emit||x>=76||sprite->x1<0||sprite->x2>=76||
       sprite->x1>sprite->x2||sprite->y1<0||sprite->y2>=44||
       sprite->y1>sprite->y2||x<(uint16_t)sprite->x1||
       x>(uint16_t)sprite->x2||!sprite->depth_units)return 0;
    uint16_t y=(uint16_t)sprite->y1,stop=(uint16_t)sprite->y2;
    uint16_t runs=0;
    while(y<=stop){
        while(y<=stop && (occluded_rows & (((uint64_t)1)<<y)))y++;
        if(y>stop)break;
        const uint16_t first=y;
        while(y<=stop && !(occluded_rows & (((uint64_t)1)<<y)))y++;
        emit(x,first,(uint16_t)(y-1),ctx);
        runs++;
    }
    return runs;
}
typedef struct {
    uint16_t (*emit)(uint16_t,const r46_p4_sprite_rect_t*,
                    uint64_t,r46_p4_mask_emit_t,void*);
} r46_p4_mask_ops_t;
static const r46_p4_mask_ops_t r46_p4_mask_ops={R46_P4_EmitMaskedPosts};
__attribute__((noinline))
const r46_p4_mask_ops_t *R46_P4_SpriteMaskOps(void){return &r46_p4_mask_ops;}
__attribute__((noinline))
uint16_t R46_P4_SpriteMaskValidate(void)
{
    const r46_p4_mask_ops_t *o=R46_P4_SpriteMaskOps();
    return (uint16_t)(o&&o->emit);
}
#endif
