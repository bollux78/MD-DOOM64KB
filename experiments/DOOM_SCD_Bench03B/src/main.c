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
#define CD_SUB_BEAT (*(volatile const u16 *)0xA12022)
#define CD_SUB_RESULT (*(volatile const u16 *)0xA12024)
#define CD_SUB_ACK (*(volatile const u16 *)0xA12026)
#define CD_PRGRAM ((volatile u16 *)0x420000)

#define SUB_READY 0x5343u
#define SUB_FAULT 0xDEADu
#define TIMEOUT_VBLANKS 60u
#define COMMAND_INTERVAL 10u

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

static const char *wait_ready(void)
{
    const u16 first_beat = CD_SUB_BEAT;
    for (u16 frame = 0; frame < TIMEOUT_VBLANKS; frame++)
    {
        const u16 signature = CD_SUB_SIG;
        if (signature == SUB_FAULT)
            return "SUB CPU EXCEPTION";
        if (signature == SUB_READY && CD_SUB_BEAT != first_beat)
            return NULL;
        SYS_doVBlankProcess();
    }
    return CD_SUB_SIG == SUB_READY ? "HEARTBEAT STALLED" : "SIGNATURE MISSING";
}

int main(bool hard)
{
    (void)hard;
    VDP_setScreenWidth320();
    VDP_setPlaneSize(64, 32, TRUE);
    VDP_drawText("DOOM SCD / BENCH 03B", 2, 2);
    VDP_drawText("DUAL 68000 / MODE 1", 2, 4);

    const bool cd_flag = (HW_VERSION & 0x20u) == 0;
    const bool cd_bios = CD_BIOS_HEADER == 0x53454741UL;
    VDP_drawText(cd_flag ? "CD FLAG SET" : "NO CD FLAG", 2, 6);
    VDP_drawText(cd_bios ? "CD BIOS SIGNATURE FOUND" : "NO CD BIOS SIGNATURE", 2, 7);
    if (!cd_flag && !cd_bios)
    {
        VDP_drawText("NO SEGA CD DETECTED", 2, 9);
        while (TRUE)
            SYS_doVBlankProcess();
    }

    const char *failure = boot_sub();
    if (failure)
    {
        VDP_drawText(failure, 2, 9);
        number("SUB CTRL: ", CD_SUBCTRL, 15);
        number("MEM CTRL: ", CD_MEMCTRL, 16);
        while (TRUE)
            SYS_doVBlankProcess();
    }

    VDP_drawText("BOOT SEQUENCE: OK", 2, 9);
    failure = wait_ready();
    VDP_drawText(failure ? failure : "SUB SIGNATURE: SC (READY)", 2, 10);

    u32 frame = 0, sent_at = 0, sent = 0, ok = 0, errors = 0, beat_changes = 0;
    u16 sequence = 0, expected = 0, prev_beat = CD_SUB_BEAT;
    bool pending = FALSE;
    while (TRUE)
    {
        SYS_doVBlankProcess();
        frame++;

        if (!failure && CD_SUB_SIG == SUB_FAULT)
        {
            failure = "SUB CPU EXCEPTION";
            errors++;
            VDP_drawText(failure, 2, 11);
        }
        if (!failure && pending)
        {
            if (CD_SUB_ACK == sequence)
            {
                pending = FALSE;
                if (CD_SUB_RESULT == expected)
                    ok++;
                else
                    errors++;
            }
            else if (frame - sent_at >= TIMEOUT_VBLANKS)
            {
                failure = "COMMAND ACK TIMEOUT";
                errors++;
                VDP_drawText(failure, 2, 11);
            }
        }
        if (!failure && !pending && frame - sent_at >= COMMAND_INTERVAL)
        {
            sequence++;
            const u16 payload = (u16)(sequence * 257u) ^ 0x1357u;
            expected = payload ^ 0x5A5Au;
            CD_MAIN_DATA = payload;
            CD_MAIN_SEQ = sequence;
            sent_at = frame;
            sent++;
            pending = TRUE;
        }

        if ((frame % 30u) == 0)
        {
            const u16 beat = CD_SUB_BEAT;
            if (beat != prev_beat)
                beat_changes++;
            prev_beat = beat;
            number("VBLANKS: ", frame, 14);
            number("SUB CTRL: ", CD_SUBCTRL, 15);
            number("MEM CTRL: ", CD_MEMCTRL, 16);
            number("SUB HEARTBEAT: ", beat, 18);
            number("BEAT CHANGES: ", beat_changes, 19);
            number("COMMANDS SENT: ", sent, 21);
            number("COMMANDS OK: ", ok, 22);
            number("ERRORS: ", errors, 23);
            number("ACK SEQUENCE: ", CD_SUB_ACK, 24);
        }
    }
}
