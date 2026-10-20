/* R46 M2C/P2C: native 76x44 camera-space sprite geometry.
 * Input coordinates are signed Q16.16 in Doom world units.
 * Pure calculations: no global buffers, renderer ownership, VDP or WAD.
 */
#ifndef R46_PIXEL4_SPRITE_CAMERA_H
#define R46_PIXEL4_SPRITE_CAMERA_H
#include <stdint.h>
typedef struct {
    int16_t x1,x2,y1,y2; /* inclusive clipped view coordinates */
    uint16_t depth_units; /* integer part of tz in world units */
} r46_p4_sprite_rect_t;
#if defined(DOOM_R46_M2C)
/* tx is left edge in camera coordinates, tz is depth, width and top/bottom
 * are signed camera-relative world values. top_z>=bottom_z.
 * Returns 1 for a nonempty visible projection; leaves output untouched
 * on rejection. This is geometry only, not patch selection or column draw. */
uint16_t R46_P4_ProjectSpriteRect(int32_t tx,int32_t tz,
    int32_t width,int32_t top_z,int32_t bottom_z,
    uint16_t gameplay,r46_p4_sprite_rect_t *out);
uint16_t R46_P4_SpriteCameraValidate(void);
#endif
#endif
