/* R46 M2C/P2B: no persistent 4x4 plane storage.
 * The future native renderer must provide scratch and own its lifetime.
 */
#ifndef R46_P4_PLANE_OWNER_H
#define R46_P4_PLANE_OWNER_H
#include <stdint.h>
enum { R46_P4_PLANE_WIDTH=76, R46_P4_PLANE_HEIGHT=44 };
typedef struct {
    /* Guard cells top[0] and top[77] allow x-1 and stop=76. */
    uint8_t top[78];
    uint8_t bottom[78];
    int16_t minx,maxx;
} r46_p4_plane_window_t;
typedef void (*r46_p4_range_emit_t)(uint16_t first,uint16_t stop,void *ctx);
#if defined(DOOM_R46_M2C)
void R46_P4_PlaneInit(r46_p4_plane_window_t *plane);
uint16_t R46_P4_PlaneJoin(r46_p4_plane_window_t *plane,
                          int16_t start,int16_t stop);
uint16_t R46_P4_PlaneSetColumn(r46_p4_plane_window_t *plane,
                               uint16_t x,uint8_t top,uint8_t bottom);
/* BSP input [first,stop) in 0..76; emits maximal open runs without mutation.
 * Return number of emitted runs (or 0 for no open runs/invalid inputs). */
uint16_t R46_P4_BSPOpenRuns(const uint8_t solid[76],
        uint16_t first,uint16_t stop,r46_p4_range_emit_t emit,void *ctx);
uint16_t R46_P4_PlaneOwnerValidate(void);
#endif
#endif
