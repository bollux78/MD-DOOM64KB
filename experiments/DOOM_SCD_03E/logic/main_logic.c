#include "logic_packet.h"
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

volatile uint8_t scd_available;
/* stage.py writes this cartridge byte and updates the ROM checksum. */
__asm__(".pushsection .rodata.scd_logic_mode,\"a\"\n"
        ".global scd_logic_mode\n"
        "scd_logic_mode: .byte 0xa0\n"
        ".popsection");
uint8_t scd_logic_loaded;
volatile uint16_t scd_sight_calls, scd_sound_calls, scd_ray_calls;
static uint16_t sequence;
static volatile LogicPacket *const packet = (volatile LogicPacket *)0x600000;

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

static bool round_trip(void)
{
    for (u16 i = 0; i < TIMEOUT; ++i)
    {
        if (CD_READY == 0xdead)
            return FALSE;
        if (CD_READY == 0x5343 && (CD_MODE & 5u) == 4u)
        {
            CD_REQUEST = COOKIE;
            for (u16 frame = 0; frame < TIMEOUT; ++frame)
            {
                if (CD_READY == 0xdead)
                    return FALSE;
                if (CD_ACK == COOKIE && (CD_MODE & 5u) == 5u)
                    return WORD_MARKER == COOKIE;
                SYS_doVBlankProcess();
            }
            return FALSE;
        }
        SYS_doVBlankProcess();
    }
    return FALSE;
}

void SCD_Probe(void)
{
    scd_available = 0;
    if ((HW_VERSION & 0x20u) || CD_BIOS != 0x53454741UL)
        return;
    scd_available = boot_sub() && round_trip();
    sequence = COOKIE;
    if (!scd_available)
        CD_CTRL = 0;
}


volatile LogicPacket *SCD_LogicPacket(void)
{
    return packet;
}

static bool wait_reply(volatile const uint16_t *reg, uint16_t id)
{
    for (uint32_t tries = 0; tries < 240000UL; ++tries)
    {
        if (*reg == id)
            return TRUE;
        if (CD_READY == 0xdeadu)
            break;
    }
    return FALSE;
}

static bool exchange(uint16_t command, uint16_t count)
{
    const uint16_t mode = (CD_MODE & 5u) ^ 1u;
    packet->command = command;
    packet->count = count;
    packet->sequence = ++sequence;
    CD_REQUEST = sequence;
    return wait_reply(&CD_ACK, sequence) && (CD_MODE & 5u) == mode &&
           wait_reply(&CD_DONE, sequence) && CD_STATUS == 0;
}

int SCD_LogicCall(uint16_t command, uint16_t count)
{
    if (!scd_available)
        return 0;
    if (exchange(command, count) && exchange(0, 0))
    {
        if (command == SIGHT_BSP)
            ++scd_sight_calls;
        else if (command == SOUND_FLOOD)
            ++scd_sound_calls;
        else if (command == SORT_INTERCEPTS)
            ++scd_ray_calls;
        return 1;
    }
    scd_available = 0;
    CD_CTRL = 0;
    return 0;
}
