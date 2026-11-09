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
#define REG16(a) (*(volatile uint16_t *)(uintptr_t)(a))
#define BANK ((volatile uint8_t *)SCD_SUB_BANK_BASE)

extern void SCD_SubTransportReset(void), SCD_SubSetTime(uint32_t);
extern const volatile uint8_t *SCD_SubExchange(uint16_t command, uint16_t argument, uint16_t *length);
extern void N3_SetCmd(const void *c), N3_LoadLevel(void), N3_SetPRnd(uint8_t v);
extern uint8_t *N2_DrawBuffer(void);


uint32_t scd_clock_units, scd_column_units;
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
    _g_gametic = h.gametic; _g_basetic = h.basetic;
    N3_SetPRnd(h.prnd);
    _g_gameaction = ga_nothing;
    N3_LoadLevel();
}

void sub_main(void)
{
    REG16(0xFF8002UL) = 4; SCD_SubTransportReset(); REG16(0xFF8020UL) = 0x5343u;
    Z_Init(); W_Init(); R_Init(); P_Init(); SCD_SubSetTime(0);
    uint16_t lock = 0, valid = 0, frame = 0;
    uint32_t render_units = 0, tic_units = 0;
    for (;;)
    {
        volatile N3FrameHead *fh = (volatile N3FrameHead *)(BANK + N3_HDR_OFFSET);
        fh->magic = N3_FR_MAGIC; fh->valid = valid; fh->lock = lock;
        fh->gametic = _g_gametic;
        fh->x = _g_player.mo ? _g_player.mo->x : 0; fh->y = _g_player.mo ? _g_player.mo->y : 0;
        fh->angle = _g_player.mo ? _g_player.mo->angle : 0;
        fh->render_units = render_units; fh->tic_units = tic_units; fh->frames = frame;
        if (valid)
        {
            const uint8_t *s = N2_DrawBuffer();
            volatile uint8_t *d = BANK + SCD_FRAME_OFFSET;
            for (uint16_t i = 1; i < SCD_FRAME_BYTES; i += 2) d[i] = s[i];
        }
        uint16_t len = 0;
        const volatile uint8_t *p = SCD_SubExchange(SCD_CMD_FRAME, ++frame, &len);
        if (!p || len < sizeof(N3PayHead) || len > sizeof pay) I_Error("N3 FRAME EXCHANGE %u", (unsigned)len);
        for (uint16_t i = 0; i < len; i++) pay[i] = p[i];
        N3PayHead h; memcpy(&h, pay, sizeof h);
        if (h.magic != N3_PAY_MAGIC || h.ntics > N3_MAX_TICS) I_Error("N3 BAD PAYLOAD");
        const uint8_t *q = pay + sizeof h;
        valid = 0; render_units = tic_units = 0;
        SCD_ClockPoll(); uint32_t t0 = scd_clock_units;
        if (h.flags & N3_F_STOP) lock = 0;
        if (h.flags & N3_F_SNAP)
        {
            if (h.snaplen != sizeof(N3SnapHead) + sizeof(player_t)) I_Error("N3 SNAPSHOT SIZE %u", (unsigned)h.snaplen);
            apply_snapshot(q); q += h.snaplen; lock = 1;
        }
        uint16_t ran = 0;
        for (uint16_t t = 0; t < h.ntics && lock; t++, q += N3_TIC_BYTES)
        {
            if (_g_gameaction != ga_nothing || _g_gamestate != GS_LEVEL) { lock = 0; break; }
            N3_SetCmd(q); _g_menuactive = q[7];
            G_Ticker(); _g_gametic++; ran++;
            SCD_ClockPoll();
        }
        SCD_ClockPoll(); tic_units = scd_clock_units - t0;
        if (lock && _g_gamestate == GS_LEVEL && _g_gameaction == ga_nothing && (ran || (h.flags & N3_F_SNAP)))
        {
            t0 = scd_clock_units;
            R_RenderPlayerView(&_g_player);
            SCD_ClockPoll(); render_units = scd_clock_units - t0;
            valid = 1;
        }
    }
}
