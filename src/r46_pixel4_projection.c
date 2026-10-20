/* Exact unmodified 4x4 R22 horizontal projection lookup data kept in ROM.
 * The 8x8 R39f compiler still owns global r_draw.c projection tables.
 * This module introduces no mutable/zero-initialized state.
 */
#if defined(DOOM_R46_M2A)
#include <stdint.h>
#include "r46_pixel4_projection.h"
#if !defined(DOOM_R46_M1B) || !defined(DOOM_R46_M1) || defined(DOOM_R22_PIXEL4)
#error R46 M2A needs the dual-linked R39f 8x8 executable with M1B native P4 modules
#endif

static const uint16_t r46_p4_xtoviewangle[77] = {
#include "r22_xtoviewangle.h"
};
static const uint8_t r46_p4_viewangletox[R46_P4_VIEWANGLETOX_COUNT] = {
#include "r22_viewangletox.h"
};
_Static_assert(sizeof(r46_p4_xtoviewangle) / sizeof(r46_p4_xtoviewangle[0]) == 77,
               "R22 X angle table differs from 77 (right-edge sentinel)");
_Static_assert(sizeof(r46_p4_viewangletox) == 2032,
               "R22 fine-angle projection table differs from 2032 bytes");

__attribute__((noinline))
uint8_t R46_P4_ViewAngleToX(uint16_t va)
{
    va &= 4095u;
    if(va < R46_P4_VIEWANGLETOXMAX)return R46_P4_VIEWWIDTH;
    if(va >= R46_P4_VIEWANGLETOX_END)return 0;
    return r46_p4_viewangletox[va - R46_P4_VIEWANGLETOXMAX];
}
__attribute__((noinline))
int16_t R46_P4_XToViewAngle(uint16_t x)
{
    if(x > R46_P4_VIEWWIDTH)return 0;
    return (int16_t)r46_p4_xtoviewangle[x];
}
__attribute__((noinline))
uint16_t R46_P4_ProjectionValidate(void)
{
    /* Read from ROM (without modifying projection/clip state). The
     * exact 76-column data will later feed M2 specialized geometry. */
    if(R46_P4_XToViewAngle(0)!=8192 ||
       R46_P4_XToViewAngle(38)!=0 ||
       R46_P4_XToViewAngle(76)!=-8192)return 0;
    if(R46_P4_ViewAngleToX(0)!=76 ||
       R46_P4_ViewAngleToX(1041)!=75 ||
       R46_P4_ViewAngleToX(3072)!=0 ||
       R46_P4_ViewAngleToX(3073)!=0)return 0;
    return 1;
}
#endif
