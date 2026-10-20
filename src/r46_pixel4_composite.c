/* R46 M2C/P2I: host-testable 76x44 compositor. No active video writes.
 * Raster destination is exclusively caller-owned, never _s_screen here.
 */
#if defined(DOOM_R46_M2C)
#include "r46_pixel4_composite.h"
#if !defined(DOOM_R46_M2B) || defined(DOOM_R22_PIXEL4)
#error P2I native compositor coexists with active R39f 8x8
#endif
typedef struct {
    uint8_t *pixels;
    uint16_t capacity, keep_rows;
    uint8_t plane_color;
    const uint8_t *sprite_colors;
    r46_p4_mask_lookup_t lookup;
    void *lookup_context;
    uint16_t spans,posts;
} r46_p4_compositor_context_t;
static void plane_cb(uint16_t y,uint16_t x1,uint16_t x2,void *ptr)
{
    r46_p4_compositor_context_t *c=(r46_p4_compositor_context_t *)ptr;
    if(y<c->keep_rows)return;
    if(R46_P4_FillRow(c->pixels,c->capacity,y,x1,x2,c->plane_color))
        c->spans++;
}
static uint64_t mask_cb(uint16_t sprite_id,uint16_t x,void *ptr)
{
    r46_p4_compositor_context_t *c=(r46_p4_compositor_context_t *)ptr;
    const uint64_t reserved=((uint64_t)1<<c->keep_rows)-1u;
    return c->lookup(sprite_id,x,c->lookup_context)|reserved;
}
static void sprite_cb(uint16_t sprite_id,uint16_t x,
                      uint16_t y1,uint16_t y2,void *ptr)
{
    r46_p4_compositor_context_t *c=(r46_p4_compositor_context_t *)ptr;
    if(R46_P4_FillColumn(c->pixels,c->capacity,x,y1,y2,
                         c->sprite_colors[sprite_id]))
        c->posts++;
}
uint16_t R46_P4_ComposePreview(uint8_t *target,uint16_t capacity,
    const r46_p4_plane_window_t *plane,uint8_t starts[44],
    uint8_t background,uint8_t plane_color,uint16_t keep_rows,
    const r46_p4_sprite_rect_t *sprites,const uint16_t *depth,
    const uint8_t *sprite_colors,uint16_t count,uint8_t *indices,
    r46_p4_mask_lookup_t lookup,void *lookup_ctx,
    r46_p4_composite_stats_t *stats)
{
    if(!target||capacity<R46_P4_RASTER_BYTES||!plane||!starts||!stats||
       background>15||plane_color>15||keep_rows>=44||count>128)return 0;
    const uint16_t empty=(uint16_t)(plane->minx==76&&plane->maxx==-1);
    if(!empty){
        if(plane->minx<0||plane->maxx>=76||plane->minx>plane->maxx)
            return 0;
        if(plane->top[plane->minx]!=0xffu ||
           plane->top[plane->maxx+2]!=0xffu)return 0;
        for(int16_t x=plane->minx;x<=plane->maxx;x++){
            uint8_t t=plane->top[x+1],b=plane->bottom[x+1];
            if(t!=0xffu&&(t>=44||b>=44||t>b))return 0;
        }
    }
    if(count){
        if(!sprites||!depth||!sprite_colors||!indices||!lookup)return 0;
        for(uint16_t i=0;i<count;i++){
            const r46_p4_sprite_rect_t *p=&sprites[i];
            if(p->x1<0||p->x2>=76||p->x1>p->x2||
               p->y1<0||p->y2>=44||p->y1>p->y2||
               !depth[i]||p->depth_units!=depth[i]||
               sprite_colors[i]>15)return 0;
        }
    }
    r46_p4_compositor_context_t c={
        target,capacity,keep_rows,plane_color,
        sprite_colors,lookup,lookup_ctx,0,0
    };
    if(!R46_P4_ClearTarget(target,capacity,background,keep_rows))return 0;
    for(uint16_t y=0;y<44;y++)starts[y]=0xffu;
    if(!empty)R46_P4_SweepPlane(plane,starts,plane_cb,&c);
    if(count)R46_P4_EmitOrderedSpriteScene(sprites,depth,count,indices,
                                           mask_cb,sprite_cb,&c);
    stats->plane_spans=c.spans;
    stats->sprite_posts=c.posts;
    return 1;
}
typedef struct {
    uint16_t (*compose)(uint8_t*,uint16_t,const r46_p4_plane_window_t*,
        uint8_t*,uint8_t,uint8_t,uint16_t,const r46_p4_sprite_rect_t*,
        const uint16_t*,const uint8_t*,uint16_t,uint8_t*,
        r46_p4_mask_lookup_t,void*,r46_p4_composite_stats_t*);
} r46_p4_composite_ops_t;
static const r46_p4_composite_ops_t compose_ops={R46_P4_ComposePreview};
__attribute__((noinline))
const r46_p4_composite_ops_t *R46_P4_CompositeOps(void){return &compose_ops;}
__attribute__((noinline))
uint16_t R46_P4_CompositeValidate(void)
{
    const r46_p4_composite_ops_t *o=R46_P4_CompositeOps();
    return (uint16_t)(o && o->compose && R46_P4_RASTER_BYTES==1672);
}
#endif
