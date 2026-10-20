/* R46 M2C/P2H: independent pixel4 geometry assembly, no 8x8 calls.
 * Not connected to Doom drawseg/VDP/heap. All arrays caller-owned.
 */
#if defined(DOOM_R46_M2C)
#include "r46_pixel4_pipeline.h"
#if !defined(DOOM_R46_M2B) || defined(DOOM_R22_PIXEL4)
#error P2H requires M2B coexistence without activating R22_PIXEL4
#endif
_Static_assert(R46_P4_PLANE_WIDTH==76 && R46_P4_SPAN_ROWS==44,
               "P2H native viewport mismatch");
uint16_t R46_P4_SweepPlane(const r46_p4_plane_window_t *p,
    uint8_t starts[44],r46_p4_span_emit_t emit,void *ctx)
{
    if(!p||!starts||!emit||p->minx<0||p->maxx>=76||
       p->minx>p->maxx)return 0;
    /* Reject malformed top/bottom columns before emitting any spans. */
    for(int16_t x=p->minx;x<=p->maxx;x++){
        uint8_t top=p->top[x+1],bottom=p->bottom[x+1];
        if(top!=0xffu && (top>=44||bottom>=44||top>bottom))return 0;
    }
    uint16_t total=0;
    for(uint16_t x=(uint16_t)p->minx;x<=(uint16_t)(p->maxx+1);x++){
        uint16_t t1=p->top[x], b1=p->bottom[x];
        uint16_t t2=p->top[x+1],b2=p->bottom[x+1];
        if(t1==0xffu){t1=44;b1=0;}
        if(t2==0xffu){t2=44;b2=0;}
        total=(uint16_t)(total+R46_P4_MakeSpans(starts,x,
                         t1,b1,t2,b2,emit,ctx));
    }
    return total;
}
typedef struct {
    r46_p4_pipeline_post_emit_t emit;
    void *ctx;
    uint16_t sprite_id;
} r46_p4_post_bridge_t;
static void bridge_post(uint16_t x,uint16_t y0,uint16_t y1,void *ptr)
{
    r46_p4_post_bridge_t *b=(r46_p4_post_bridge_t *)ptr;
    b->emit(b->sprite_id,x,y0,y1,b->ctx);
}
uint16_t R46_P4_EmitOrderedSpriteScene(
    const r46_p4_sprite_rect_t *sprites,const uint16_t *depth,
    uint16_t count,uint8_t *order,r46_p4_mask_lookup_t mask_lookup,
    r46_p4_pipeline_post_emit_t emit,void *ctx)
{
    if(!sprites||!depth||!order||!mask_lookup||!emit||
       count==0||count>128)return 0;
    for(uint16_t i=0;i<count;i++){
        const r46_p4_sprite_rect_t *p=&sprites[i];
        if(!depth[i] || p->depth_units!=depth[i]||
           p->x1<0 || p->x2>=76 || p->x1>p->x2 ||
           p->y1<0 || p->y2>=44 || p->y1>p->y2)return 0;
    }
    if(R46_P4_SortSprites(depth,count,order)!=count)return 0;
    uint16_t total=0;
    r46_p4_post_bridge_t bridge={emit,ctx,0};
    for(uint16_t i=0;i<count;i++){
        uint16_t id=order[i];
        const r46_p4_sprite_rect_t *p=&sprites[id];
        bridge.sprite_id=id;
        for(uint16_t x=(uint16_t)p->x1;x<=(uint16_t)p->x2;x++){
            uint64_t mask=mask_lookup(id,x,ctx);
            total=(uint16_t)(total+R46_P4_EmitMaskedPosts(
                x,p,mask,bridge_post,&bridge));
        }
    }
    return total;
}
typedef struct {
    uint16_t (*plane)(const r46_p4_plane_window_t*,uint8_t*,
                      r46_p4_span_emit_t,void*);
    uint16_t (*sprites)(const r46_p4_sprite_rect_t*,const uint16_t*,
                        uint16_t,uint8_t*,r46_p4_mask_lookup_t,
                        r46_p4_pipeline_post_emit_t,void*);
} r46_p4_pipeline_ops_t;
static const r46_p4_pipeline_ops_t pipeline_ops={
    R46_P4_SweepPlane,R46_P4_EmitOrderedSpriteScene
};
__attribute__((noinline))
const r46_p4_pipeline_ops_t *R46_P4_PipelineOps(void){return &pipeline_ops;}
__attribute__((noinline))
uint16_t R46_P4_PipelineValidate(void)
{
    const r46_p4_pipeline_ops_t *o=R46_P4_PipelineOps();
    return (uint16_t)(o && o->plane && o->sprites);
}
#endif
