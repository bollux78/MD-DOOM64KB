/* R46 M3C: separate boot-only dual bank VDP diagnostic.
 * NOT called by normal renderer, PERF control or playable 8x8 build. */
#ifndef R46_M3C_VIDEO_HEADER_H
#define R46_M3C_VIDEO_HEADER_H
#include <stdint.h>
#if defined(DOOM_R46_M3C_DIAG)
void R46_M3C_ShowVideoTest(uint16_t *shared_backing,
                           void (*reload_cell_tiles)(void),
                           void (*restore_cell_palette)(void));
#endif
#endif
