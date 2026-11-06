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
#define WORD_COUNT 1672u

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
    CD_MAIN_SWAP = 0;
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



#define CD_TIMER (*(volatile const u16 *)0xa1200c)
#define SUB_RENDER_TICKS (*(volatile const u16 *)0xa12024)
enum { TRIALS = 16, PLANE_WORDS = 1344, PLANE_A = 0xc000, PLANE_B = 0xe000 };
/* count, render, request-to-ready, swap, VBlank wait, DMA, end-to-end, errors */
volatile u32 scene_metrics[2][8];
volatile u16 scene_state;
static u16 local[2 * PLANE_WORDS + 1];

extern void scene_render(uint16_t *planes);
extern const uint8_t *scene_reference(void);

static u16 since(u16 start)
{
    return (CD_TIMER - start) & 0xfffu;
}

static u32 command(u16 address)
{
    return ((u32)(address & 0x3fffu) << 16) | (address >> 14);
}

static bool ready(volatile const u16 *reg, u16 id)
{
    const u32 start = vtimer;
    while (*reg != id)
        if (CD_SUB_SIG == SUB_FAULT || vtimer - start >= 6u)
            return FALSE;
    return TRUE;
}

static void transfer(const volatile u16 *src, u16 dest, bool cd)
{
    DMA_doDma(DMA_VRAM, (void *)(src + cd), dest, PLANE_WORDS, 2);
    VDP_waitDMACompletion();
    if (cd)
    {
        VDP_CTRL = command(dest) | 0x40000000UL;
        VDP_DATA = src[0];
        VDP_DATA = src[1];
    }
}

static u16 verify(void)
{
    const u8 *ref = scene_reference();
    u16 bad = 0;
    for (u16 plane = 0; plane < 2; ++plane)
    {
        VDP_CTRL = command((plane ? PLANE_B : PLANE_A) + 128u);
        for (u16 y = 1; y < 22; ++y)
            for (u16 x = 0; x < 64; ++x)
            {
                const u16 off = y * 152u + plane * 76u + x * 2u;
                const u16 expected = x < 38 ? (u16)ref[off] << 8 | ref[off + 1u] : 0;
                bad += VDP_DATA != expected;
            }
    }
    return bad;
}

static void prepare_display(void)
{
    VDP_setScreenWidth320();
    VDP_setPlaneSize(64, 32, TRUE);
    VDP_setBGAAddress(PLANE_A);
    VDP_setBGBAddress(PLANE_B);
    VDP_clearPlane(BG_A, TRUE);
    VDP_clearPlane(BG_B, TRUE);
    VDP_setHorizontalScroll(BG_A, 0);
    VDP_setHorizontalScroll(BG_B, 4);
    u16 gray[16];
    for (u16 i = 0; i < 16; ++i)
        gray[i] = (i >> 1) * 0x222u;
    PAL_setPalette(PAL0, gray, CPU);
    PAL_setPalette(PAL1, gray, CPU);
    PAL_setColor(15, 0xeee);
    for (u16 i = 0; i < 256; ++i)
    {
        u32 tile[8];
        for (u16 row = 0; row < 8; ++row)
            tile[row] = (row < 4 ? i >> 4 : i & 15u) * 0x11110000UL;
        VDP_loadTileData(tile, 256u + i, 1, CPU);
        VDP_loadTileData(tile, 512u + i, 1, CPU);
    }
    VDP_drawText("doom-md-scd-scene-replay.bin", 5, 0);
}

static void run(void)
{
    if ((HW_VERSION & 0x20u) || CD_BIOS_HEADER != 0x53454741UL || boot_sub())
        return;
    for (u16 i = 0; CD_SUB_SIG != SUB_READY || (CD_MEMCTRL & 5u) != 4u; ++i)
    {
        if (i == TIMEOUT_VBLANKS)
            return;
        SYS_doVBlankProcess();
    }
    for (u16 cd = 0; cd < 2; ++cd)
        for (u16 id = 1; id <= TRIALS; ++id)
        {
            SYS_doVBlankProcess();
            const u16 start = CD_TIMER;
            u16 render, work, swap_ticks = 0;
            if (cd)
            {
                CD_MAIN_SEQ = id;
                if (!ready(&CD_SUB_READY, id))
                    return;
                work = since(start);
                render = SUB_RENDER_TICKS;
                const u16 bank = (CD_MEMCTRL & 5u) ^ 1u;
                const u16 swap_start = CD_TIMER;
                CD_MAIN_SWAP = id;
                if (!ready(&CD_SUB_ACK, id) || (CD_MEMCTRL & 5u) != bank || WORD_ID != id)
                    return;
                swap_ticks = since(swap_start);
            }
            else
            {
                scene_render(local);
                work = render = since(start);
            }

            const u16 wait_start = CD_TIMER;
            SYS_doVBlankProcess();
            const u16 wait = since(wait_start);
            SYS_disableInts();
            const u16 dma_start = CD_TIMER;
            const volatile u16 *src = cd ? WORD_DATA : local;
            transfer(src, PLANE_A + 128u, cd);
            transfer(src + PLANE_WORDS, PLANE_B + 128u, cd);
            const u16 dma = since(dma_start);
            const u16 total = since(start);
            /* Verify the live planes after timing, with interrupts masked. */
            const u16 bad = verify();
            SYS_enableInts();
            scene_metrics[cd][7] += bad;
            if (bad)
                return;
            ++scene_metrics[cd][0];
            scene_metrics[cd][1] += render;
            scene_metrics[cd][2] += work;
            scene_metrics[cd][3] += swap_ticks;
            scene_metrics[cd][4] += wait;
            scene_metrics[cd][5] += dma;
            scene_metrics[cd][6] += total;
        }
    scene_state = 1;
}

void __attribute__((noipa)) scene_complete(void)
{
    __asm__ volatile ("" ::: "memory");
}

int main(bool hard)
{
    (void)hard;
    prepare_display();
    run();
    scene_complete();
    VDP_drawText(scene_state ? "E1M1 TIC 200 - VRAM VERIFIED" : "SCENE TEST FAILED", 3, 23);
    number("MD TOTAL TICKS: ", scene_metrics[0][6], 25);
    number("SCD TOTAL TICKS: ", scene_metrics[1][6], 26);
    for (;;)
        SYS_doVBlankProcess();
}
