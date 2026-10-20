/* R46 M2C/P2A: host-testable native row span lifecycle and BSP mask.
 * Deliberately no persistent buffers. Call only from the future 4x4
 * renderer owner after acquiring exclusive scratch/framebuffer ownership.
 */
#if defined(DOOM_R46_M2C)
#include "r46_pixel4_spans.h"
#if !defined(DOOM_R46_M2B) || defined(DOOM_R22_PIXEL4)
#error Native span helpers require M2B coexistence with the 8x8 renderer
#endif
_Static_assert(R46_P4_SPAN_COLS==76 && R46_P4_SPAN_ROWS==44,"P4 span geometry drift");
void R46_P4_SpansClear(uint8_t starts[44],uint8_t solid[76])
{
    if(starts)for(uint16_t i=0;i<44;i++)starts[i]=0xffu;
    if(solid)for(uint16_t i=0;i<76;i++)solid[i]=0;
}
uint16_t R46_P4_MarkSolid(uint8_t solid[76],int16_t first,int16_t stop)
{
    if(!solid||stop<=first||stop<=0||first>=76)return 0;
    if(first<0)first=0;
    if(stop>76)stop=76;
    uint16_t added=0;
    for(int16_t i=first;i<stop;i++){
        if(!solid[i])added++;
        solid[i]=1;
    }
    return added;
}
uint16_t R46_P4_MakeSpans(uint8_t starts[44],uint16_t x,
    uint16_t t1,uint16_t b1,uint16_t t2,uint16_t b2,
    r46_p4_span_emit_t emit,void *ctx)
{
    if(!starts||!emit||x>76||t1>44||t2>44||b1>=44||b2>=44)return 0;
    /* Doom uses top=0xff, bottom=0 for the empty boundary.
     * Normalize that sentinel into an empty interval [44,0]. */
    uint16_t emitted=0;
    if(t1==44)b1=0;
    if(t2==44)b2=0;
    while(t1<t2 && t1<=b1){
        if(starts[t1]==0xffu||starts[t1]>=x)return 0;
        emit(t1,starts[t1],(uint16_t)(x-1),ctx);emitted++;t1++;
    }
    while(b1>b2 && b1>=t1){
        if(starts[b1]==0xffu||starts[b1]>=x)return 0;
        emit(b1,starts[b1],(uint16_t)(x-1),ctx);emitted++;b1--;
    }
    while(t2<t1 && t2<=b2)starts[t2++]=(uint8_t)x;
    while(b2>b1 && b2>=t2)starts[b2--]=(uint8_t)x;
    return emitted;
}
__attribute__((noinline))
uint16_t R46_P4_SpansValidate(void)
{
    return (uint16_t)(R46_P4_SPAN_COLS==76 && R46_P4_SPAN_ROWS==44);
}
#endif
