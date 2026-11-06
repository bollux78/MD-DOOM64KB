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
enum { TRIALS = 32, BASE = 0x2000, SECOND = 0x4000 };
/* Rows: contiguous native/CD, two-plane per-row native/CD (SGDK, display off),
 * then M1+M2+M6: plane-pitch image, 2 direct-register DMAs inside VBlank with the
 * display ON, native RAM reference / Word RAM.
 * Columns: completed, swap ticks, DMA ticks, combined ticks, bad words,
 * trials that left VBlank before the DMA finished. */
enum { MODES = 6, PLANE_ROWS = 21, PLANE_WORDS = PLANE_ROWS * 64 };
volatile u32 delivery_result[MODES][6];
static u16 plane_native[2 * PLANE_WORDS];
#define WORD_PLANE ((volatile const u16 *)0x604000)
#define VDP_STATUS (*(volatile const u16 *)0xc00004)
#define VDP_CTRL16 (*(volatile u16 *)0xc00004)
volatile u16 delivery_state;
static u16 native[WORD_COUNT + 1];
static u16 request;

static u16 check_row(const u16 *src, u16 dest, u16 count);

static u16 elapsed(u16 start)
{
    return (CD_TIMER - start) & 0xfffu;
}

static u32 command(u16 address)
{
    return ((u32)(address & 0x3fffu) << 16) | (address >> 14);
}

static bool swap(void)
{
    const u16 mode = (CD_MEMCTRL & 5u) ^ 1u;
    CD_MAIN_SWAP = ++request;
    for (u32 tries = 0; tries < 100000UL; ++tries)
        if (CD_SUB_ACK == request && (CD_MEMCTRL & 5u) == mode)
            return WORD_ID == request;
    return FALSE;
}

static void dma_row(const volatile u16 *src, u16 dest, u16 count, bool cd)
{
    /* One-word read-delay compensation verified by the 03D transport probe. */
    DMA_doDma(DMA_VRAM, (void *)(src + cd), dest, count, 2);
    VDP_waitDMACompletion();
    if (cd)
    {
        VDP_CTRL = command(dest) | 0x40000000UL;
        VDP_DATA = src[0];
        VDP_DATA = src[1];
    }
}

/* M6: DMA by register writes, no SGDK. 68000 is halted by the VDP during the
 * transfer, so no software wait is needed. */
static void dma_direct(const volatile u16 *src, u16 dest, u16 count, bool cd)
{
    const u32 from = ((u32)(src + cd) >> 1) & 0x7fffffUL;
    VDP_CTRL16 = 0x8f02;
    VDP_CTRL16 = 0x9300 | (count & 0xff);
    VDP_CTRL16 = 0x9400 | (count >> 8);
    VDP_CTRL16 = 0x9500 | (from & 0xff);
    VDP_CTRL16 = 0x9600 | ((from >> 8) & 0xff);
    VDP_CTRL16 = 0x9700 | ((from >> 16) & 0x7f);
    VDP_CTRL = command(dest) | 0x40000080UL;
    if (cd)
    {
        VDP_CTRL = command(dest) | 0x40000000UL;
        VDP_DATA = src[0];
        VDP_DATA = src[1];
    }
}

static void frame_plane(const volatile u16 *src, bool cd)
{
    dma_direct(src, BASE + 128u, PLANE_WORDS, cd);
    dma_direct(src + PLANE_WORDS, SECOND + 128u, PLANE_WORDS, cd);
}

static u16 verify_plane(void)
{
    return check_row(plane_native, BASE + 128u, PLANE_WORDS) +
           check_row(plane_native + PLANE_WORDS, SECOND + 128u, PLANE_WORDS);
}

static void frame(const volatile u16 *src, bool rows, bool cd)
{
    if (!rows)
    {
        dma_row(src, BASE, WORD_COUNT, cd);
        return;
    }
    /* Same 38-word source rows and 64-word destination pitch as uncropped R128. */
    for (u16 y = 1; y < 22; ++y)
    {
        dma_row(src + y * 76u, BASE + y * 128u, 38, cd);
        dma_row(src + y * 76u + 38u, SECOND + y * 128u, 38, cd);
    }
}

static u16 check_row(const u16 *src, u16 dest, u16 count)
{
    u16 bad = 0;
    VDP_CTRL = command(dest);
    for (u16 i = 0; i < count; ++i)
        bad += VDP_DATA != src[i];
    return bad;
}

static u16 verify(bool rows)
{
    if (!rows)
        return check_row(native, BASE, WORD_COUNT);
    u16 bad = 0;
    for (u16 y = 1; y < 22; ++y)
    {
        bad += check_row(native + y * 76u, BASE + y * 128u, 38);
        bad += check_row(native + y * 76u + 38u, SECOND + y * 128u, 38);
    }
    return bad;
}

static void run(void)
{
    if ((HW_VERSION & 0x20u) || CD_BIOS_HEADER != 0x53454741UL)
    {
        delivery_state = 1;
        return;
    }
    if (boot_sub())
        return;
    for (u16 n = 0; CD_SUB_SIG != SUB_READY || (CD_MEMCTRL & 5u) != 4u; ++n)
    {
        if (n == TIMEOUT_VBLANKS)
            return;
        SYS_doVBlankProcess();
    }
    if (!swap())
        return;
    for (u16 i = 0; i < WORD_COUNT; ++i)
        native[i] = WORD_DATA[i];
    for (u16 y = 0; y < PLANE_ROWS; ++y)
        for (u16 x = 0; x < 64; ++x)
        {
            const u16 *row = native + (y + 1u) * 76u;
            plane_native[y * 64u + x] = x < 38 ? row[x] : 0;
            plane_native[PLANE_WORDS + y * 64u + x] = x < 38 ? row[38 + x] : 0;
        }

    VDP_setEnable(FALSE);
    for (u16 mode = 0; mode < 4; ++mode)
    {
        const bool cd = mode & 1u, rows = mode & 2u;
        for (u16 i = 0; i < TRIALS; ++i)
        {
            SYS_doVBlankProcess();
            SYS_disableInts();
            /* Poison the destination so a no-op DMA cannot pass. */
            VDP_CTRL = command(BASE + (rows ? 128u : 0u)) | 0x40000000UL;
            VDP_DATA = native[rows ? 76 : 0] ^ 0xffffu;
            const u16 start = CD_TIMER;
            const bool ok = !cd || swap();
            const u16 after_swap = CD_TIMER;
            if (ok)
                frame(cd ? WORD_DATA : native, rows, cd);
            const u16 combined = elapsed(start);
            const u16 dma = elapsed(after_swap);
            const u16 bad = ok ? verify(rows) : 1;
            SYS_enableInts();
            if (!ok || bad)
            {
                delivery_result[mode][4] += bad;
                VDP_setEnable(TRUE);
                return;
            }
            ++delivery_result[mode][0];
            delivery_result[mode][1] += (after_swap - start) & 0xfffu;
            delivery_result[mode][2] += dma;
            delivery_result[mode][3] += combined;
        }
    }
    VDP_setEnable(TRUE);
    /* M1+M2+M6: display ON, transfer inside VBlank. */
    VDP_setReg(1, VDP_getReg(1) | 0x10);
    for (u16 mode = 4; mode < MODES; ++mode)
    {
        const bool cd = mode & 1u;
        for (u16 i = 0; i < TRIALS; ++i)
        {
            SYS_disableInts();
            VDP_CTRL = command(BASE + 128u) | 0x40000000UL;
            VDP_DATA = plane_native[0] ^ 0xffffu;
            while (VDP_STATUS & 8u) ;          /* leave the current VBlank */
            while (!(VDP_STATUS & 8u)) ;       /* start of the next one */
            const u16 start = CD_TIMER;
            const bool ok = !cd || swap();
            const u16 after_swap = CD_TIMER;
            if (ok)
                frame_plane(cd ? WORD_PLANE : plane_native, cd);
            const bool late = !(VDP_STATUS & 8u);
            const u16 combined = elapsed(start);
            const u16 dma = elapsed(after_swap);
            const u16 bad = ok ? verify_plane() : 1;
            SYS_enableInts();
            if (!ok || bad)
            {
                delivery_result[mode][4] += bad;
                return;
            }
            ++delivery_result[mode][0];
            delivery_result[mode][1] += (after_swap - start) & 0xfffu;
            delivery_result[mode][2] += dma;
            delivery_result[mode][3] += combined;
            delivery_result[mode][5] += late;
        }
    }
    delivery_state = 2;
}

void __attribute__((noipa)) delivery_complete(void)
{
    __asm__ volatile ("" ::: "memory");
}

int main(bool hard)
{
    (void)hard;
    VDP_setScreenWidth320();
    VDP_drawText("doom-md-scd-frame-delivery.bin", 4, 1);
    run();
    delivery_complete();
    VDP_drawText(delivery_state == 2 ? "VRAM READBACK PASS" : "DELIVERY TEST FAILED", 3, 4);
    number("NATIVE PACKED TICKS: ", delivery_result[0][3], 7);
    number("SCD PACKED TICKS: ", delivery_result[1][3], 8);
    number("NATIVE ROW DMA TICKS: ", delivery_result[2][3], 10);
    number("SCD ROW DMA TICKS: ", delivery_result[3][3], 11);
    number("PACKED SWAP TICKS: ", delivery_result[1][1], 13);
    number("ROW SWAP TICKS: ", delivery_result[3][1], 14);
    number("NATIVE PLANE VBL TICKS: ", delivery_result[4][3], 15);
    number("SCD PLANE VBL TICKS: ", delivery_result[5][3], 16);
    number("SCD PLANE LATE: ", delivery_result[5][5], 17);
    VDP_drawText("32 FRAMES PER MODE", 3, 19);
    for (;;)
        SYS_doVBlankProcess();
}
