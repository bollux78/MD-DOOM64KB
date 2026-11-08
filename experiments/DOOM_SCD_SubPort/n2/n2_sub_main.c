/* N2 sub program: the whole R128 engine (SRAM-in-RAM model) runs on the Sega CD; the MD only
 * serves the WAD and shows frames. The spawn of E1M1 is rendered 24 times by the native column
 * back end (m2/scd_draw.c); each frame is expanded to a linear 4bpp bitmap (4x4 px per sample,
 * 304x176, stride 256 B) in the sub's Word RAM bank, which the MD reads through the 1M cell view. */
#include <stdint.h>
#include "doomdef.h"
#include "globdata.h"
#include "g_game.h"
#include "p_tick.h"
#include "r_main.h"
#include "w_wad.h"
#include "z_zone.h"
#include "i_system.h"
#include "r22_pixel4.h"
#define REG16(a) (*(volatile uint16_t *)(uintptr_t)(a))
#define BANK ((volatile uint8_t *)0x0C0000UL)

extern void SCD_SubTransportReset(void), SCD_SubSetTime(uint32_t), SCD_MetadataInit(void);
extern int SCD_SubFrame(uint16_t arg, uint8_t out[16]);
extern void N2_InitGame(void), N2_SetCommand(int8_t, int8_t, int16_t, uint8_t);
extern uint8_t scd_fb[R22_H][R22_W];
extern uint32_t scd_columns, scd_pixels;
extern uint32_t scd_clock_units;
extern void SCD_ClockPoll(void);

/* Report for the MD (sub status words are taken by the transport): last words of the bank. */
static void expand(void)
{
    for (uint16_t y = 0; y < R22_H; y++)
    {
        volatile uint8_t *row = BANK + (uint32_t)y * 4u * 256u;
        const uint8_t *s = scd_fb[y];
        for (uint16_t x = 0; x < R22_W; x++)
        {
            const uint8_t c = s[x], b = (uint8_t)((c << 4) | c);
            volatile uint8_t *p = row + x * 2u;
            p[0] = b; p[1] = b; p[256] = b; p[257] = b; p[512] = b; p[513] = b; p[768] = b; p[769] = b;
        }
        if (!(y & 7)) SCD_ClockPoll();
    }
}

void sub_main(void)
{
    REG16(0xFF8002UL) = 4; SCD_SubTransportReset(); REG16(0xFF8020UL) = 0x5343u;
    Z_Init(); W_Init(); REG16(0xFF8024UL) = 0x4E31;           /* 'N1': directory loaded */
    SCD_MetadataInit(); P_Init(); R_Init();
    N2_InitGame();                                           /* G_InitNew(sk_medium, 1) -> E1M1 */
    N2_SetCommand(0, 0, 0, 0); SCD_SubSetTime(0); G_Ticker(); _g_gametic++;
    if (!_g_player.mo || _g_gamestate != GS_LEVEL) I_Error("N2 NO LEVEL");
    uint8_t input[16];
    for (uint16_t f = 0; f < 24; f++)
    {
        SCD_ClockPoll();
        const uint32_t t0 = scd_clock_units;
        R_RenderPlayerView(&_g_player);
        SCD_ClockPoll();
        const uint32_t t1 = scd_clock_units;
        expand();
        SCD_ClockPoll();
        const uint32_t t2 = scd_clock_units;
        /* frame report at bank+0xFF00: render units, expand units, columns, pixels */
        volatile uint32_t *rep = (volatile uint32_t *)(BANK + 0xFF00u);
        rep[0] = 0x4E324652UL; rep[1] = f; rep[2] = t1 - t0; rep[3] = t2 - t1; rep[4] = scd_columns; rep[5] = scd_pixels;
        scd_columns = scd_pixels = 0;
        if (!SCD_SubFrame(f, input)) I_Error("N2 FRAME TRANSPORT");
    }
    REG16(0xFF8020UL) = 0x51B1u;                             /* done */
    for (;;) {}
}
