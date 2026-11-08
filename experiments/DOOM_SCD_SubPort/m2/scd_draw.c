/* N1: Sega CD native column output. Replaces the MD pixel4 back end (i_genesisv.c / r22_video.inc)
 * on the sub-CPU. Same column math as R22 (frac = texturemid>>7 + (y-CENTERY)*fracstep, texel =
 * source[frac>>9]), same colour mapping (colormap -> r22_color nibble), but the output is one byte
 * per logical pixel in scd_fb (76x44). A later pass expands scd_fb into the linear 4bpp bitmap that
 * the Mega-CD 1M cell-image view turns into VDP tiles (proved by N0).
 * Not yet: R49 colormix attributes, R56/R59 dual colour tables, fuzz effect (drawn as dark). */
#include <stdint.h>
#include "doomdef.h"
#include "doomtype.h"
#include "m_fixed.h"
#include "r_main.h"
#include "r22_pixel4.h"
#include "r22_palette.h"   /* r22_color (PLAYPAL -> 16 colours) and r22_cram */

#ifndef CENTERY
#define CENTERY (R22_H / 2)   /* 22, as the R22 back end */
#endif
#define SCD_W R22_W
#define SCD_H R22_H
uint8_t scd_fb[SCD_H][SCD_W];
uint32_t scd_columns, scd_pixels;
/* Sub stopwatch (30.72 us units, 12-bit, wraps ~125.8 ms): polled from every column so long
 * frames never lose a wrap. */
uint32_t scd_clock_units, scd_column_units;
static uint16_t scd_clock_prev;
void SCD_ClockPoll(void)
{
    const uint16_t now = *(volatile const uint16_t *)0xFF800CUL & 4095u;
    scd_clock_units += (uint16_t)(now - scd_clock_prev) & 4095u;
    scd_clock_prev = now;
}

static void column(const draw_column_vars_t *v, const uint8_t *map)
{
    SCD_ClockPoll();
    const uint32_t c0 = scd_clock_units;
    int16_t x = v->x, y0 = v->yl, y1 = v->yh;
    if ((uint16_t)x >= SCD_W || y1 < y0) return;
    int16_t first = y0 < 0 ? 0 : y0;
    if (y1 >= SCD_H) y1 = SCD_H - 1;
    if (first > y1) return;
    uint16_t frac = (uint16_t)((v->texturemid >> 7) + (y0 - CENTERY) * v->fracstep);
    frac = (uint16_t)(frac + (uint16_t)((uint32_t)(uint16_t)(first - y0) * v->fracstep));
    const uint16_t step = v->fracstep;
    const uint8_t *src = v->source, *cm = v->colormap;
    uint8_t *d = &scd_fb[first][x];
    for (int16_t y = first; y <= y1; y++)
    {
        uint8_t c = src[frac >> 9];
        if (cm) c = cm[c];
        *d = map[c] & 15u;
        d += SCD_W;
        frac = (uint16_t)(frac + step);
    }
    scd_columns++; scd_pixels += (uint32_t)(y1 - first + 1);
    SCD_ClockPoll();
    scd_column_units += scd_clock_units - c0;
}

void R_DrawColumnWall(const draw_column_vars_t *v) { column(v, r22_color); }
void R_DrawColumnSprite(const draw_column_vars_t *v) { column(v, r22_color); }
void R_DrawFuzzColumn(const draw_column_vars_t *v)
{
    draw_column_vars_t dark = *v;
    dark.colormap = fullcolormap + 20 * 256;   /* simplified spectre: dark copy */
    column(&dark, r22_color);
}
void R_DrawColumnFlat(uint8_t c, const draw_column_vars_t *v)
{
    int16_t x = v->x, y0 = v->yl, y1 = v->yh;
    if ((uint16_t)x >= SCD_W || y1 < y0) return;
    if (y0 < 0) y0 = 0;
    if (y1 >= SCD_H) y1 = SCD_H - 1;
    const uint8_t n = r22_color[c] & 15u;
    uint8_t *d = &scd_fb[y0][x];
    for (int16_t y = y0; y <= y1; y++, d += SCD_W) *d = n;
    scd_columns++; scd_pixels += (uint32_t)(y1 - y0 + 1);
}
