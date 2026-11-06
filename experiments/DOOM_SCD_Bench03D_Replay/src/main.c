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
#define CD_MAIN_SWAP (*(volatile u16 *)0xA12018)
#define CD_SUB_SIG (*(volatile const u16 *)0xA12020)
#define CD_TIMER (*(volatile const u16 *)0xA1200C)
#define CD_SUB_TICKS (*(volatile const u16 *)0xA12024)
#define CD_SUB_ERROR (*(volatile const u16 *)0xA1202A)
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
#define FRAME_BYTES 3344u
#define WORD_COUNT (FRAME_BYTES / 2u)

_Static_assert(SUB_PROGRAM_WORDS > 0 && SUB_PROGRAM_WORDS <= 0x3c000u,
               "Sub-CPU image must leave 32 KiB of PRG RAM for stack");

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

    CD_MAIN_SEQ = 0;
    CD_MAIN_SWAP = 0;
    CD_MAIN_DATA = 0;
    for (u32 first = 0; first < SUB_PROGRAM_WORDS; first += 65536u)
    {
        const u32 remaining = SUB_PROGRAM_WORDS - first;
        const u32 words = remaining < 65536u ? remaining : 65536u;
        CD_MEMCTRL = (u16)((first >> 16) << 6);
        for (u32 i = 0; i < words; i++)
            CD_PRGRAM[i] = sub_program[first + i];
        for (u32 i = 0; i < words; i++)
        {
            if (CD_PRGRAM[i] != sub_program[first + i])
            {
                CD_SUB_BYTE = 0;
                return "PRG RAM VERIFY FAILED";
            }
        }
    }
    CD_MEMCTRL = 0;

    CD_SUB_BYTE = 0;
    if (!wait_sub(1, 0))
        return "SECOND RESET TIMEOUT";

    CD_SUB_BYTE = 1;
    if (!wait_sub(3, 1))
        return "RELEASE TIMEOUT";
    return NULL;
}

extern const u8 scd_fixture[];
extern u32 scd_replay(u32 index, u8 *output, u32 verify);
static u8 frame[FRAME_BYTES];
volatile u32 main_ticks, sub_ticks, swap_ticks, dma_ticks, display_vblanks, useful;
volatile u32 stale, timeouts, useful_hash;

__attribute__((noinline, noclone, used))
static void replay_pass(void)
{
    VDP_drawText("REPLAY PASS / 8 FRAMES / 64 TIMED", 2, 12);
}

__attribute__((noinline, noclone))
static void scd_replay_fail(const char *message)
{
    VDP_drawText(message, 2, 14);
    while (TRUE)
        SYS_doVBlankProcess();
}

static u16 delta(u16 start)
{
    return (CD_TIMER - start) & 0x0fffu;
}

static void wait_frame(u16 id, bool swap, u16 bank, bool useful_work)
{
    const u32 start = vtimer;
    while (TRUE)
    {
        if (CD_SUB_SIG == SUB_FAULT)
            scd_replay_fail("SUB CPU EXCEPTION");
        if ((!swap && CD_SUB_READY == id) ||
            (swap && CD_SUB_ACK == id && (CD_MEMCTRL & 5u) == (4u | bank)))
            return;
        if (vtimer - start >= ((!swap && id <= 8u) ? 30u : 6u))
        {
            timeouts++;
            scd_replay_fail(swap ? "SWAP TIMEOUT" : "RENDER TIMEOUT");
        }
        if (useful_work)
        {
            useful_hash = (useful_hash << 5) ^ (useful_hash >> 17) ^ id;
            useful++;
        }
    }
}

static void upload(void)
{
    const u16 dest = TILE_USER_INDEX * 32u;
    const u16 first = WORD_DATA[0], second = WORD_DATA[1];
    DMA_doDma(DMA_VRAM, (void *)0x600022, dest, WORD_COUNT, 2);
    VDP_waitDMACompletion();
    SYS_disableInts();
    VDP_CTRL = 0x40000000UL | ((u32)(dest & 0x3fffu) << 16) | (dest >> 14);
    VDP_DATA = first;
    VDP_DATA = second;
    SYS_enableInts();
}

int main(bool hard)
{
    (void)hard;
    VDP_setScreenWidth320();
    VDP_drawText("SCD 03D / R128 COLUMN REPLAY", 2, 0);
    if ((HW_VERSION & 0x20u) && CD_BIOS_HEADER != 0x53454741UL)
        scd_replay_fail("NO SEGA CD DETECTED");
    const char *failure = boot_sub();
    if (failure)
        scd_replay_fail(failure);
    for (u16 wait = 0; CD_SUB_SIG != SUB_READY || (CD_MEMCTRL & 5u) != 4u; wait++)
    {
        if (wait == TIMEOUT_VBLANKS)
            scd_replay_fail("WORD RAM 1M INIT TIMEOUT");
        SYS_doVBlankProcess();
    }

    for (u16 i = 0; i < 8; i++)
    {
        const u32 error = scd_replay(i, frame, 1);
        if (error)
        {
            number("MAIN CALL OR OFFSET: ", error, 15);
            scd_replay_fail("MAIN KERNEL MISMATCH");
        }
    }
    for (u16 i = 0; i < 64; i++)
    {
        const u32 vstart = vtimer;
        const u16 start = CD_TIMER;
        scd_replay(i & 7u, frame, 0);
        if (vtimer - vstart >= 6u)
            scd_replay_fail("MAIN TIMER RANGE");
        main_ticks += delta(start);
    }

    CD_MAIN_SEQ = 1;
    u32 first_present = 0;
    for (u16 id = 1; id <= 72; id++)
    {
        const bool verify = id <= 8;
        wait_frame(id, FALSE, 0, !verify);
        if (CD_SUB_ERROR)
        {
            number("SUB CALL OR OFFSET: ", CD_SUB_ERROR, 15);
            scd_replay_fail("SUB KERNEL MISMATCH");
        }
        const u16 elapsed = CD_SUB_TICKS;
        const u16 next_bank = (CD_MEMCTRL ^ 1u) & 1u;
        u16 start = CD_TIMER;
        CD_MAIN_SWAP = id; /* console: DMNA reads 1 after 2M->1M, so request swaps via comm word */
        wait_frame(id, TRUE, next_bank, FALSE);
        if (!verify)
            swap_ticks += delta(start);
        if (WORD_ID != id)
        {
            stale++;
            scd_replay_fail("STALE WORD RAM FRAME");
        }
        if (id < 72)
            CD_MAIN_SEQ = id + 1u;

        if (verify)
        {
            const u32 *offset = (const u32 *)scd_fixture;
            const u16 *expected = (const u16 *)(scd_fixture + offset[1 + id] + 4);
            for (u16 i = 0; i < WORD_COUNT; i++)
                if (WORD_DATA[i] != expected[i])
                    scd_replay_fail("FRAMEBUFFER MISMATCH");
            if (id == 8)
                first_present = vtimer;
        }
        else
        {
            sub_ticks += elapsed;
            start = CD_TIMER;
            upload();
            dma_ticks += delta(start);
        }
    }
    display_vblanks = vtimer - first_present;
    number("MAIN DRAW TICKS: ", main_ticks, 3);
    number("SUB DRAW TICKS: ", sub_ticks, 4);
    number("MAIN SWAP WAIT: ", swap_ticks, 5);
    number("VDP DMA TICKS: ", dma_ticks, 6);
    number("DISPLAY VBLANKS: ", display_vblanks, 7);
    number("MAIN USEFUL LOOPS: ", useful, 8);
    number("STALE: ", stale, 9);
    number("TIMEOUTS: ", timeouts, 10);
    replay_pass();
    while (TRUE)
        SYS_doVBlankProcess();
}
