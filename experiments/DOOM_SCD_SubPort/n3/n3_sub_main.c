/* N3 sub program: the R128 engine (SRAM-in-RAM model, R128 Pair-V drawers) runs the same game
 * logic as the MD in lockstep and renders the view. Loop: publish header + last frame in our
 * Word RAM bank, request FRAME, receive snapshot/ticcmds, run them, render. */
#include <stdint.h>
#include "doomdef.h"
#include "d_player.h"
#include "d_ticcmd.h"
#include "globdata.h"
#include "g_game.h"
#include "p_setup.h"
#include "r_main.h"
#include "w_wad.h"
#include "z_zone.h"
#include "i_system.h"
#include "scd_proto.h"
#include "n3_proto.h"
#include "r84_columns.h"
#define REG16(a) (*(volatile uint16_t *)(uintptr_t)(a))
#define BANK ((volatile uint8_t *)SCD_SUB_BANK_BASE)

extern void SCD_SubTransportReset(void), SCD_SubSetTime(uint32_t);
extern const volatile uint8_t *SCD_SubExchange(uint16_t command, uint16_t argument, uint16_t *length);
extern void N3_SetCmd(const void *c), N3_LoadLevel(void), N3_SetPRnd(uint8_t v);
extern uint8_t *N2_DrawBuffer(void);


uint32_t scd_clock_units, scd_column_units;
uint8_t n3_demoplayback;   /* MD's demoplayback for game logic (the sub itself never reads the demo) */
static int16_t win_x0 = 0, win_x1 = 76;
int16_t N3_X0(void) { return win_x0; }
int16_t N3_X1(void) { return win_x1; }
static uint16_t scd_clock_prev;
void SCD_ClockPoll(void)
{
    const uint16_t now = *(volatile const uint16_t *)0xFF800CUL & 4095u;
    scd_clock_units += (uint16_t)(now - scd_clock_prev) & 4095u;
    scd_clock_prev = now;
}

static uint8_t pay[sizeof(N3PayHead) + sizeof(N3SnapHead) + sizeof(player_t) + N3_MAX_TICS * N3_TIC_BYTES + 16];

static void apply_snapshot(const uint8_t *p)
{
    N3SnapHead h; memcpy(&h, p, sizeof h);
    memcpy(&_g_player, p + sizeof h, sizeof(player_t));
    /* MD pointers are meaningless here; P_SpawnPlayer/P_SetupPsprites rebuild the rest. */
    _g_player.mo = 0; _g_player.attacker = 0; _g_player.message = 0;
    _g_gamemap = h.gamemap; _g_gameskill = (skill_t)h.gameskill;
    _g_respawnmonsters = h.respawnmonsters; _g_usergame = h.usergame;
    _g_menuactive = h.menuactive; _g_demoplayback = 0;
    { extern uint8_t n3_demoplayback; n3_demoplayback = h.demoplayback; }
    _g_gametic = h.gametic; _g_basetic = h.basetic;
    N3_SetPRnd(h.prnd);
    _g_gameaction = ga_nothing;
    { extern void SCD_WadFlushToMark(void); SCD_WadFlushToMark(); }
    N3_LoadLevel();
    { extern void SCD_WadLevelDone(void); SCD_WadLevelDone(); }
}

void sub_main(void)
{
    REG16(0xFF8002UL) = 4; SCD_SubTransportReset(); REG16(0xFF8020UL) = 0x5343u;
    Z_Init(); W_Init();
    /* R84 wall pool (all maps) into both Word RAM banks: each exchange swaps the bank we see */
    for (uint16_t k = 0; k < 2u; k++)
    {
        uint16_t len = 0;
        const volatile uint8_t *pp = SCD_SubExchange(N3_CMD_POOL, k, &len);
        if (!pp || len != N3_POOL_BYTES) I_Error("N3 POOL %u", (unsigned)len);
        const volatile uint16_t *ps = (const volatile uint16_t *)pp;
        volatile uint16_t *d = (volatile uint16_t *)(BANK + N3_POOL_OFFSET);
        for (uint16_t i = 0; i < (uint16_t)((len + 1u) >> 1); i++) d[i] = ps[i];
    }
    R_Init(); P_Init(); SCD_SubSetTime(0);
    { extern void SCD_WadMark(void); SCD_WadMark(); }
    uint16_t lock = 0, valid = 0, frame = 0, first_tic = 0, rnd_fixes = 0;
    uint32_t render_units = 0, tic_units = 0, idle_units = 0;
    for (;;)
    {
        volatile N3FrameHead *fh = (volatile N3FrameHead *)(BANK + N3_HDR_OFFSET);
        fh->magic = N3_FR_MAGIC; fh->valid = valid; fh->lock = lock;
        fh->gametic = _g_gametic;
        fh->x = _g_player.mo ? _g_player.mo->x : 0; fh->y = _g_player.mo ? _g_player.mo->y : 0;
        fh->angle = _g_player.mo ? _g_player.mo->angle : 0;
        fh->render_units = render_units; fh->tic_units = tic_units; fh->frames = frame; fh->idle_units = idle_units; { extern uint8_t N3_GetPRnd(void); fh->prnd = N3_GetPRnd(); } fh->health = (uint16_t)_g_player.health; fh->lump_misses = rnd_fixes;
        if (valid)
        {
            /* only our window's sample bytes (MD merges exactly these) */
            const uint8_t *s0 = N2_DrawBuffer();
            for (uint16_t par = 0; par < 2u; par++)
            {
                int16_t xs = win_x0 + ((win_x0 & 1) != (int16_t)par);
                if (xs >= win_x1) continue;
                const uint16_t first = (uint16_t)(par * 76u + (uint16_t)(xs >> 1) * 2u + 1u);
                const uint16_t n = (uint16_t)((win_x1 - xs + 1) >> 1);
                for (uint16_t y = 0; y < 22u; y++)
                {
                    const uint8_t *sp = s0 + y * 152u + first;
                    volatile uint8_t *dp = BANK + SCD_FRAME_OFFSET + y * 152u + first;
                    for (uint16_t k = n; k; k--) { *dp = *sp; dp += 2; sp += 2; }
                }
            }
        }
        uint16_t len = 0;
        SCD_ClockPoll(); const uint32_t w0 = scd_clock_units;
        const volatile uint8_t *p = SCD_SubExchange(SCD_CMD_FRAME, ++frame, &len);
        SCD_ClockPoll(); idle_units = scd_clock_units - w0;
        if (!p || len < sizeof(N3PayHead) || len > sizeof pay) I_Error("N3 FRAME EXCHANGE %u", (unsigned)len);
        for (uint16_t i = 0; i < len; i++) pay[i] = p[i];
        N3PayHead h; memcpy(&h, pay, sizeof h);
        if (h.magic != N3_PAY_MAGIC || h.ntics > N3_MAX_TICS) I_Error("N3 BAD PAYLOAD");
        const uint8_t *q = pay + sizeof h;
        win_x0 = (int16_t)h.x0; win_x1 = (int16_t)h.x1;
        if (win_x0 < 0 || win_x0 > 76 || win_x1 < win_x0 || win_x1 > 76) { win_x0 = 0; win_x1 = 76; }
        valid = 0; render_units = tic_units = 0;
        SCD_ClockPoll(); uint32_t t0 = scd_clock_units;
        if (h.flags & N3_F_STOP) lock = 0;
        if (h.flags & N3_F_SNAP)
        {
            if (h.snaplen != sizeof(N3SnapHead) + sizeof(player_t)) I_Error("N3 SNAPSHOT SIZE %u", (unsigned)h.snaplen);
            apply_snapshot(q); q += h.snaplen; lock = 1;
        }
        uint16_t ran = 0;
        if (h.flags & N3_F_SNAP) first_tic = 1;
        for (uint16_t t = 0; t < h.ntics && lock; t++, q += N3_TIC_BYTES)
        {
            if (_g_gameaction != ga_nothing || _g_gamestate != GS_LEVEL) { lock = 0; break; }
            { /* The MD may reset the RNG after a level load (demo start does): adopt the MD's P_Random
               * index at every tic start; real logic divergence still shows up in the x/y/health check. */
              extern uint8_t N3_GetPRnd(void);
              if (N3_GetPRnd() != q[6]) { if (!first_tic) rnd_fixes++; N3_SetPRnd(q[6]); }
              first_tic = 0; }
            N3_SetCmd(q); _g_menuactive = q[7];
            G_Ticker(); _g_gametic++; ran++;
            SCD_ClockPoll();
        }
        SCD_ClockPoll(); tic_units = scd_clock_units - t0;
        if (!(h.flags & N3_F_NORENDER) && lock && _g_gamestate == GS_LEVEL && _g_gameaction == ga_nothing)
        {
            t0 = scd_clock_units;
            R_RenderPlayerView(&_g_player);
            SCD_ClockPoll(); render_units = scd_clock_units - t0;
            valid = 1;
        }
    }
}
