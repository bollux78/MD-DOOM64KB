/* Native Manifold checkpoint storage for Mega EverDrive X-series SSF mode.
 * The X7 exposes 256 KiB SRAM in the UPPER half of virtual bank 31.
 * Slot 5 is used here because it is bank 5 in the M14 layouts.
 * Source: https://blog.roberthargreaves.com/2025/03/10/sram-and-everdrives
 *
 * IMPORTANT: do NOT call while another code path is executing from slot 5.
 * All accesses mask interrupts, stop Z80 if needed, and restore bank 5.
 * Firmware/physical SRAM persistence is not verified until X7 testing.
 */
#ifndef M14_SRAM_H
#define M14_SRAM_H
typedef unsigned short m14_sw;
typedef unsigned long m14_dw;
typedef struct { m14_sw w[32]; } m14_checkpoint;
#define M14_SRAM_WORDS ((volatile m14_sw *)0x002c0000UL)
#define M14_CTRL0 (*(volatile m14_sw *)0x00a130f0UL)
#define M14_CTRL5 (*(volatile m14_sw *)0x00a130faUL)
#define M14_Z80BUS (*(volatile m14_sw *)0x00a11100UL)
#define M14_REC_MAGIC 0x4d53
#define M14_REC_VERSION 1
#define M14_REC_GUARD 0xa55a
#define M14_REC_WORDS 32
#define M14_LOAD_MAGIC 0x4c44
#define M14_REQ_OFFSET 80

typedef struct { m14_sw old_sr; m14_sw had_z80_bus; } m14_sram_guard;
static m14_sram_guard m14_sram_enter(int writing) {
    m14_sram_guard ctx;
    __asm volatile("move.w %%sr,%0" : "=d"(ctx.old_sr));
    __asm volatile("move.w #0x2700,%%sr" : : : "memory");
    ctx.had_z80_bus = (M14_Z80BUS & 0x0100) == 0;
    if (!ctx.had_z80_bus) {
        int to = 300;    /* Z80 held in RESET never acknowledges the request: it is not using the bus, so go on */
        M14_Z80BUS = 0x0100;
        while ((M14_Z80BUS & 0x0100) && --to) { }
    }
    M14_CTRL0 = writing ? 0xa000 : 0x8000; /* unlock / write enable */
    M14_CTRL5 = 31;  /* slot $280000-$2fffff maps bank 31 */
    return ctx;
}
static void m14_sram_leave(m14_sram_guard ctx) {
    M14_CTRL5 = 5;   /* restore M14 identity slot 5 */
    M14_CTRL0 = 0x8000;  /* write protect before continuing */
    if (!ctx.had_z80_bus) M14_Z80BUS = 0;
    __asm volatile("move.w %0,%%sr" : : "d"(ctx.old_sr) : "memory");
}
static m14_sw m14_cksum(const m14_checkpoint *r) {
    m14_sw a = 0xd0a6;
    int i;
    for (i = 1; i <= 29; i++) {
        a = (m14_sw)((a << 5) | (a >> 11));
        a ^= r->w[i];
    }
    return a;
}
static int m14_rec_valid(const m14_checkpoint *r) {
    m14_sw c = m14_cksum(r);
    return (r->w[0] == M14_REC_MAGIC &&
            r->w[1] == M14_REC_VERSION && r->w[3] < 9 &&
            r->w[10] < 1024 &&
            r->w[12] <= 200 && r->w[13] <= 200 &&
            r->w[29] <= 8 &&
            r->w[30] == c && r->w[31] == (m14_sw)(c ^ M14_REC_GUARD));
}
static void m14_read_slot(int slot, m14_checkpoint *dst) {
    int i;
    for (i = 0; i < 32; i++)
        dst->w[i] = M14_SRAM_WORDS[slot * 32 + i];
}
static int m14_latest(m14_checkpoint *r, m14_checkpoint *other) {
    int va = m14_rec_valid(r), vb = m14_rec_valid(other);
    if (!va && !vb) return -1;
    if (!va) return 1;
    if (!vb) return 0;
    return ((short)(other->w[2] - r->w[2]) > 0) ? 1 : 0;
}
/* Returns 1 only after checksum/version/magic verification in SRAM. */
static int m14_sram_load(m14_checkpoint *dst) {
    m14_checkpoint a, b;
    m14_sram_guard ctx = m14_sram_enter(0);
    m14_read_slot(0, &a);
    m14_read_slot(1, &b);
    m14_sram_leave(ctx);
    int best = m14_latest(&a, &b);
    if (best < 0) return 0;
    *dst = best ? b : a;
    return 1;
}
/* Two alternating records. Never invalidate the previous verified slot. */
static int m14_sram_save(m14_checkpoint *src) {
    m14_checkpoint a, b, verify;
    int i;
    m14_sram_guard ctx = m14_sram_enter(1);
    m14_read_slot(0, &a);
    m14_read_slot(1, &b);
    int best = m14_latest(&a, &b);
    int target = (best < 0) ? 0 : (best ^ 1);
    src->w[0] = M14_REC_MAGIC;
    src->w[1] = M14_REC_VERSION;
    src->w[2] = (best < 0) ? 1 : (m14_sw)((best ? b.w[2] : a.w[2]) + 1);
    src->w[30] = m14_cksum(src);
    src->w[31] = src->w[30] ^ M14_REC_GUARD;
    /* commit magic last. Old slot is never overwritten. */
    M14_SRAM_WORDS[target * 32] = 0;
    for (i = 1; i < 32; i++)
        M14_SRAM_WORDS[target * 32 + i] = src->w[i];
    M14_SRAM_WORDS[target * 32] = src->w[0];
    m14_read_slot(target, &verify);
    m14_sram_leave(ctx);
    if (!m14_rec_valid(&verify)) return 0;
    for (i = 0; i < 32; i++)
        if (verify.w[i] != src->w[i]) return 0;
    return 1;
}
/* A load request survives the warm reboot into the SGDK map image.
 * Record remains valid if power is lost before the map loads. */
static int m14_sram_request(m14_sw mapid) {
    m14_checkpoint saved;
    if (!m14_sram_load(&saved) || saved.w[3] != mapid) return 0;
    m14_sram_guard ctx = m14_sram_enter(1);
    M14_SRAM_WORDS[M14_REQ_OFFSET + 0] = 0;
    M14_SRAM_WORDS[M14_REQ_OFFSET + 1] = mapid;
    M14_SRAM_WORDS[M14_REQ_OFFSET + 2] = saved.w[2];
    M14_SRAM_WORDS[M14_REQ_OFFSET + 3] = mapid ^ saved.w[2] ^ 0x5a3c;
    M14_SRAM_WORDS[M14_REQ_OFFSET + 0] = M14_LOAD_MAGIC;
    int ok = M14_SRAM_WORDS[M14_REQ_OFFSET + 0] == M14_LOAD_MAGIC;
    m14_sram_leave(ctx);
    return ok;
}
static int m14_sram_take_request(m14_sw expected_map) {
    m14_sw mark, map, seq, check;
    m14_sram_guard ctx = m14_sram_enter(1);
    mark = M14_SRAM_WORDS[M14_REQ_OFFSET + 0];
    map = M14_SRAM_WORDS[M14_REQ_OFFSET + 1];
    seq = M14_SRAM_WORDS[M14_REQ_OFFSET + 2];
    check = M14_SRAM_WORDS[M14_REQ_OFFSET + 3];
    /* Regardless of validity, consume once to prevent boot loops. */
    M14_SRAM_WORDS[M14_REQ_OFFSET + 0] = 0;
    m14_sram_leave(ctx);
    if (mark != M14_LOAD_MAGIC || map != expected_map ||
        check != (m14_sw)(map ^ seq ^ 0x5a3c)) return 0;
    m14_checkpoint saved;
    return m14_sram_load(&saved) && saved.w[3] == map && saved.w[2] == seq;
}
#endif
