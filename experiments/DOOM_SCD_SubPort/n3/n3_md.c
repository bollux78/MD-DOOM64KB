/* N3 MD side, linked into the R128 game. The Sega CD sub runs the same Doom logic in lockstep
 * (same ticcmds, deterministic like a demo) and renders the 3D view with the R128 Pair-V drawers;
 * the MD keeps everything else (input, menus, HUD, sound, presentation) and shows the sub's frame
 * instead of calling R_RenderPlayerView. One frame of view latency buys full parallelism.
 * Any problem (no Sega CD, sub error, desync, timeout) falls back to the plain R128 renderer. */
#include <stddef.h>
#include <stdint.h>
#include <genesis.h>
#include "doomdef.h"
#include "d_player.h"
#include "d_ticcmd.h"
#include "globdata.h"
#include "w_wad.h"
#include "z_zone.h"
#include "scd_proto.h"
#include "n3_proto.h"
#include "n3_sub.h"

#define HW_VERSION (*(volatile const u8 *)0xA10001)
#define CD_BIOS_HEADER (*(volatile const u32 *)0x400100)
#define CD_SUB_BYTE (*(volatile u8 *)0xA12001)
#define CD_MEMCTRL (*(volatile u16 *)0xA12002)
#define CD_MEMCTRL_LO (*(volatile u8 *)0xA12003)
#define CD_MAIN_SWAP (*(volatile u16 *)0xA12018)
#define CD_SUB_SIG (*(volatile const u16 *)0xA12020)
#define CD_PRGRAM ((volatile u16 *)0x420000)

extern void SCD_MdServeReset(void);
extern int16_t SCD_MdServeOnce(void);
extern uint16_t SCD_MdPendingCmd(void);
extern uint8_t *N2_DrawBuffer(void);
extern void N3_GetCmd(void *out);
extern uint8_t N3_GetPRnd(void);
extern volatile uint32_t _g_vblankCount;

typedef struct {
    uint8_t active, lock, snap_pending, have_frame;
    uint16_t ntics, seq;
    uint32_t frames_sub, frames_md, desyncs, timeouts, wait_vblanks, exchanges, sub_render_units, sub_tic_units;
    int32_t chk_gametic, chk_x, chk_y; uint32_t chk_angle; uint8_t chk_valid, prev_valid, last_error, pad;
    /* N3_VERIFY: the sub's frame of the same game state vs the MD's own R128 render (offset 60). */
    uint32_t verify_frames, verify_diff_bytes, verify_max, verify_zero;
    uint8_t *verify_buf;
    /* split screen: MD renders [md_x0, split), the sub renders [split, 76) of the same state */
    int16_t split, md_x0, md_x1; uint8_t expect_frame, rendering;
    uint32_t split_sum, wait_b_vblanks, md_render_vblanks;
    uint8_t early, pad2[3];
    int16_t split_fp; uint16_t pad3; uint32_t sub_idle_units;
    /* first desync: MD reference vs sub report */
    int32_t d_tic, d_x, d_y, s_tic, s_x, s_y; uint16_t d_prnd, s_prnd, d_health, s_health;
    uint8_t chk_prnd, prev_prnd; uint16_t chk_health, prev_health;
    int32_t prev_gametic, prev_x, prev_y; uint32_t prev_angle;
    N3SnapHead snap;
    player_t snap_player;
    uint8_t tics[N3_MAX_TICS][N3_TIC_BYTES];
} N3State;
/* The only MD static of N3 (4 bytes of BSS): 0 = off, 1 = sub booted but state not allocated yet. */
static N3State *n3;
#define N3_BOOTED ((N3State *)1)

static bool wait_sub(u8 mask, u8 expected)
{
    for (u32 n = 0; n < 400000UL; n++) if ((CD_SUB_BYTE & mask) == expected) return TRUE;
    return FALSE;
}

static bool boot_sub(void)
{
    CD_MEMCTRL = 0xFF00;
    CD_SUB_BYTE = 3; CD_SUB_BYTE = 2; CD_SUB_BYTE = 0;
    for (u16 i = 0; i < 128; i++) __asm__ volatile ("nop");
    if (!wait_sub(1, 0)) return FALSE;
    CD_SUB_BYTE = 3;
    if (!wait_sub(3, 3)) return FALSE;
    CD_MEMCTRL = 0; CD_MAIN_SWAP = 0;
    u32 done = 0;
    for (u16 bank = 0; done < SUB_PROGRAM_WORDS; bank++)
    {
        CD_MEMCTRL_LO = (u8)(bank << 6);
        u32 n = SUB_PROGRAM_WORDS - done; if (n > 65536UL) n = 65536UL;
        for (u32 i = 0; i < n; i++) CD_PRGRAM[i] = sub_program[done + i];
        for (u32 i = 0; i < n; i++) if (CD_PRGRAM[i] != sub_program[done + i]) return FALSE;
        done += n;
    }
    CD_MEMCTRL_LO = 0;
    *(volatile u8 *)0xA12002 = 0xFF;   /* write-protect vectors + most of the sub code */
    CD_SUB_BYTE = 0;
    if (!wait_sub(1, 0)) return FALSE;
    CD_SUB_BYTE = 1;
    if (!wait_sub(3, 1)) return FALSE;
    for (u32 n = 0; n < 4000000UL; n++) if (CD_SUB_SIG == 0x5343u && (CD_MEMCTRL & 5u) == 4u) return TRUE;
    return FALSE;
}

/* Sub I_Error / exception: message address in $A1202A/2C; halt the sub and copy the text from
 * PRG-RAM (128 KiB window) into the MD's Word RAM bank at 0x61F100 for diagnostics. */
static void fetch_sub_error(void)
{
    const u32 addr = ((u32)*(volatile const u16 *)0xA1202A << 16) | *(volatile const u16 *)0xA1202C;
    volatile u8 *msg = (volatile u8 *)0x61F100;
    msg[0] = 0;
    *(volatile u32 *)0x61F0F8 = ((u32)*(volatile const u16 *)0xA12026 << 16) | *(volatile const u16 *)0xA12028;
    if (addr >= 0x80000UL) return;
    CD_SUB_BYTE = 3;
    if (!wait_sub(2, 2)) return;
    CD_MEMCTRL_LO = (u8)((addr >> 17) << 6);
    volatile const u8 *p = (volatile const u8 *)(0x420000UL + (addr & 0x1FFFFUL));
    u16 i = 0;
    for (; i < 39 && p[i] >= 32 && p[i] < 127; i++) msg[i] = p[i];
    msg[i] = 0;
    CD_MEMCTRL_LO = 0;
}

/* Before D_DoomMain: boot the sub and serve its engine init (WAD directory, R_Init lumps) until
 * it asks for its first FRAME, which stays pending for the first D_Display. */
void N3_Boot(void)
{
    n3 = 0;
    if ((HW_VERSION & 0x20u) || CD_BIOS_HEADER != 0x53454741UL) return;
    SYS_disableInts();
    if (boot_sub())
    {
        W_Init();
        SCD_MdServeReset();
        volatile u16 *diag = (volatile u16 *)0x61F0F0;   /* boot diagnostics in our Word RAM bank */
        diag[0] = 0xB007; diag[1] = 0; diag[2] = 0; diag[3] = 0;
        u32 spins = 0;
        for (; spins < 600000000UL; spins++)
        {
            if (CD_SUB_SIG == 0xDEADu) { diag[1] = 1; fetch_sub_error(); break; }
            const u16 cmd = SCD_MdPendingCmd();
            if (cmd == SCD_CMD_FRAME) { diag[1] = 2; n3 = N3_BOOTED; break; }
            if (!cmd) continue;   /* never call the server blind: a FRAME could slip in */
            diag[2] = cmd; diag[3] = *(volatile const u16 *)0xA12024;
            if (SCD_MdServeOnce() < 0) diag[0]++;   /* count, keep serving */
        }
        if (spins >= 600000000UL) diag[1] = 4;
    }
    SYS_enableInts();
}

static N3State *state(void)
{
    if (n3 == N3_BOOTED)
    {
        N3State *s = (N3State *)Z_MallocStatic(sizeof(N3State));
        memset(s, 0, sizeof *s);
        s->active = 1;
        s->split = 38; s->split_fp = 38 * 16;
#if defined(N3_VERIFY)
        s->verify_buf = (uint8_t *)Z_MallocStatic(SCD_FRAME_BYTES);
#endif
        n3 = s;
    }
    return n3;
}

/* Sega CD exclusive: demos (and the benchmark built on them) run in lockstep too. */
static bool user_level(void) { return _g_gamestate == GS_LEVEL; }
#define N3_DEMO_OK 1

/* G_DoLoadLevel entry (any cause: new game, next map, death): snapshot what the level load reads. */
void N3_OnLoadLevel(void)
{
    N3State *s = state();
    if (!s || !s->active) return;
    /* demos stay on the MD; the sub holds the wall textures of every map */
    if (_g_demoplayback && !N3_DEMO_OK) { s->lock = 0; s->snap_pending = 0; s->ntics = 0; return; }
    s->snap.gamemap = _g_gamemap; s->snap.gameskill = (int16_t)_g_gameskill;
    s->snap.respawnmonsters = (uint8_t)_g_respawnmonsters; s->snap.usergame = (uint8_t)_g_usergame;
    s->snap.prnd = N3_GetPRnd(); s->snap.menuactive = (uint8_t)_g_menuactive;
    s->snap.gametic = _g_gametic; s->snap.basetic = _g_basetic;
    memcpy(&s->snap_player, &_g_player, sizeof(player_t));
    s->snap_pending = 1; s->lock = 1; s->ntics = 0; s->chk_valid = 0;
}

/* After every G_Ticker: queue the ticcmd the MD just simulated. */
void N3_OnTicEnd(void)
{
    N3State *s = n3;
    if (!s || s == N3_BOOTED || !s->active || !s->lock) return;
    if (!user_level()) { s->lock = 0; s->ntics = 0; return; }
    if (s->ntics >= N3_MAX_TICS) { s->lock = 0; s->desyncs++; s->ntics = 0; return; }
    uint8_t *t = s->tics[s->ntics++];
    /* the command this tic actually used (netcmd, or the demo's): the sub feeds it as netcmd */
    memcpy(t, &_g_player.cmd, sizeof(ticcmd_t));
    t[7] = (uint8_t)_g_menuactive;
}

extern const uint16_t n3_r84_blocks[];
extern const uint16_t n3_r84_nblocks;
extern const uint8_t *N3_R84Pixels(void);
/* Server hook: the sub's R84 subset, gathered from our own pool (block 0 = missing marker). */
uint16_t N3_MdPoolPayload(volatile uint8_t *p)
{
    const uint8_t *pool = N3_R84Pixels();
    volatile uint8_t *d = p;
    for (uint16_t i = 0; i < 128u; i++) *d++ = 0xB0;
    for (uint16_t b = 0; b < n3_r84_nblocks; b++)
    {
        const uint8_t *src = pool + (uint32_t)n3_r84_blocks[b] * 128u;   /* byte copy: pool may be odd-aligned */
        for (uint16_t i = 0; i < 128u; i++) *d++ = src[i];
    }
    return (uint16_t)(128u * (n3_r84_nblocks + 1u));
}

/* Server hook: build the FRAME response (runs before the swap). */
uint16_t N3_MdFramePayload(volatile uint8_t *p)
{
    N3State *s = state();
    if (!s) return 0;
    uint16_t flags = 0, snaplen = 0;
#if defined(N3_SPLIT)
    const uint16_t norender = s->expect_frame ? N3_F_NORENDER : 0;
#else
    const uint16_t norender = 0;
#endif
    if (!s->lock) flags |= N3_F_STOP;
    else if (s->snap_pending) { flags |= N3_F_SNAP; snaplen = sizeof(N3SnapHead) + sizeof(player_t); }
    const uint16_t ntics = s->lock ? s->ntics : 0;
#if defined(N3_SPLIT)
    N3PayHead h = { N3_PAY_MAGIC, (uint16_t)(flags | norender), ntics, snaplen, (uint16_t)s->split, 76 };
#else
    N3PayHead h = { N3_PAY_MAGIC, flags, ntics, snaplen, 0, 76 };
#endif
    uint16_t o = 0;
    for (uint16_t i = 0; i < sizeof h; i++) p[o++] = ((const uint8_t *)&h)[i];
    if (snaplen)
    {
        for (uint16_t i = 0; i < sizeof(N3SnapHead); i++) p[o++] = ((const uint8_t *)&s->snap)[i];
        for (uint16_t i = 0; i < sizeof(player_t); i++) p[o++] = ((const uint8_t *)&s->snap_player)[i];
        s->snap_pending = 0;
    }
    for (uint16_t t = 0; t < ntics; t++)
        for (uint16_t i = 0; i < N3_TIC_BYTES; i++) p[o++] = s->tics[t][i];
    s->ntics = 0;
    /* What the sub must report next time: the MD state right after these tics. */
    s->prev_valid = s->chk_valid; s->prev_gametic = s->chk_gametic; s->prev_x = s->chk_x; s->prev_y = s->chk_y; s->prev_angle = s->chk_angle;
    s->prev_prnd = s->chk_prnd; s->prev_health = s->chk_health;
    s->chk_prnd = N3_GetPRnd(); s->chk_health = (uint16_t)_g_player.health;
    s->chk_valid = s->lock && _g_player.mo;
    if (s->chk_valid) { s->chk_gametic = _g_gametic; s->chk_x = _g_player.mo->x; s->chk_y = _g_player.mo->y; s->chk_angle = _g_player.mo->angle; }
    s->exchanges++;
    return o;
}

/* Server hook after the swap: the bank the sub filled (header + Pair-V frame) is ours. */
void N3_MdFrameArrived(uint16_t arg)
{
    (void)arg;
    N3State *s = n3;
    if (!s || s == N3_BOOTED) return;
    volatile const N3FrameHead *h = (volatile const N3FrameHead *)(SCD_MD_BANK_BASE + N3_HDR_OFFSET);
    if (h->magic != N3_FR_MAGIC) return;
    s->sub_render_units += h->render_units; s->sub_tic_units += h->tic_units;
    if (!s->expect_frame) s->sub_idle_units = h->idle_units;   /* A header: how long the sub waited for B */
    if (!h->valid || !s->lock || !s->prev_valid) return;
    if (h->gametic != s->prev_gametic || h->x != s->prev_x || h->y != s->prev_y || h->angle != s->prev_angle ||
        h->prnd != s->prev_prnd || h->health != s->prev_health)
    {
        if (!s->desyncs) { s->d_tic = s->prev_gametic; s->d_x = s->prev_x; s->d_y = s->prev_y; s->d_prnd = s->prev_prnd; s->d_health = s->prev_health;
                           s->s_tic = h->gametic; s->s_x = h->x; s->s_y = h->y; s->s_prnd = h->prnd; s->s_health = h->health; }
        s->desyncs++; s->lock = 0; return;       /* until the next level load */
    }
    volatile const uint8_t *src = (volatile const uint8_t *)(SCD_MD_BANK_BASE + SCD_FRAME_OFFSET);
#if defined(N3_SPLIT)
    /* Only the frame of exactly the MD's state (second exchange) is merged: the sub's columns. */
    if (!s->expect_frame) return;
    {
        uint8_t *dst = N2_DrawBuffer();
        const int16_t x0 = s->split;
        /* Pair-V rows: [even x samples][odd x samples], 2 bytes each, sample byte odd */
        for (uint16_t par = 0; par < 2u; par++)
        {
            int16_t xs = x0 + ((x0 & 1) != (int16_t)par);
            if (xs >= 76) continue;
            const uint16_t first = (uint16_t)(par * 76u + (uint16_t)(xs >> 1) * 2u + 1u);
            const uint16_t n = (uint16_t)((76 - xs + 1) >> 1);
            for (uint16_t y = 0; y < 22u; y++)
            {
                volatile const uint8_t *sp = src + y * 152u + first;
                uint8_t *dp = dst + y * 152u + first;
                for (uint16_t k = n; k; k--) { *dp = *sp; dp += 2; sp += 2; }
            }
        }
        s->have_frame = 1; s->frames_sub++;
        return;
    }
#endif
    /* Pair-V: copy only the sample bytes (odd); MD attribute bytes stay as R128 set them. */
#if defined(N3_VERIFY)
    uint8_t *dst = s->verify_buf;
#else
    uint8_t *dst = N2_DrawBuffer();
#endif
    for (uint16_t i = 1; i < SCD_FRAME_BYTES; i += 2) dst[i] = src[i];
    s->have_frame = 1;
    s->frames_sub++;
}

/* D_Display start (after R22_BeginFrame): one exchange per MD frame while the sub is alive.
 * Waits for the sub's FRAME request, serving its lump requests meanwhile. */
void N3_Pump(void)
{
    N3State *s = state();
    s = n3;
    if (!s || s == N3_BOOTED || !s->active) return;
    s->have_frame = 0;
    const uint32_t t0 = _g_vblankCount;
    for (;;)
    {
        if (CD_SUB_SIG == 0xDEADu) { fetch_sub_error(); s->active = 0; s->last_error = 1; return; }
        const uint16_t cmd = SCD_MdPendingCmd();
        if (cmd)
        {
            const int16_t r = SCD_MdServeOnce();
            if (r < 0) { s->active = 0; s->last_error = 2; return; }
            if (cmd == SCD_CMD_FRAME) break;
        }
        else if (_g_vblankCount - t0 > 60u * 8u) { s->active = 0; s->timeouts++; return; }
    }
    s->wait_vblanks += _g_vblankCount - t0;
#if defined(N3_VERIFY) && !defined(N3_SPLIT)
    /* Second exchange with no new tics: receive the frame of exactly the MD's current state. */
    if (s->lock)
        for (;;)
        {
            if (CD_SUB_SIG == 0xDEADu) { s->active = 0; s->last_error = 1; return; }
            const uint16_t cmd = SCD_MdPendingCmd();
            if (!cmd) { if (_g_vblankCount - t0 > 60u * 8u) { s->active = 0; s->timeouts++; return; } continue; }
            if (SCD_MdServeOnce() < 0) { s->active = 0; s->last_error = 2; return; }
            if (cmd == SCD_CMD_FRAME) break;
        }
#endif
}

/* Serve requests until the sub's next FRAME request has been answered (0 new tics). */
/* Time in scanlines (63.5 us): VBlank count + VDP V counter (VBlank IRQ comes at line 224). */
#ifndef N3_LATE_LINES
#define N3_LATE_LINES 100
#endif
#ifndef N3_READY_LINES
#define N3_READY_LINES 15
#endif
static uint32_t lines_now(void)
{
    for (;;)
    {
        const uint32_t vb = _g_vblankCount;
        const uint16_t v = *(volatile const uint8_t *)0xC00008;
        if (vb == _g_vblankCount) return vb * 262u + (v >= 224u ? v - 224u : v + 38u);
    }
}
static int wait_frame(N3State *s)
{
    const uint32_t t0 = _g_vblankCount;
    for (;;)
    {
        if (CD_SUB_SIG == 0xDEADu) { fetch_sub_error(); s->active = 0; s->last_error = 1; return 0; }
        const uint16_t cmd = SCD_MdPendingCmd();
        if (!cmd) { if (_g_vblankCount - t0 > 60u * 8u) { s->active = 0; s->timeouts++; return 0; } continue; }
        if (SCD_MdServeOnce() < 0) { s->active = 0; s->last_error = 2; return 0; }
        if (cmd == SCD_CMD_FRAME) return 1;
    }
}
/* Called per seg while the MD renders its window: serve the sub's lump requests right away so it
 * never stalls behind our render (FRAME requests wait for wait_frame). */
void N3_Poll(void)
{
    N3State *s = n3;
    if (!s || s == N3_BOOTED || !s->active || !s->rendering) return;
    const uint16_t cmd = SCD_MdPendingCmd();
    if (cmd && cmd != SCD_CMD_FRAME && SCD_MdServeOnce() < 0) { s->active = 0; s->last_error = 3; }
}
int16_t N3_X0(void) { N3State *s = n3; return (s && s != N3_BOOTED && s->rendering) ? s->md_x0 : 0; }
int16_t N3_X1(void) { N3State *s = n3; return (s && s != N3_BOOTED && s->rendering) ? s->md_x1 : 76; }

/* Replaces R_RenderPlayerView: 1 = the frame is already in the draw buffer. */
int N3_Display(void)
{
    N3State *s = n3;
#if defined(N3_SPLIT)
    extern uint8_t N3_ColorMode(void);
    /* the sub only has the default colour profile's tables: other modes render on the MD */
    if (s && s != N3_BOOTED && s->active && s->lock && s->chk_valid && N3_ColorMode() == N3_R59_MODE)
    {
        extern void R_RenderPlayerView(player_t *);
        /* The sub is already rendering [split, 76) of this exact state; render ours meanwhile. */
        const uint32_t t0 = _g_vblankCount;
        s->md_x0 = 0; s->md_x1 = s->split; s->rendering = 1;
        R_RenderPlayerView(&_g_player);
        s->rendering = 0;
        /* Overlap: run the next frame's game logic while the sub is still drawing its half. */
        { extern void N3_EarlyTics(void); s->early = 1; N3_EarlyTics(); }
        const uint32_t t1 = _g_vblankCount, l1 = lines_now();
        s->expect_frame = 1; s->have_frame = 0;
        const int ok = wait_frame(s);
        s->expect_frame = 0;
        const uint32_t w = _g_vblankCount - t1;
        const int32_t md_wait = (int32_t)(lines_now() - l1);
        s->md_render_vblanks += t1 - t0; s->wait_b_vblanks += w; s->split_sum += (uint32_t)s->split;
        /* Balance (measured best in BlastEm, vs finer scanline controllers): the CPU that waits
         * gets more columns next frame. */
        (void)md_wait;
        if (w > 1 && s->split < 66) s->split += 2;
        else if (w == 0 && s->split > 10) s->split -= 1;
        if (ok && s->have_frame)
        {
            s->have_frame = 0;
#if defined(N3_VERIFY)
            /* merged frame vs the MD's own full render of the same state */
            uint8_t *fb = N2_DrawBuffer();
            for (uint16_t i = 1; i < SCD_FRAME_BYTES; i += 2) s->verify_buf[i] = fb[i];
            R_RenderPlayerView(&_g_player);
            uint32_t d = 0;
            for (uint16_t i = 1; i < SCD_FRAME_BYTES; i += 2) d += fb[i] != s->verify_buf[i];
            s->verify_frames++; s->verify_diff_bytes += d; if (d > s->verify_max) s->verify_max = d; if (!d) s->verify_zero++;
#endif
            return 1;
        }
        /* No sub half: draw it ourselves. */
        s->md_x0 = s->md_x1; s->md_x1 = 76; s->rendering = 1;
        R_RenderPlayerView(&_g_player);
        s->rendering = 0; s->frames_md++;
        return 1;
    }
#endif
#if defined(N3_VERIFY)
    if (s && s != N3_BOOTED && s->have_frame)
    {
        s->have_frame = 0;
        extern void R_RenderPlayerView(player_t *);
        R_RenderPlayerView(&_g_player);
        const uint8_t *md = N2_DrawBuffer();
        uint32_t d = 0;
        for (uint16_t i = 1; i < SCD_FRAME_BYTES; i += 2) d += md[i] != s->verify_buf[i];
        s->verify_frames++; s->verify_diff_bytes += d; if (d > s->verify_max) s->verify_max = d; if (!d) s->verify_zero++;
        return 1;
    }
#endif
    if (s && s != N3_BOOTED && s->have_frame) { s->have_frame = 0; return 1; }
    if (s && s != N3_BOOTED) s->frames_md++;
    return 0;
}
void *N3_State(void) { return n3; }
/* TryRunTics: logic already ran early inside the last D_Display, do not wait for a tic. */
int N3_SkipWait(void) { N3State *s = n3; if (s && s != N3_BOOTED && s->early) { s->early = 0; return 1; } return 0; }
