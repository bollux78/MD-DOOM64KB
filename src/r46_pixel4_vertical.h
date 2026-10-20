/* R46 M2B: independent 76x44 vertical geometry contract.
 * This is NOT a second active Doom renderer. The primary R39f 8x8
 * remains responsible for every frame until M2C/M3 are validated.
 *
 * All scratch arrays belong to caller. No additional BSS for 76-column
 * clipping, sky masks, 4x4 planes or hardware HUD/sprite graphics.
 */
#ifndef R46_PIXEL4_VERTICAL_H
#define R46_PIXEL4_VERTICAL_H
#include <stdint.h>
enum {
    R46_P4_VW = 76,
    R46_P4_VH = 44,
    R46_P4_VCY = 22,
    R46_P4_CLIP_BYTES = 76*2*2,
    R46_P4_TOPBAR = 1,
    R46_P4_BORDER = 2
};
#if defined(DOOM_R46_M2B)
typedef struct {
    void (*init_opening_clips)(int16_t floorclip[76],int16_t ceilingclip[76],
                               uint16_t reserve_topbar);
    uint16_t (*clip_column)(int16_t x,int16_t *yl,int16_t *yh,
                            uint16_t gameplay);
    uint16_t (*geometry_validate)(void);
} r46_p4_vertical_ops_t;
/* Opening clips are ephemeral 76-column arrays (304 bytes total).
 * Future M2C owner must find reuse or local scratch before calling. */
void R46_P4_InitOpeningClips(int16_t floorclip[76],int16_t ceilingclip[76],
                              uint16_t reserve_topbar);
/* Returns 1 if any pixels remain, zero otherwise.
 * On failure yl/yh are left unchanged. Gameplay clips x,y<2 as R44.
 * On success yl/yh contain inclusive clipping bounds. */
uint16_t R46_P4_ClipColumn(int16_t x,int16_t *yl,int16_t *yh,uint16_t gameplay);
const r46_p4_vertical_ops_t *R46_P4_VerticalOps(void);
uint16_t R46_P4_VerticalValidate(void);
#endif
#endif
