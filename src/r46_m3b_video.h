/* R46 M3B isolated diagnostic: real VDP pixel4 presentation at boot.
 * Only the special video-test ROM may call this. It returns to R39f
 * after a bounded visual test, leaving gameplay in original 8x8 mode.
 */
#ifndef R46_M3B_VIDEO_HEADER_H
#define R46_M3B_VIDEO_HEADER_H
#include <stdint.h>
#if defined(DOOM_R46_M3B_DIAG)
void R46_M3B_ShowVideoTest(uint16_t *shared_backing,
                           void (*reload_cell_tiles)(void),
                           void (*restore_cell_palette)(void));
#endif
#endif
