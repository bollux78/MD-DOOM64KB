/* N2 sub program: the whole R128 engine (SRAM-in-RAM model) runs on the Sega CD; the MD only
 * serves the WAD and shows frames. The spawn of E1M1 is rendered 24 times by the native column
 * back end (m2/scd_draw.c); each frame is expanded to a linear 4bpp bitmap (4x4 px per sample,
 * 304x176, stride 256 B) in the sub's Word RAM bank, which the MD reads through the 1M cell view. */
#include <stdint.h>
#include "doomdef.h"
#include "globdata.h"
#include "g_game.h"
#include "p_tick.h"
#include "p_setup.h"
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
extern uint32_t scd_clock_units, scd_column_units;
extern void SCD_ClockPoll(void);
#if N2_PROF & 2
extern void scd_prof_start(void), scd_prof_stop(void);
extern uint8_t scd_prof_tab[];
static void prof_on(void) { scd_prof_start(); }
static void prof_off(void) { scd_prof_stop(); }
#else
static void prof_on(void) {}
static void prof_off(void) {}
#endif

/* Report for the MD (sub status words are taken by the transport): last words of the bank. */
static void expand(void)
{
    /* 4x4 px per sample: 2 samples -> one long (8 nibbles) per pixel row, 4 rows; stride 256 B. */
    static const uint16_t nib4[16] = { 0x0000, 0x1111, 0x2222, 0x3333, 0x4444, 0x5555, 0x6666, 0x7777,
                                       0x8888, 0x9999, 0xAAAA, 0xBBBB, 0xCCCC, 0xDDDD, 0xEEEE, 0xFFFF };
    for (uint16_t y = 0; y < R22_H; y++)
    {
        volatile uint32_t *r0 = (volatile uint32_t *)(BANK + (uint32_t)y * 1024u);
        const uint8_t *s = scd_fb[y];
        for (uint16_t x = 0; x < R22_W / 2; x++)
        {
            const uint32_t w = ((uint32_t)nib4[s[0]] << 16) | nib4[s[1]];
            s += 2;
            r0[0] = w; r0[64] = w; r0[128] = w; r0[192] = w;
            r0++;
        }
        if (!(y & 7)) SCD_ClockPoll();
    }
}

extern uint8_t _end[];
static void stack_paint(void)
{
    uint32_t sp; __asm__ volatile ("move.l %%sp,%0" : "=a" (sp));
    for (volatile uint32_t *p = (volatile uint32_t *)(((uint32_t)_end + 3) & ~3UL); (uint32_t)p < sp - 256; p++) *p = 0xA5A5A5A5UL;
}
static uint16_t stack_depth(void)
{
    const volatile uint32_t *p = (const volatile uint32_t *)(((uint32_t)_end + 3) & ~3UL);
    while ((uint32_t)p < 0x80000UL && *p == 0xA5A5A5A5UL) p++;
    return (uint16_t)(0x80000UL - (uint32_t)p);
}

static uint32_t lowmem_copy[64];
void sub_main(void)
{
    stack_paint();
    for (uint16_t i = 0; i < 64; i++) lowmem_copy[i] = ((volatile const uint32_t *)0)[i];
    REG16(0xFF8002UL) = 4; SCD_SubTransportReset(); REG16(0xFF8020UL) = 0x5343u;
    Z_Init(); W_Init(); REG16(0xFF8024UL) = 0x4E31;           /* 'N1': directory loaded */
    R_Init(); P_Init();                                      /* D_DoomMain order */
    N2_InitGame();                                           /* G_InitNew(sk_medium, 1) -> E1M1 */
    N2_SetCommand(0, 0, 0, 0); SCD_SubSetTime(0); G_Ticker(); _g_gametic++;
    if (!_g_player.mo || _g_gamestate != GS_LEVEL) I_Error("N2 NO LEVEL");
    uint8_t input[16];
    uint32_t min_render = 0;
    for (uint16_t f = 0; f < 24; f++)
    {
        SCD_ClockPoll();
        const uint32_t t0 = scd_clock_units;
        if (f) prof_on();   /* frame 0 loads every lump through the MD; sample cached frames only */
        R_RenderPlayerView(&_g_player);
        prof_off();
        SCD_ClockPoll();
        const uint32_t t1 = scd_clock_units;
        expand();
        SCD_ClockPoll();
        const uint32_t t2 = scd_clock_units;
        /* frame report at bank+0xFF00: render units, expand units, columns, pixels */
        volatile uint32_t *rep = (volatile uint32_t *)(BANK + 0xFF00u);
        rep[0] = 0x4E324652UL; rep[1] = f; rep[2] = t1 - t0; rep[3] = t2 - t1; rep[4] = scd_columns; rep[5] = scd_pixels;
        if (f == 0 || t1 - t0 < min_render) min_render = t1 - t0;
        rep[6] = min_render; rep[7] = scd_column_units; scd_column_units = 0;
        scd_columns = scd_pixels = 0;
        if (!SCD_SubFrame(f, input)) I_Error("N2 FRAME TRANSPORT");
    }
#if N2_PROF & 2
    REG16(0xFF802AUL) = (uint16_t)((uint32_t)(uintptr_t)scd_prof_tab >> 16);
    REG16(0xFF802CUL) = (uint16_t)(uintptr_t)scd_prof_tab;  /* MD fetches the histogram */
#else
    REG16(0xFF802AUL) = 0xFFFF;
#endif
    {   uint16_t first = 0xFFFF, count = 0;
        for (uint16_t i = 0; i < 64; i++)
            if (((volatile const uint32_t *)0)[i] != lowmem_copy[i]) { if (first == 0xFFFF) first = i * 4; count++; }
        REG16(0xFF8026UL) = first; REG16(0xFF8028UL) = count;
    }
    REG16(0xFF802EUL) = stack_depth();                       /* deepest stack use in bytes */
    REG16(0xFF8020UL) = 0x51B1u;                             /* done */
    for (;;) {}
}
