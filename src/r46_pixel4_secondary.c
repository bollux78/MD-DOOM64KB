/* R46 M1: second 4x4 packed renderer co-linked with the R39f 8x8
 * renderer, but deliberately not enabled for VDP presentation yet.
 *
 * IMPORTANT: _s_screen (38x28 16-bit tilemap = 2128 bytes) is shared
 * backing memory. While mode 8x8 runs this module must not draw/clear
 * pixels. A later M2/M3 transition will retire pending VDP operations,
 * switch geometry and grant ownership of this buffer to native 4x4.
 *
 * This does not reuse R20_REG_COLUMNS or FLAT_INLINE (8x8 word-tile asm).
 * R42 wall ASM writes one packed 4bpp nibble at a time into a framebuffer
 * with 38-byte stride, exactly as the approved R44 76x44 backend.
 */
#if defined(DOOM_R46_M1)
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include "r46_pixel4_secondary.h"
#include "r22_pixel4.h"
#include "r22_palette.h"
#include "globdata.h"
#include "doomdef.h"

#if !defined(DOOM_R20_REG_COLUMNS) || !defined(DOOM_R39F_DITHER3)
#error R46 M1 secondary module requires R39f primary 8x8 cell kernel
#endif
#if defined(DOOM_R22_PIXEL4)
#error R46 M1 requires primary cell renderer; pixel4 geometry comes later
#endif

/* R20 asm references global _s_screen; never hide or relocate its symbol. */
extern uint16_t _s_screen[38 * 28];
enum { R46_CELL_BACKING_BYTES = 38 * 28 * 2, R46_P4_CENTERY = 22 };
_Static_assert(R46_CELL_BACKING_BYTES >= R22_FB_BYTES,
    "Secondary pixel4 must share the existing 8x8 tilemap memory");
_Static_assert(R22_FB_BYTES == 1672 && R22_PITCH == 38,
    "R44 pixel4 framebuffer format changed");
_Static_assert(sizeof(_s_screen) == R46_CELL_BACKING_BYTES,
    "R20 backing buffer size changed");

static inline uint8_t *R46_P4_Pixels(void)
{
    return (uint8_t *)(void *)_s_screen;
}
static inline void R46_P4_Plot(int16_t x,int16_t y,uint8_t color)
{
    if((uint16_t)x >= R22_W || (uint16_t)y >= R22_H) return;
    if(_g_gamestate == GS_LEVEL && (x<2 || y<2)) return;
    R22_Put(R46_P4_Pixels(),(uint16_t)x,(uint16_t)y,color);
}

/* Only the forthcoming mode dispatcher may call clear when pixel4
 * exclusively owns the shared tilemap/packed frame buffer. */
static void R46_P4_Clear(void)
{
    memset(R46_P4_Pixels(),0,R22_FB_BYTES);
}

static void R46_P4_Sprite(const draw_column_vars_t *v)
{
    int16_t n=v->yh-v->yl+1;
    if(n<=0)return;
    uint16_t frac=(uint16_t)((v->texturemid>>7)+(v->yl-R46_P4_CENTERY)*v->fracstep);
    for(int16_t y=v->yl;y<=v->yh;y++) {
        uint8_t c=v->source[frac>>9];
        if(v->colormap)c=v->colormap[c];
        R46_P4_Plot(v->x,y,r22_color[c]);
        frac=(uint16_t)(frac+v->fracstep);
    }
}

static void R46_P4_Wall(const draw_column_vars_t *v)
{
    /* Identical clipping and fraction adjustment to R42/R44 ASM,
     * specialized for 76x44 instead of current 8x8 CENTERY=11. */
    int16_t x=v->x, y0=v->yl, y1=v->yh;
    if(y1<y0 || (uint16_t)x>=R22_W)return;
    int16_t border=(_g_gamestate==GS_LEVEL)?2:0;
    if(x<border)return;
    int16_t first=y0;
    if(first<border)first=border;
    if(y1>=R22_H)y1=R22_H-1;
    if(first>y1)return;
    uint16_t frac=(uint16_t)((v->texturemid>>7)+(y0-R46_P4_CENTERY)*v->fracstep);
    frac=(uint16_t)(frac+(uint16_t)((uint32_t)(uint16_t)(first-y0)*(uint32_t)v->fracstep));
    const uint16_t step=v->fracstep;
    const uint8_t *source=v->source,*colormap=v->colormap;
    uint8_t *dst=R46_P4_Pixels()+(uint16_t)first*R22_PITCH+((uint16_t)x>>1);
    int16_t remaining=(int16_t)(y1-first+1);
    if(x&1){
        do {
            uint8_t ci=source[frac>>9];
            if(colormap)ci=colormap[ci];
            uint8_t c=(uint8_t)(r22_color[ci]&15);
            __asm__ volatile(
                "move.b (%[ptr]),%%d0\n\t"
                "andi.b #0xf0,%%d0\n\t"
                "or.b %[col],%%d0\n\t"
                "move.b %%d0,(%[ptr])"
                :: [ptr] "a" (dst), [col] "d" (c)
                : "d0","cc","memory");
            dst+=R22_PITCH; frac=(uint16_t)(frac+step);
        }while(--remaining);
    }else{
        do {
            uint8_t ci=source[frac>>9];
            if(colormap)ci=colormap[ci];
            uint8_t c=(uint8_t)((r22_color[ci]&15)<<4);
            __asm__ volatile(
                "move.b (%[ptr]),%%d0\n\t"
                "andi.b #0x0f,%%d0\n\t"
                "or.b %[col],%%d0\n\t"
                "move.b %%d0,(%[ptr])"
                :: [ptr] "a" (dst), [col] "d" (c)
                : "d0","cc","memory");
            dst+=R22_PITCH; frac=(uint16_t)(frac+step);
        }while(--remaining);
    }
}
static void R46_P4_Flat(uint8_t color,const draw_column_vars_t *v)
{
    color=r22_color[color];
    for(int16_t y=v->yl;y<=v->yh;y++)R46_P4_Plot(v->x,y,color);
}
static uint32_t R46_P4_ExpandPair(uint8_t value)
{
    return R22_ExpandPair(value);
}

/* These entry points MUST remain callable via the ops address returned
 * to the 8x8 primary, otherwise the linker may strip unused functions.
 * No writes are performed by obtaining/validating this table. */
static const r46_p4_ops_t r46_p4_ops = {
    R22_W,R22_H,R22_PITCH,R22_FB_BYTES,R46_CELL_BACKING_BYTES,
    R46_P4_Clear,R46_P4_Wall,R46_P4_Sprite,R46_P4_Flat,R46_P4_ExpandPair
};

__attribute__((noinline))
const r46_p4_ops_t *R46_P4_Ops(void) { return &r46_p4_ops; }
__attribute__((noinline))
uint16_t R46_P4_Validate(void)
{
    const r46_p4_ops_t *p=R46_P4_Ops();
    return (uint16_t)(p->width==76 && p->height==44 && p->pitch==38
          && p->frame_bytes==1672 && p->backing_bytes==2128
          && p->clear!=0 && p->wall!=0 && p->sprite!=0 && p->flat!=0
          && p->expand_pair!=0);
}
#endif
