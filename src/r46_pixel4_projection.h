/* R46 M2A: native 76x44 horizontal projection ROM tables.
 * Completely separate from R39f 38x22 viewangletox / xtoviewangle.
 * NO additional WRAM tables. No geometry mode dispatch enabled yet.
 * Exact original R22 data is included from src/r22_* generated headers.
 */
#ifndef R46_P4_PROJECTION_H
#define R46_P4_PROJECTION_H
#include <stdint.h>
enum {
    R46_P4_VIEWWIDTH = 76,
    R46_P4_VIEWHEIGHT = 44,
    R46_P4_HALFHEIGHT = 22,
    R46_P4_VIEWANGLETOXMAX = 1041,
    R46_P4_VIEWANGLETOX_END = 3073,
    R46_P4_VIEWANGLETOX_COUNT = 4096-1023-R46_P4_VIEWANGLETOXMAX
};
#if defined(DOOM_R46_M2A)
/* Fine-angle argument is 0..4095, same as original viewangletox.
 * x (0..75) yields signed angle in 16-bit units.
 * No per-column runtime 8x8/4x4 conditionals are introduced. */
uint8_t R46_P4_ViewAngleToX(uint16_t fine_angle);
int16_t R46_P4_XToViewAngle(uint16_t x);
uint16_t R46_P4_ProjectionValidate(void);
#endif
#endif
