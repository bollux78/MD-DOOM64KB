/* One snapshot shared by conversion and publication; all values are tile units. */
typedef struct {uint8_t y0,y1,x0,x1;} r92_rect_t;
static r92_rect_t r92_rect={1,22,0,38};
static uint8_t r92_shadow_on;
uint8_t R92_ShadowOn(void){return r92_shadow_on;}
static void R92_Snapshot(void){
    r92_rect=(r92_rect_t){1,22,0,38};
#if defined(DOOM_R57_CROP16)
    if(r57_queued_crop)r92_rect=(r92_rect_t){R57_TILE_YMIN,R57_TILE_YEND,R57_TILE_XMIN,R57_TILE_XEND};
#endif
}
static void R92_RestoreAttributes(void){
    uint16_t *p=(uint16_t *)(void *)r22_fb.pixels;
    for(uint16_t y=1;y<22;y++)for(uint16_t x=0;x<38;x++){
        uint16_t *a=p+y*76+x,*b=a+38;
        *a=(*a&255u)|0x0100u;*b=(*b&255u)|0x2200u;
    }
}
void R92_SetShadow(uint8_t on){
    R20_StopVideo();on=(on!=0);
    if(r92_shadow_on && !on)R92_RestoreAttributes();
    r92_shadow_on=on;
    /* Existing menu-exit path reloads CRAM with the active effect palette.
       Also request refresh for callers outside the menu. */
    r59_color_dirty=1;
}
void __attribute__((noinline,used)) R92_AfterPass(void){__asm__ volatile("":::"memory");}
static void R92_ShadowPass(uint16_t *pixels,const uint32_t *table,
    const uint16_t maps[2][2][256],const uint16_t costs[2][2][256],uint8_t palette)
{
    for(uint16_t y=r92_rect.y0;y<r92_rect.y1;y++){
        uint16_t *a=pixels+y*76,*b=a+38;
        for(uint16_t x=r92_rect.x0;x<r92_rect.x1;x++){
            uint16_t ca=a[x]&255u,cb=b[x]&255u;
            if(!palette){uint32_t pair=table[(ca<<8)|cb];a[x]=pair>>16;b[x]=(uint16_t)pair;}
            else{
                uint32_t n=(uint32_t)costs[0][0][ca]+costs[0][1][cb];
                uint32_t s=(uint32_t)costs[1][0][ca]+costs[1][1][cb];
                uint16_t state=s<n;a[x]=maps[state][0][ca];b[x]=maps[state][1][cb];
            }
        }
    }
}
