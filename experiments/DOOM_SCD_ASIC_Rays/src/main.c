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


volatile u16 asic_probe_result[7];

static bool wait_reply(volatile const u16 *reg, u16 value)
{
    for (u16 frame = 0; frame < TIMEOUT; ++frame)
    {
        if (*reg == value)
            return TRUE;
        if (CD_READY == 0xdeadu)
            return FALSE;
        SYS_doVBlankProcess();
    }
    return FALSE;
}

static void run_probe(void)
{
    if ((HW_VERSION & 0x20u) || CD_BIOS != 0x53454741UL)
    {
        asic_probe_result[0] = 1;
        return;
    }
    if (!boot_sub() || !wait_reply(&CD_READY, 0x5343))
        goto fail;

    CD_REQUEST = 1;
    if (!wait_reply(&CD_ACK, 1) || (CD_MODE & 5u) != 5u || WORD_MARKER != COOKIE)
        goto fail;

    CD_REQUEST = 2;
    if (!wait_reply(&CD_ACK, 2) || (CD_MODE & 4u))
        goto fail;
    if (CD_MODE & 1u)
        CD_MODE = 2;  /* DMNA applies only once both CPUs are in 2M. */
    CD_REQUEST = 3;
    if (!wait_reply(&CD_DONE, 3))
        goto fail;

    asic_probe_result[1] = CD_STATUS;
    asic_probe_result[2] = CD_DRAW_TICKS;
    asic_probe_result[3] = *(volatile const u16 *)0xa12022;
    asic_probe_result[4] = *(volatile const u16 *)0xa1202c;
    asic_probe_result[5] = *(volatile const u16 *)0xa1202e;
    CD_REQUEST = 4;
    if (!wait_reply(&CD_ACK, 4) || (CD_MODE & 5u) != 5u || WORD_MARKER != (COOKIE ^ 0xffffu))
        goto fail;
    asic_probe_result[6] = 1;
    asic_probe_result[0] = 2;
    return;
fail:
    CD_CTRL = 0;
    asic_probe_result[0] = 3;
}

void __attribute__((noipa)) asic_probe_complete(void)
{
    __asm__ volatile ("" ::: "memory");
}

int main(bool hard_reset)
{
    (void)hard_reset;
    VDP_setScreenWidth320();
    VDP_drawText("doom-md-scd-asic-probe.bin", 7, 2);
    run_probe();
    asic_probe_complete();
    if (asic_probe_result[0] == 2)
    {
        VDP_drawText(asic_probe_result[1] == 1 ? "ASIC 1M: MATCH" : "ASIC 1M: NO MATCH", 3, 6);
        VDP_drawText(asic_probe_result[3] == 1 ? "ASIC 2M: MATCH" : "ASIC 2M: NO MATCH", 3, 8);
        VDP_drawText("1M BANK EXCHANGE RESTORED", 3, 10);
        VDP_drawText("8X8 PIXEL TEST", 3, 12);
    }
    else
        VDP_drawText(asic_probe_result[0] == 1 ? "SEGA CD NOT DETECTED" : "COMMUNICATION FAILED", 3, 6);
    for (;;)
        SYS_doVBlankProcess();
}
