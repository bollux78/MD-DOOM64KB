/* N0: does the Mega-CD 1M "cell image" view turn a linear bitmap written by the sub-CPU into
 * VDP tiles, and can one DMA move a whole 256x128 frame (16 KiB) to VRAM?
 * Sub writes linear 4bpp, stride 256 B, at bank+0x10000 (64x16-cell view). MD reads the bank's
 * cell view at 0x630000 (cart mode: Word RAM 0x600000, cell image +0x20000, 64x16 view +0x10000).
 * Expected tile order: column-major, tile t = column*16 + row. */
#include <genesis.h>
#include <string.h>
#include "sub_program.h"

#define HW_VERSION (*(volatile const u8 *)0xA10001)
#define CD_BIOS_HEADER (*(volatile const u32 *)0x400100)
#define CD_SUB_BYTE (*(volatile u8 *)0xA12001)
#define CD_MEMCTRL (*(volatile u16 *)0xA12002)
#define CD_MAIN_SEQ (*(volatile u16 *)0xA12010)
#define CD_MAIN_DATA (*(volatile u16 *)0xA12012)
#define CD_MAIN_SWAP (*(volatile u16 *)0xA12018)
#define CD_SUB_SIG (*(volatile const u16 *)0xA12020)
#define CD_SUB_ACK (*(volatile const u16 *)0xA12026)
#define CD_TIMER (*(volatile const u16 *)0xa1200c)
#define CD_PRGRAM ((volatile u16 *)0x420000)
#define WORD_ID (*(volatile const u16 *)0x600000)
#define LINEAR ((volatile const u8 *)0x610000)
#define CELLS ((volatile const u16 *)0x630000)
#define VDP_CTRL (*(volatile u32 *)0xc00004)
#define VDP_CTRL16 (*(volatile u16 *)0xc00004)
#define VDP_STATUS (*(volatile const u16 *)0xc00004)
#define VDP_DATA (*(volatile u16 *)0xc00000)
enum { WORDS = 8192, DEST = 0x2000, TIMEOUT = 60 };

/* rows: cpu-view check, dma display-off, dma 3 VBlanks display-on.
 * cols: completed, bad words, ticks, late */
volatile u32 cell_result[3][4];
volatile u16 cell_state;
static u16 request;
static u16 expected[WORDS];

void __attribute__((noipa)) cell_complete(void) { __asm__ volatile ("" ::: "memory"); }

static bool wait_sub(u8 mask, u8 value)
{
    for (u16 f = 0; f < TIMEOUT; f++) { if ((CD_SUB_BYTE & mask) == value) return TRUE; SYS_doVBlankProcess(); }
    return FALSE;
}
static bool boot_sub(void)
{
    SYS_disableInts();
    CD_MEMCTRL = 0xFF00; CD_SUB_BYTE = 3; CD_SUB_BYTE = 2; CD_SUB_BYTE = 0;
    SYS_enableInts();
    for (u16 i = 0; i < 128; i++) __asm__ volatile ("nop");
    if (!wait_sub(1, 0)) return FALSE;
    CD_SUB_BYTE = 3;
    if (!wait_sub(3, 3)) return FALSE;
    CD_MEMCTRL = 0; CD_MAIN_SEQ = 0; CD_MAIN_SWAP = 0; CD_MAIN_DATA = 0;
    for (u32 i = 0; i < SUB_PROGRAM_WORDS; i++) CD_PRGRAM[i] = sub_program[i];
    for (u32 i = 0; i < SUB_PROGRAM_WORDS; i++) if (CD_PRGRAM[i] != sub_program[i]) return FALSE;
    CD_SUB_BYTE = 0;
    if (!wait_sub(1, 0)) return FALSE;
    CD_SUB_BYTE = 1;
    return wait_sub(3, 1);
}
static bool swap(void)
{
    const u16 mode = (CD_MEMCTRL & 5u) ^ 1u;
    CD_MAIN_SWAP = ++request;
    for (u32 t = 0; t < 100000UL; ++t)
        if (CD_SUB_ACK == request && (CD_MEMCTRL & 5u) == mode) return WORD_ID == request;
    return FALSE;
}
static u32 command(u16 a) { return ((u32)(a & 0x3fffu) << 16) | (a >> 14); }
static u16 elapsed(u16 s) { return (CD_TIMER - s) & 0xfffu; }

static void dma_cells(u16 first, u16 count)
{
    const volatile u16 *src = CELLS + first;
    const u16 dest = DEST + first * 2u;
    const u32 from = ((u32)(src + 1) >> 1) & 0x7fffffUL;  /* Word RAM DMA: one-word read delay */
    VDP_CTRL16 = 0x8f02;
    VDP_CTRL16 = 0x9300 | (count & 0xff);
    VDP_CTRL16 = 0x9400 | (count >> 8);
    VDP_CTRL16 = 0x9500 | (from & 0xff);
    VDP_CTRL16 = 0x9600 | ((from >> 8) & 0xff);
    VDP_CTRL16 = 0x9700 | ((from >> 16) & 0x7f);
    VDP_CTRL = command(dest) | 0x40000080UL;
    VDP_CTRL = command(dest) | 0x40000000UL;
    VDP_DATA = src[0];
    VDP_DATA = src[1];
}
static u16 verify_vram(void)
{
    u16 bad = 0;
    VDP_CTRL = command(DEST);
    for (u16 i = 0; i < WORDS; i++) bad += VDP_DATA != expected[i];
    return bad;
}
static void poison(void)
{
    VDP_CTRL = command(DEST) | 0x40000000UL;
    for (u16 i = 0; i < WORDS; i++) VDP_DATA = 0xA5A5;
}

static void run(void)
{
    if ((HW_VERSION & 0x20u) || CD_BIOS_HEADER != 0x53454741UL) { cell_state = 1; return; }
    if (!boot_sub()) { cell_state = 2; return; }
    for (u16 n = 0; CD_SUB_SIG != 0x5343u || (CD_MEMCTRL & 5u) != 4u; ++n)
    {
        if (n == TIMEOUT) { cell_state = 2; return; }
        SYS_doVBlankProcess();
    }
    if (!swap()) { cell_state = 3; return; }
    /* Expected tiles from the LINEAR view of the same bank. */
    for (u16 c = 0; c < 32; c++)
        for (u16 r = 0; r < 16; r++)
            for (u16 l = 0; l < 8; l++)
            {
                const volatile u8 *line = LINEAR + (u32)(r * 8u + l) * 256u + c * 4u;
                const u16 w = (u16)(c * 16u + r) * 16u + l * 2u;
                expected[w] = ((u16)line[0] << 8) | line[1];
                expected[w + 1] = ((u16)line[2] << 8) | line[3];
            }
    /* 1) CPU read of the cell view. */
    u16 bad = 0, s = CD_TIMER;
    for (u16 i = 0; i < WORDS; i++) bad += CELLS[i] != expected[i];
    cell_result[0][0] = 1; cell_result[0][1] = bad; cell_result[0][2] = elapsed(s);
    /* 2) one 16 KiB DMA, display off. */
    VDP_setReg(1, VDP_getReg(1) | 0x10);
    for (u16 t = 0; t < 8; t++)
    {
        poison();
        SYS_disableInts();
        VDP_setEnable(FALSE);
        s = CD_TIMER;
        dma_cells(0, WORDS);
        const u16 ticks = elapsed(s);
        VDP_setEnable(TRUE);
        SYS_enableInts();
        cell_result[1][0]++; cell_result[1][1] += verify_vram(); cell_result[1][2] += ticks;
    }
    /* 3) display ON, three VBlanks (2731 + 2731 + 2730 words), each must finish inside VBlank. */
    static const u16 part[3][2] = { {0, 2731}, {2731, 2731}, {5462, 2730} };
    for (u16 t = 0; t < 8; t++)
    {
        poison();
        SYS_disableInts();
        u32 ticks = 0, late = 0;
        for (u16 p = 0; p < 3; p++)
        {
            while (VDP_STATUS & 8u) ;
            while (!(VDP_STATUS & 8u)) ;
            s = CD_TIMER;
            dma_cells(part[p][0], part[p][1]);
            ticks += elapsed(s);
            late += !(VDP_STATUS & 8u);
        }
        SYS_enableInts();
        cell_result[2][0]++; cell_result[2][1] += verify_vram(); cell_result[2][2] += ticks; cell_result[2][3] += late;
    }
    cell_state = 4;
}

static void line(const char *label, u32 v, u16 y)
{
    char t[40], d[12];
    uintToStr(v, d, 1); strcpy(t, label); strcat(t, d);
    VDP_drawText(t, 1, y);
}

int main(bool hard)
{
    (void)hard;
    VDP_drawText("doom-md-scd-cell-image.bin", 1, 1);
    run();
    cell_complete();
    const bool pass = cell_state == 4 && !cell_result[0][1] && !cell_result[1][1] && !cell_result[2][1];
    VDP_drawText(pass ? "N0 CELL IMAGE PASS" : "N0 CELL IMAGE FAIL", 1, 3);
    line("STATE ", cell_state, 4);
    line("CPU VIEW BAD WORDS ", cell_result[0][1], 6);
    line("DMA 16K BAD WORDS ", cell_result[1][1], 7);
    line("DMA 16K TICKS/8 ", cell_result[1][2], 8);
    line("3-VBL DMA BAD WORDS ", cell_result[2][1], 10);
    line("3-VBL DMA TICKS/8 ", cell_result[2][2], 11);
    line("3-VBL LATE PARTS ", cell_result[2][3], 12);
    for (;;) SYS_doVBlankProcess();
    return 0;
}
