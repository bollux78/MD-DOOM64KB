/* Persistent telemetry + SRAM benchmark records (test ROM "tele").
 * Shared by the game (common block) and the bare-metal menu.
 * All functions need the SRAM window opened with m14_sram_enter().
 * Layout (16-bit words in the X7 SRAM window):
 *   256 + map*32 : per-map telemetry record (32 words)
 *  1024          : canary/boot-counter record (32 words)
 *  1056          : benchmark results record (32 words)
 *  2048..2303    : scratch area for the write/readback pattern test
 */
#ifndef M14_TELE_H
#define M14_TELE_H
#include "m14_sram.h"
#define M14T_BASE 256
#define M14T_STRIDE 32
#define M14T_MAGIC 0x5454
#define M14T_VER 1
#define M14T_CANARY 1024
#define M14T_BENCH 1056
#define M14T_SCRATCH 2048
typedef struct { m14_sw w[32]; } m14_tele_rec;
enum { T_MAGIC = 0, T_VER = 1, T_SESS = 2, T_FH = 3, T_FL = 4, T_TH = 5, T_TL = 6,
       T_B0 = 7, /* 7..11: frames with >=30, >=20, >=15, >=10, <10 fps */
       T_DTMAX = 12, T_STK = 13, T_HEAP = 14, T_DEPTH = 15, T_TRIPS = 16, T_CK = 30, T_GD = 31 };
static m14_sw m14t_ck(const m14_tele_rec *r) {
    m14_sw a = 0x7e1e;
    int i;
    for (i = 1; i <= 29; i++) { a = (m14_sw)((a << 5) | (a >> 11)); a ^= r->w[i]; }
    return a;
}
static int m14t_valid(const m14_tele_rec *r) {
    m14_sw c = m14t_ck(r);
    return r->w[T_MAGIC] == M14T_MAGIC && r->w[T_VER] == M14T_VER &&
           r->w[T_CK] == c && r->w[T_GD] == (m14_sw)(c ^ M14_REC_GUARD);
}
static void m14t_read(int base, m14_tele_rec *r) {
    int i;
    for (i = 0; i < 32; i++) r->w[i] = M14_SRAM_WORDS[base + i];
}
static void m14t_write(int base, m14_tele_rec *r) {   /* commit magic last */
    int i;
    r->w[T_CK] = m14t_ck(r);
    r->w[T_GD] = (m14_sw)(r->w[T_CK] ^ M14_REC_GUARD);
    M14_SRAM_WORDS[base] = 0;
    for (i = 1; i < 32; i++) M14_SRAM_WORDS[base + i] = r->w[i];
    M14_SRAM_WORDS[base] = r->w[0];
}
#endif
