#include <genesis.h>
#include <string.h>
#include "sub_program.h"

#define HW_VERSION (*(volatile const u8 *)0xA10001)
#define CD_BIOS_HEADER (*(volatile const u32 *)0x400100)
#define CD_SUB_BYTE (*(volatile u8 *)0xA12001)
#define CD_SUBCTRL (*(volatile const u16 *)0xA12000)
#define CD_MEMCTRL (*(volatile u16 *)0xA12002)
#define CD_MAIN_SEQ (*(volatile u16 *)0xA12010)
#define CD_MAIN_DATA (*(volatile u16 *)0xA12012)
#define CD_SUB_SIG (*(volatile const u16 *)0xA12020)
#define CD_SUB_READY (*(volatile const u16 *)0xA12028)
#define CD_SUB_ACK (*(volatile const u16 *)0xA12026)
#define CD_PRGRAM ((volatile u16 *)0x420000)

#define SUB_READY 0x5343u
#define SUB_FAULT 0xDEADu
#define TIMEOUT_VBLANKS 60u
#define WORD_ID (*(volatile const u16 *)0x600000)
#define WORD_DATA ((volatile const u16 *)0x600020)
#define VDP_CTRL (*(volatile u32 *)0xc00004)
#define VDP_DATA (*(volatile u16 *)0xc00000)
#define TILE_COUNT 512u
#define WORD_COUNT (TILE_COUNT * 16u)

_Static_assert(SUB_PROGRAM_WORDS > 0 && SUB_PROGRAM_WORDS <= 65536u,
               "Sub-CPU image must fit in one Program RAM bank");

static void number(const char *label, u32 value, u16 y)
{
    char line[40], digits[12];
    uintToStr(value, digits, 1);
    strcpy(line, label);
    strcat(line, digits);
    VDP_clearTextLine(y);
    VDP_drawText(line, 2, y);
}

static bool wait_sub(u8 mask, u8 expected)
{
    for (u16 frame = 0; frame < TIMEOUT_VBLANKS; frame++)
    {
        if ((CD_SUB_BYTE & mask) == expected)
            return TRUE;
        SYS_doVBlankProcess();
    }
    return FALSE;
}

static const char *boot_sub(void)
{
    /* Gate Array reset sequence for cartridge boot. */
    SYS_disableInts();
    CD_MEMCTRL = 0xFF00;
    CD_SUB_BYTE = 3;
    CD_SUB_BYTE = 2;
    CD_SUB_BYTE = 0;
    SYS_enableInts();
    for (u16 i = 0; i < 128; i++)
        __asm__ volatile ("nop");

    if (!wait_sub(1, 0))
        return "RESET TIMEOUT";

    CD_SUB_BYTE = 3;
    if (!wait_sub(3, 3))
        return "BUS REQUEST TIMEOUT";

    CD_MEMCTRL = 0;
    CD_MAIN_SEQ = 0;
    CD_MAIN_DATA = 0;
    for (u32 i = 0; i < SUB_PROGRAM_WORDS; i++)
        CD_PRGRAM[i] = sub_program[i];
    for (u32 i = 0; i < SUB_PROGRAM_WORDS; i++)
    {
        if (CD_PRGRAM[i] != sub_program[i])
        {
            CD_SUB_BYTE = 0;
            return "PRG RAM VERIFY FAILED";
        }
    }

    CD_SUB_BYTE = 0;
    if (!wait_sub(1, 0))
        return "SECOND RESET TIMEOUT";

    CD_SUB_BYTE = 1;
    if (!wait_sub(3, 1))
        return "RELEASE TIMEOUT";
    return NULL;
}

static u32 frames, swaps, stale, timeouts;

__attribute__((noinline, noclone, used))
static void gate_pass(void)
{
    VDP_drawText("TRANSPORT PASS / 16 VERIFIED", 2, 7);
}

__attribute__((noinline, noclone))
static void scd_gate_fail(const char *message)
{
    VDP_clearTextLine(7);
    VDP_drawText(message, 2, 7);
    number("FRAMES: ", frames, 3);
    number("SWAPS: ", swaps, 4);
    number("STALE: ", stale, 5);
    number("TIMEOUTS: ", timeouts, 6);
    while (TRUE)
        SYS_doVBlankProcess();
}

static void await_frame(u16 id, bool swap, u16 next_bank)
{
    const u32 start = vtimer;
    for (;;)
    {
        if (CD_SUB_SIG == SUB_FAULT)
            scd_gate_fail("SUB CPU EXCEPTION");
        if (!swap && CD_SUB_READY == id)
            return;
        if (swap && CD_SUB_ACK == id && (CD_MEMCTRL & 7u) == (4u | next_bank))
            return;
        if (vtimer - start >= 6u)
        {
            timeouts++;
            scd_gate_fail(swap ? "SWAP TIMEOUT" : "FRAME TIMEOUT");
        }
    }
}

static u32 vram_command(u16 address)
{
    return ((u32)(address & 0x3fffu) << 16) | (address >> 14);
}

static void transfer_and_check(u16 id)
{
    const u16 dest = TILE_USER_INDEX * 32u;
    const u16 first = WORD_DATA[0], second = WORD_DATA[1];

    /* The Mega-CD manual compensates for a one-word DMA read delay.
     * The source lies within one 128 KiB window, including its guard word. */
    DMA_doDma(DMA_VRAM, 0x600022, dest, WORD_COUNT, 2);
    VDP_waitDMACompletion();
    SYS_disableInts();
    VDP_CTRL = vram_command(dest) | 0x40000000UL;
    VDP_DATA = first;
    VDP_DATA = second;

    VDP_CTRL = vram_command(dest);
    u16 expected = id;
    u16 bad = WORD_COUNT;
    for (u16 i = 0; i < WORD_COUNT; i++)
    {
        expected = (u16)((expected << 3) | (expected >> 13));
        expected = (u16)((expected ^ 0x5a69u) + 0x1113u);
        if (VDP_DATA != expected)
        {
            bad = i;
            break;
        }
    }
    SYS_enableInts();
    if (bad != WORD_COUNT)
    {
        number("FIRST BAD VRAM WORD: ", bad, 8);
        scd_gate_fail("VRAM DMA MISMATCH");
    }
}

int main(bool hard)
{
    (void)hard;
    VDP_setScreenWidth320();
    VDP_setPlaneSize(64, 32, TRUE);
    VDP_drawText("SCD 03D / WORD RAM 1M / DMA", 2, 0);

    if ((HW_VERSION & 0x20u) && CD_BIOS_HEADER != 0x53454741UL)
        scd_gate_fail("NO SEGA CD DETECTED");
    const char *failure = boot_sub();
    if (failure)
        scd_gate_fail(failure);

    for (u16 wait = 0; CD_SUB_SIG != SUB_READY || (CD_MEMCTRL & 7u) != 4u; wait++)
    {
        if (wait == TIMEOUT_VBLANKS)
            scd_gate_fail("WORD RAM 1M INIT TIMEOUT");
        SYS_doVBlankProcess();
    }

    static const u16 colors[16] = {
        0x000, 0x202, 0x402, 0x604, 0x806, 0xa06, 0xc28, 0xe48,
        0x024, 0x046, 0x068, 0x28a, 0x4ac, 0x6ce, 0x8ee, 0xeee
    };
    PAL_setPalette(PAL1, colors, CPU);
    for (u16 i = 0; i < TILE_COUNT; i++)
        VDP_setTileMapXY(BG_B, TILE_ATTR_FULL(PAL1, 0, 0, 0, TILE_USER_INDEX + i),
                         4 + (i % 32u), 10 + (i / 32u));

    u16 id = 1;
    CD_MAIN_SEQ = id;
    while (TRUE)
    {
        await_frame(id, FALSE, 0);
        const u16 next_bank = (CD_MEMCTRL ^ 1u) & 1u;
        CD_MEMCTRL = 0;
        await_frame(id, TRUE, next_bank);
        swaps++;
        if (WORD_ID != id)
        {
            stale++;
            scd_gate_fail("STALE WORD RAM FRAME");
        }
        CD_MAIN_SEQ = (u16)(id + 1u);

        /* The Sub CPU can fill the other bank during the DMA and readback.
         * No swap is requested until all access to this bank is complete. */
        transfer_and_check(id);
        id++;
        frames++;
        if (frames == 16)
            gate_pass();
        if ((frames & 7u) == 0)
        {
            number("FRAMES: ", frames, 3);
            number("SWAPS: ", swaps, 4);
            number("STALE: ", stale, 5);
            number("TIMEOUTS: ", timeouts, 6);
        }
        SYS_doVBlankProcess();
    }
}
