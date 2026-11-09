/* N3 lockstep wire format (MD <-> Sega CD sub), on top of the S1 transport (scd_proto.h).
 * MD -> sub (FRAME response payload): N3PayHead, [N3SnapHead + player_t], ntics x N3_TIC_BYTES.
 * sub -> MD (in the bank the sub filled before requesting FRAME): N3FrameHead at N3_HDR_OFFSET,
 * the R128 Pair-V buffer (3344 B) at SCD_FRAME_OFFSET. */
#ifndef DOOM_N3_PROTO_H
#define DOOM_N3_PROTO_H
#include <stdint.h>
#define N3_PAY_MAGIC 0x4E33u
#define N3_FR_MAGIC 0x4E334652UL
#define N3_MAX_TICS 32u
#define N3_TIC_BYTES 8u
#define N3_HDR_OFFSET 0x0F00u
#define N3_CMD_POOL 9u                 /* sub -> MD: send the resident R84 wall-texture pool */
#define N3_POOL_OFFSET 0x10200UL       /* pool copy in both Word RAM banks (above any lump payload) */
#define N3_F_SNAP 1u   /* level (re)load: snapshot follows, sub runs G_DoLoadLevel */
#define N3_F_STOP 2u
#define N3_F_NORENDER 4u   /* run the tics now, no frame wanted (exchange B: next frame's logic) */   /* MD left lockstep (menu-less non-level state, demo, desync) */
typedef struct { uint16_t magic, flags, ntics, snaplen, x0, x1; } N3PayHead;   /* x0..x1: sub render window */
typedef struct {
    int16_t gamemap, gameskill;
    uint8_t respawnmonsters, usergame, prnd, menuactive;
    int32_t gametic, basetic;
} N3SnapHead;
typedef struct {
    uint32_t magic;
    uint16_t valid, lock;
    int32_t gametic, x, y;
    uint32_t angle;
    uint32_t render_units, tic_units, frames;
    uint16_t lump_misses, error;
    uint32_t idle_units;   /* sub clock units spent waiting in its previous exchange */
    uint16_t prnd, health;
} N3FrameHead;
#endif
