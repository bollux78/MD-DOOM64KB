/* N2 MD side (inside the R128 tree, before D_DoomMain): boot the sub, serve DIR/LUMP, show the
 * frames the Sega CD renders (DMA from the 1M cell view), then START -> R128 on the MD (playable). */
#include <stddef.h>
#include <stdint.h>
#include <genesis.h>
#include "doomtype.h"
#include "w_wad.h"
#include "i_system.h"
#include "r21_textscreen.h"
#include "r22_palette.h"
#include "scd_proto.h"
#include "n2_sub.h"

#define HW_VERSION (*(volatile const u8 *)0xA10001)
#define CD_BIOS_HEADER (*(volatile const u32 *)0x400100)
#define CD_SUB_BYTE (*(volatile u8 *)0xA12001)
#define CD_MEMCTRL (*(volatile u16 *)0xA12002)
#define CD_MEMCTRL_LO (*(volatile u8 *)0xA12003)
#define CD_MAIN_SWAP (*(volatile u16 *)0xA12018)
#define CD_SUB_SIG (*(volatile const u16 *)0xA12020)
#define CD_SUB_ARG (*(volatile const u16 *)0xA12024)
#define CD_TIMER (*(volatile const u16 *)0xA1200C)
#define CD_PRGRAM ((volatile u16 *)0x420000)
#define CELLS ((volatile const u16 *)0x620000)
#define VDP_CTRL (*(volatile u32 *)0xC00004)
#define VDP_CTRL16 (*(volatile u16 *)0xC00004)
#define VDP_STATUS (*(volatile const u16 *)0xC00004)
#define VDP_DATA (*(volatile u16 *)0xC00000)
enum { TILE_BASE = 256, COLS = 38, ROWS = 22 };

extern void SCD_MdServeReset(void);
extern int16_t SCD_MdServeOnce(void);
extern uint16_t SCD_MdTransactions(void), SCD_MdErrors(void);
extern uint32_t SCD_MdBytes(void), SCD_MdTimeouts(void);

typedef struct { u16 stage, frames, errors, timeouts; u32 bytes, render_units, expand_units, columns, pixels, vblanks, min_render, column_units, stack_depth, lowmem; } N2Report;
#define REPORT (*(volatile N2Report *)0x61F000)
static N2Report *rep;

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
    /* Multi-window loader: 128 KiB PRG-RAM banks through $420000, bank in $A12003 bits 6-7. */
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
    /* Write-protect the first 0xFF x 512 B of PRG-RAM (vectors + most code) against the sub:
     * stray MD-hardware writes in R128 code must not destroy the program. */
    *(volatile u8 *)0xA12002 = 0xFF;
    CD_SUB_BYTE = 0;
    if (!wait_sub(1, 0)) return FALSE;
    CD_SUB_BYTE = 1;
    if (!wait_sub(3, 1)) return FALSE;
    for (u32 n = 0; n < 4000000UL; n++) if (CD_SUB_SIG == 0x5343u && (CD_MEMCTRL & 5u) == 4u) return TRUE;
    return FALSE;
}
static u32 command(u16 a) { return ((u32)(a & 0x3fffu) << 16) | (a >> 14); }
static void wait_vblank(void) { while (VDP_STATUS & 8u) ; while (!(VDP_STATUS & 8u)) ; }

/* Called by the patched server right after a FRAME exchange: the bank the sub filled is ours. */
void N2_MdFrameArrived(u16 frame)
{
    volatile const u32 *r = (volatile const u32 *)0x60FF00UL;
    if (r[0] == 0x4E324652UL) { rep->render_units += r[2]; rep->expand_units += r[3]; rep->columns += r[4]; rep->pixels += r[5]; rep->min_render = r[6]; rep->column_units += r[7]; }
    rep->frames = frame + 1;
    /* 38 column DMAs of 22 cells (704 B) from the 64x32 cell view, 8 per VBlank. */
    VDP_CTRL16 = 0x8f02;
    for (u16 c = 0; c < COLS; c++)
    {
        if (!(c & 7)) { wait_vblank(); rep->vblanks++; }
        const volatile u16 *src = CELLS + (u32)c * 512u;
        const u16 dest = (u16)((TILE_BASE + c * ROWS) * 32u);
        const u32 from = ((u32)(src + 1) >> 1) & 0x7fffffUL;
        const u16 count = ROWS * 16u;
        VDP_CTRL16 = 0x9300 | (count & 0xff); VDP_CTRL16 = 0x9400 | (count >> 8);
        VDP_CTRL16 = 0x9500 | (from & 0xff); VDP_CTRL16 = 0x9600 | ((from >> 8) & 0xff);
        VDP_CTRL16 = 0x9700 | ((from >> 16) & 0x7f);
        VDP_CTRL = command(dest) | 0x40000080UL;
        VDP_CTRL = command(dest) | 0x40000000UL;
        VDP_DATA = src[0]; VDP_DATA = src[1];
    }
}

void __attribute__((noipa)) n2_frame_shown(void) { __asm__ volatile ("" ::: "memory"); }
void __attribute__((noipa)) n2_complete(void) { __asm__ volatile ("" ::: "memory"); }
void __attribute__((noipa)) n2_continue(void) { __asm__ volatile ("" ::: "memory"); }

static void setup_screen(void)
{
    I_R21_TextScreen();
    VDP_setReg(1, VDP_getReg(1) | 0x10);
    PAL_setColors(0, r22_cram[0], 16, CPU);
    for (u16 c = 0; c < COLS; c++)
        for (u16 r = 0; r < ROWS; r++)
            VDP_setTileMapXY(BG_A, TILE_ATTR_FULL(PAL0, 0, 0, 0, TILE_BASE + c * ROWS + r), 1 + c, 3 + r);
    VDP_drawText("doom-md-scd-n2.bin  SEGA CD RENDER", 1, 1);
}

/* Sub I_Error leaves the message address in $A1202A/2C. Halt the sub (bus request) and read the
 * string from PRG-RAM through the 128 KiB window, into Word RAM at 0x61F100 (report area). */
static void fetch_sub_error(void)
{
    const u32 addr = ((u32)*(volatile const u16 *)0xA1202A << 16) | *(volatile const u16 *)0xA1202C;
    volatile u8 *msg = (volatile u8 *)0x61F100;
    msg[0] = 0;
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

/* Profiler table (512 x {fn, units, calls}, 6 KiB at the address in $A1202A/2C) -> Word RAM 0x61C000. */
static void fetch_profile(void)
{
    const u32 addr = ((u32)*(volatile const u16 *)0xA1202A << 16) | *(volatile const u16 *)0xA1202C;
    if (addr >= 0x80000UL) return;
    CD_SUB_BYTE = 3;
    if (!wait_sub(2, 2)) return;
    volatile u16 *dst = (volatile u16 *)0x61C000;
    for (u16 i = 0; i < 3072; i++)
    {
        const u32 a = addr + i * 2u;
        CD_MEMCTRL_LO = (u8)((a >> 17) << 6);
        dst[i] = *(volatile const u16 *)(0x420000UL + (a & 0x1FFFFUL));
    }
    CD_MEMCTRL_LO = 0;
}

static void run(void)
{
    if ((HW_VERSION & 0x20u) || CD_BIOS_HEADER != 0x53454741UL) { rep->stage = 1; return; }
    if (!boot_sub()) { rep->stage = 2; return; }
    rep->stage = 3;
    W_Init();
    setup_screen();
    SCD_MdServeReset();
    for (u32 spins = 0; spins < 400000000UL; spins++)
    {
        const int16_t served = SCD_MdServeOnce();
        if (served < 0) { rep->stage = 4; break; }
        if (served > 0 && rep->frames) n2_frame_shown();
        if (CD_SUB_SIG == 0x51B1u) { rep->stage = 5; rep->stack_depth = *(volatile const u16 *)0xA1202E; rep->lowmem = ((u32)*(volatile const u16 *)0xA12026 << 16) | *(volatile const u16 *)0xA12028; fetch_profile(); break; }
        if (CD_SUB_SIG == 0xDEADu) { rep->stage = 6; rep->lowmem = ((u32)*(volatile const u16 *)0xA12026 << 16) | *(volatile const u16 *)0xA12028; fetch_sub_error(); break; }
    }
    rep->errors = SCD_MdErrors(); rep->timeouts = SCD_MdTimeouts(); rep->bytes = SCD_MdBytes();
}

void N2_Test(void)
{
    N2Report r;
    memset(&r, 0, sizeof r);
    rep = &r;
    SYS_disableInts();
    run();
    REPORT = r;
    SYS_enableInts();
    n2_complete();
    char t[40];
    const bool pass = r.stage == 5 && r.frames == 24 && !r.errors && !r.timeouts;
    sprintf(t, "N2 %s STAGE %u FRAMES %u", pass ? "PASS" : "FAIL", (unsigned)r.stage, (unsigned)r.frames); VDP_drawText(t, 1, 26);
    sprintf(t, "CD RENDER MS/FRAME %u", (unsigned)(r.frames ? r.render_units * 3072u / 100000u / r.frames : 0)); VDP_drawText(t, 1, 27);
    if (r.stage == 6) { char m[40]; volatile const u8 *e = (volatile const u8 *)0x61F100; u16 i = 0; for (; i < 39 && e[i]; i++) m[i] = (char)e[i]; m[i] = 0; VDP_drawText(m, 1, 25); }
    VDP_drawText("START: PLAY R128 ON MEGA DRIVE", 1, 2);
    volatile u8 *const data = (volatile u8 *)0xA10003, *const ctrl = (volatile u8 *)0xA10009;
    *ctrl = 0x40;
    for (u16 frames = 0; frames < 900; frames++)
    {
        wait_vblank();
        *data = 0; __asm__ volatile ("nop; nop; nop; nop");
        const u8 b = *data; *data = 0x40;
        if (!(b & 0x20u)) break;
    }
    n2_continue();
}
