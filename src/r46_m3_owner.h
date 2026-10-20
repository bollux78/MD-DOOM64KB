/* R46 M3A: explicit caller-owned renderer/VDP handoff protocol.
 * Pure state machine: callers must REALLY stop and drain DMA/ISR and
 * reconfigure VRAM/CRAM before acknowledging; no hardware writes here.
 * No global state, heap, or premature 4x4 activation.
 */
#ifndef R46_M3_OWNER_PROTOCOL_H
#define R46_M3_OWNER_PROTOCOL_H
#include <stdint.h>
enum { R46_M3_CELL=0, R46_M3_PIXEL4=1 };
enum { R46_M3_ACTIVE=0, R46_M3_QUIESCE=1, R46_M3_RECONFIGURE=2 };
enum {
    R46_M3_DMA_DRAINED=1u,
    R46_M3_IRQ_DISABLED=2u,
    R46_M3_VRAM_READY=4u,
    R46_M3_CRAM_READY=8u,
    R46_M3_MAP_READY=16u,
    R46_M3_QUIESCE_ALL=3u,
    R46_M3_RECONFIG_ALL=28u
};
typedef struct {
    uint16_t owner,desired,phase,acknowledged,epoch;
} r46_m3_owner_t;
#if defined(DOOM_R46_M2C)
void R46_M3_OwnerInit(r46_m3_owner_t *state);
uint16_t R46_M3_Request(r46_m3_owner_t *state,uint16_t new_owner);
/* Quiesce acknowledgments are legal only in QUIESCE phase and must be
 * supplied AFTER DMA drain / IRQ stop have really finished. */
uint16_t R46_M3_AckQuiesce(r46_m3_owner_t *state,uint16_t flags);
/* VRAM/CRAM/tile-map acknowledgments require both quiescence flags.
 * The caller is responsible for real VDP writes and completion barriers. */
uint16_t R46_M3_AckReconfigure(r46_m3_owner_t *state,uint16_t flags);
uint16_t R46_M3_Commit(r46_m3_owner_t *state);
/* Abort is safe only before any VDP reconfiguration has begun. */
uint16_t R46_M3_AbortQuiesce(r46_m3_owner_t *state);
uint16_t R46_M3_MayWrite(const r46_m3_owner_t *state,uint16_t owner);
uint16_t R46_M3_OwnerValidate(void);
#endif
#endif
