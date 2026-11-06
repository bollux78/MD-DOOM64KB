#include <genesis.h>
#include "scd_probe_sub.h"

#define HW_VERSION (*(volatile const u8 *)0xa10001)
#define CD_BIOS (*(volatile const u32 *)0x400100)
#define CD_CTRL (*(volatile u8 *)0xa12001)
#define CD_MODE (*(volatile u16 *)0xa12002)
#define CD_TIMER (*(volatile const u16 *)0xa1200c)
#define CD_DRAW_TICKS (*(volatile const u16 *)0xa12024)
#define CD_REQUEST (*(volatile u16 *)0xa12018)
#define CD_READY (*(volatile const u16 *)0xa12020)
#define CD_DONE (*(volatile const u16 *)0xa12028)
#define CD_STATUS (*(volatile const u16 *)0xa1202a)
#define CD_ACK (*(volatile const u16 *)0xa12026)
#define CD_PRG ((volatile u16 *)0x420000)
#define WORD_MARKER (*(volatile const u16 *)0x600000)
#define TIMEOUT 60
#define COOKIE 0x37e1u

_Static_assert(SUB_PROGRAM_WORDS > 0 && SUB_PROGRAM_WORDS < 65536u,
               "sub-CPU image must fit in one Program RAM bank");

static bool wait_control(u8 mask, u8 value)
{
    for (u16 i = 0; i < TIMEOUT; ++i)
    {
        if ((CD_CTRL & mask) == value)
            return TRUE;
        SYS_doVBlankProcess();
    }
    return FALSE;
}

static bool boot_sub(void)
{
    SYS_disableInts();
    CD_MODE = 0xff00;
    CD_CTRL = 3;
    CD_CTRL = 2;
    CD_CTRL = 0;
    SYS_enableInts();
    for (u16 i = 0; i < 128; ++i)
        __asm__ volatile ("nop");
    if (!wait_control(1, 0))
        return FALSE;

    CD_CTRL = 3;
    if (!wait_control(3, 3))
        return FALSE;
    CD_MODE = 0;
    CD_REQUEST = 0;
    for (u16 i = 0; i < SUB_PROGRAM_WORDS; ++i)
        CD_PRG[i] = sub_program[i];
    for (u16 i = 0; i < SUB_PROGRAM_WORDS; ++i)
        if (CD_PRG[i] != sub_program[i])
            return FALSE;

    CD_CTRL = 0;
    if (!wait_control(1, 0))
        return FALSE;
    CD_CTRL = 1;
    return wait_control(3, 1);
}



enum { REPORT_WORDS = 11 };
volatile u32 ray_bench_result[REPORT_WORDS + 1];

static bool wait_reply(volatile const u16 *reg, u16 value)
{
    for (u16 frame = 0; frame < 600; ++frame)
    {
        if (*reg == value)
            return TRUE;
        if (CD_READY == 0xdeadu)
            return FALSE;
        SYS_doVBlankProcess();
    }
    return FALSE;
}

static void run_bench(void)
{
    if ((HW_VERSION & 0x20u) || CD_BIOS != 0x53454741UL)
    {
        ray_bench_result[0] = 1;
        return;
    }
    if (!boot_sub() || !wait_reply(&CD_READY, 0x5343))
        goto fail;
    if (CD_MODE & 1u)
        CD_MODE = 2;
    CD_REQUEST = 1;
    if (!wait_reply(&CD_DONE, 1) || (CD_MODE & 7u) != 1u)
        goto fail;
    const volatile u32 *const report = (const volatile u32 *)0x630000;
    for (u16 i = 0; i < REPORT_WORDS; ++i)
        ray_bench_result[i + 1u] = report[i];
    ray_bench_result[0] = 2;
    return;
fail:
    CD_CTRL = 0;
    ray_bench_result[0] = 3;
}

void __attribute__((noipa)) ray_bench_complete(void)
{
    __asm__ volatile ("" ::: "memory");
}

static void row(const char *label, u32 value, u16 y)
{
    char digits[12];
    VDP_drawText(label, 2, y);
    uintToStr(value, digits, 1);
    VDP_drawText(digits, 29, y);
}

int main(bool hard_reset)
{
    (void)hard_reset;
    VDP_setScreenWidth320();
    VDP_drawText("doom-md-scd-asic-rays-v3.bin", 8, 2);
    run_bench();
    ray_bench_complete();
    if (ray_bench_result[0] == 2)
    {
        row("RAYS", ray_bench_result[1], 5);
        row("ASIC SETUP TICKS", ray_bench_result[2], 7);
        row("ASIC DRAW TICKS", ray_bench_result[3], 8);
        row("ASIC SCAN TICKS", ray_bench_result[4], 9);
        row("SUB DDA TICKS", ray_bench_result[5], 10);
        row("ASIC DDA MISMATCH", ray_bench_result[6], 12);
        row("FALSE BLOCKED", ray_bench_result[7], 13);
        row("FALSE CLEAR", ray_bench_result[8], 14);
        row("NATIVE VISIBLE", ray_bench_result[9], 15);
        row("NATIVE BLOCKED", ray_bench_result[10], 16);
        row("ASIC TIMEOUTS", ray_bench_result[11], 17);
    }
    else
        VDP_drawText(ray_bench_result[0] == 1 ? "SEGA CD NOT DETECTED" : "COMMUNICATION FAILED", 3, 6);
    for (;;)
        SYS_doVBlankProcess();
}
