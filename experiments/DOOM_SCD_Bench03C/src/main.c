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
#define CD_SUB_RESULT (*(volatile const u16 *)0xA12024)
#define CD_SUB_ACK (*(volatile const u16 *)0xA12026)
#define CD_PRGRAM ((volatile u16 *)0x420000)

#define SUB_READY 0x5343u
#define SUB_FAULT 0xDEADu
#define TIMEOUT_VBLANKS 60u
#define CD_TIMER (*(volatile const u16 *)0xA1200C)
#define WORD_RAM ((volatile const u16 *)0x600000)
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

static union { u16 words[WORD_COUNT]; u32 dma[TILE_COUNT * 8u]; } staging;
extern void scd_generate_tiles(void *dst, u32 seed, u32 words);

static u16 elapsed(u16 start)
{
    return (CD_TIMER - start) & 0x0fffu;
}

static bool valid_tiles(const u16 *pixels, u16 value)
{
    for (u16 i = 0; i < WORD_COUNT; i++)
    {
        value = (u16)((value << 3) | (value >> 13));
        value = (u16)((value ^ 0x5a69u) + 0x1113u);
        if (pixels[i] != value)
            return FALSE;
    }
    return TRUE;
}

__attribute__((noinline))
static void upload_tiles(void)
{
    VDP_loadTileData(staging.dma, TILE_USER_INDEX, TILE_COUNT, DMA);
    VDP_waitDMACompletion();
}

static void stop(const char *message)
{
    VDP_drawText(message, 2, 7);
    while (TRUE)
        SYS_doVBlankProcess();
}

int main(bool hard)
{
    (void)hard;
    static const u16 colors[16] = {
        0x000, 0x202, 0x402, 0x604, 0x806, 0xa06, 0xc28, 0xe48,
        0x024, 0x046, 0x068, 0x28a, 0x4ac, 0x6ce, 0x8ee, 0xeee
    };
    JOY_init();
    VDP_setScreenWidth320();
    VDP_setPlaneSize(64, 32, TRUE);
    VDP_drawText("DOOM SCD / BENCH 03C / 16 KiB", 2, 0);
    VDP_drawText("A: SWITCH MAIN / SEGA CD", 2, 8);

    if ((HW_VERSION & 0x20u) && CD_BIOS_HEADER != 0x53454741UL)
        stop("NO SEGA CD DETECTED");
    const char *failure = boot_sub();
    if (failure)
        stop(failure);

    u16 wait = 0;
    while (CD_SUB_SIG != SUB_READY || (CD_MEMCTRL & 7u) != 1u)
    {
        if (CD_SUB_SIG == SUB_FAULT)
            stop("SUB CPU EXCEPTION");
        if (wait++ == TIMEOUT_VBLANKS)
            stop("WORD RAM INIT TIMEOUT");
        SYS_doVBlankProcess();
    }

    PAL_setPalette(PAL1, colors, CPU);
    for (u16 i = 0; i < TILE_COUNT; i++)
        VDP_setTileMapXY(BG_B, TILE_ATTR_FULL(PAL1, 0, 0, 0, TILE_USER_INDEX + i),
                         4 + (i % 32u), 10 + (i / 32u));

    bool use_cd = TRUE;
    u16 previous_pad = 0, sequence = 0, seed = 0;
    u32 blocks = 0;
    while (TRUE)
    {
        SYS_doVBlankProcess();
        const u16 pad = JOY_readJoypad(JOY_1);
        const bool changed = (pad & BUTTON_A) && !(previous_pad & BUTTON_A);
        previous_pad = pad;
        if (changed)
        {
            use_cd = !use_cd;
            blocks = 0;
        }

        u16 generate, transport = 0;
        seed += 17;
        u16 start = CD_TIMER;
        if (use_cd)
        {
            const u32 started_frame = vtimer;
            CD_MAIN_DATA = seed;
            CD_MEMCTRL = 2; /* 2M: DMNA grants the Sub CPU access */
            CD_MAIN_SEQ = ++sequence;

            while (CD_SUB_ACK != sequence || (CD_MEMCTRL & 7u) != 1u)
            {
                if (CD_SUB_SIG == SUB_FAULT)
                    stop("SUB CPU EXCEPTION");
                if (vtimer - started_frame >= 5u)
                    stop("WORD RAM RETURN / ACK TIMEOUT");
            }
            const u16 roundtrip = elapsed(start);
            generate = CD_SUB_RESULT;
            start = CD_TIMER;
            for (u16 i = 0; i < WORD_COUNT; i++)
                staging.words[i] = WORD_RAM[i];
            transport = (roundtrip >= generate ? roundtrip - generate : 0) + elapsed(start);
        }
        else
        {
            scd_generate_tiles(staging.words, seed, WORD_COUNT);
            generate = elapsed(start);
        }

        start = CD_TIMER;
        if (!valid_tiles(staging.words, seed))
            stop("TILE DATA MISMATCH");
        const u16 verify = elapsed(start);

        start = CD_TIMER;
        upload_tiles();
        const u16 upload = elapsed(start);
        blocks++;

        if (blocks == 1 || (blocks & 15u) == 0)
        {
            VDP_clearTextLine(2);
            VDP_drawText(use_cd ? "SOURCE: SEGA CD 68000" : "SOURCE: MAIN 68000", 2, 2);
            number("BLOCKS VERIFIED: ", blocks, 3);
            number("GENERATE TICKS: ", generate, 4);
            number("HANDOFF + COPY TICKS: ", transport, 5);
            number("VERIFY TICKS: ", verify, 6);
            number("VDP DMA TICKS: ", upload, 7);
        }
    }
}
