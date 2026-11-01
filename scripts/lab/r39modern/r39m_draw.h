/* R39f tile-word scene writer. GPL-2.0-or-later. */
#ifndef R39M_DRAW_H
#define R39M_DRAW_H
#include <stdint.h>
extern const int16_t CENTERY;
static inline int R39M_Clip(int16_t x,int16_t *lo,int16_t *hi)
{
    if((uint16_t)x>=38u)return 0;
    int16_t a=0,b=22;
    if(_g_gamestate==GS_LEVEL){
        if(x<r57_view.xmin/2 || x>=r57_view.xend/2)return 0;
        a=r57_view.ymin/2;b=r57_view.yend/2;
    }
    if(*lo<a)*lo=a;
    if(*hi>=b)*hi=b-1;
    return *lo<=*hi;
}
static inline void R39M_Fill(uint8_t *fb,int16_t x,int16_t lo,int16_t hi,uint16_t cell)
{
    uint16_t *dst=(uint16_t *)(void *)fb+(uint16_t)lo*38u+(uint16_t)x;
    uint16_t n=(uint16_t)(hi-lo);
#if defined(__m68k__)
    __asm__ volatile("1: move.w %2,(%0)\n\tadda.w #76,%0\n\tdbra %1,1b"
        : "+&a"(dst),"+&d"(n):"d"(cell):"cc","memory");
#else
    do{*dst=cell;dst+=38;}while(n--);
#endif
}
static inline void R39M_Texture(uint8_t *fb,const draw_column_vars_t *v,
    const uint16_t *map,const uint16_t *colors,const uint8_t *shade)
{
    int16_t lo=v->yl,hi=v->yh;
    if(!R39M_Clip(v->x,&lo,&hi))return;
    uint16_t frac=(uint16_t)((v->texturemid>>7)+(lo-CENTERY)*v->fracstep);
    uint16_t *dst=(uint16_t *)(void *)fb+(uint16_t)lo*38u+(uint16_t)v->x;
    uint16_t n=(uint16_t)(hi-lo);
#if defined(__m68k__)
    if(map){
        /* Original R20/R39 ADDX pixel kernel, 76-byte tile-word row stride. */
        uint16_t ip=frac,fl=frac,si=v->fracstep,sl=si,tmp;
        __asm__ volatile(
            "lsl.w #7,%[fl]\n\trol.w #7,%[ip]\n\tand.w %[k],%[ip]\n\t"
            "lsl.w #7,%[sl]\n\trol.w #7,%[si]\n\tand.w %[k],%[si]\n"
            "1: moveq #0,%[t]\n\tmove.b (%[s],%[ip].w),%[t]\n\t"
            "add.w %[t],%[t]\n\tmove.w (%[m],%[t].w),(%[d])\n\t"
            "lea 76(%[d]),%[d]\n\tadd.w %[sl],%[fl]\n\t"
            "addx.w %[si],%[ip]\n\tand.w %[k],%[ip]\n\tdbra %[n],1b"
            :[d]"+&a"(dst),[fl]"+&d"(fl),[ip]"+&d"(ip),[sl]"+&d"(sl),
             [si]"+&d"(si),[n]"+&d"(n),[t]"=&d"(tmp)
            :[s]"a"(v->source),[m]"a"(map),[k]"d"((uint16_t)127):"cc","memory");
        return;
    }
#endif
    do{
        uint8_t c=v->source[frac>>9];
        if(map)*dst=map[c];else{if(shade)c=shade[c];*dst=colors[c];}
        dst+=38;frac=(uint16_t)(frac+v->fracstep);
    }while(n--);
}
#endif
