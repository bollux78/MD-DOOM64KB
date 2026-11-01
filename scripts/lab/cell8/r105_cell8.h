/* R105 cell8: one scene sample per 8x8 tile. GPL-2.0-or-later. */
#ifndef R105_CELL8_H
#define R105_CELL8_H
#include <stdint.h>
/* This header is included after draw_column_vars_t, viewport and game state declarations. */
extern const int16_t CENTERY;
static inline int R105_CellClip(int16_t x,int16_t *y0,int16_t *y1)
{
    if((uint16_t)x>=38u) return 0;
    int16_t lo=0,hi=22;
    if(_g_gamestate==GS_LEVEL) {
        if(x<r57_view.xmin/2 || x>=r57_view.xend/2) return 0;
        lo=r57_view.ymin/2; hi=r57_view.yend/2;
    }
    if(*y0<lo)*y0=lo;
    if(*y1>=hi)*y1=hi-1;
    return *y0<=*y1;
}
static inline int R105_CellVisible(int16_t x,int16_t y)
{
    int16_t lo=y,hi=y;
    return R105_CellClip(x,&lo,&hi);
}
static inline void R105_CellStore(uint8_t *fb,int16_t x,int16_t y,uint8_t a,uint8_t b)
{
    uint8_t *d=fb+(uint16_t)y*152u+(uint16_t)x*2u+1u;
    d[0]=(uint8_t)((a&15u)*17u);
    d[76]=(uint8_t)((b&15u)*17u);
}
static inline void R105_CellFill(uint8_t *fb,int16_t x,int16_t y0,int16_t y1,uint8_t a,uint8_t b)
{
    uint8_t *d=fb+(uint16_t)y0*152u+(uint16_t)x*2u+1u;
    a=(uint8_t)((a&15u)*17u); b=(uint8_t)((b&15u)*17u);
    for(int16_t y=y0;y<=y1;y++,d+=152) { d[0]=a; d[76]=b; }
}
static inline void R105_CellTexture(uint8_t *fb,const draw_column_vars_t *v,
    const uint8_t *even,const uint8_t *odd,const uint8_t *colormap)
{
    int16_t y0=v->yl,y1=v->yh;
    if(!R105_CellClip(v->x,&y0,&y1)) return;
    uint16_t f=(uint16_t)((v->texturemid>>7)+(y0-CENTERY)*v->fracstep);
    uint8_t *d=fb+(uint16_t)y0*152u+(uint16_t)v->x*2u+1u;
    for(int16_t y=y0;y<=y1;y++,d+=152,f=(uint16_t)(f+v->fracstep)) {
        uint8_t c=v->source[f>>9]; if(colormap)c=colormap[c];
        d[0]=(uint8_t)((even[c]&15u)*17u);
        d[76]=(uint8_t)((odd[c]&15u)*17u);
    }
}
#endif
