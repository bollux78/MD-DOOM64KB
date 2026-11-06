#include "ray_game.h"
#include "ray_origin.h"
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



__asm__(".pushsection .rodata.scd_ray_mode,\"a\"\n"
        ".global scd_ray_mode\n"
        "scd_ray_mode: .byte 0xa0\n"
        ".popsection");

#define RAY_BANK ((volatile uint16_t *)0x61c000)
enum { SLOTS = 64, STRIDE = 8, SLOT_WORDS = SLOTS * STRIDE };
volatile uint8_t scd_ray_available, scd_ray_profile;
volatile uint32_t scd_ray_sight_ticks, scd_ray_transition_ticks;
volatile uint16_t scd_ray_batches, scd_ray_accepted, scd_ray_queued;
static uint16_t epoch, submitted_tic, current_tic;
static uint8_t pending, ready, queued, active;

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

void SCD_RayBoot(void)
{
    if ((HW_VERSION & 0x20u) || CD_BIOS != 0x53454741UL)
        return;
    if (boot_sub() && wait_reply(&CD_READY, 0x5343))
    {
        if (CD_MODE & 1u)
            CD_MODE = 2;  /* Initial transfer is in 2M. */
        CD_REQUEST = COOKIE;
        if (wait_reply(&CD_ACK, COOKIE) && (CD_MODE & 7u) == 4u)
        {
            for (uint16_t i = 0; i < 2 * SLOT_WORDS; i += STRIDE)
                RAY_BANK[i] = 0;
            scd_ray_available = 1;
            return;
        }
    }
    CD_CTRL = 0;
}

void SCD_RayBegin(uint16_t tic, uint16_t map)
{
    active = map == 1 && (scd_ray_mode & 1u);
    current_tic = tic;
    queued = ready = 0;
    if (!scd_ray_available)
        return;
    if (pending)
    {
        if (CD_DONE != epoch)
        {
            if ((uint16_t)(tic - submitted_tic) > 8u || CD_READY == 0xdeadu)
            {
                CD_CTRL = 0;
                scd_ray_available = 0;
            }
            return;
        }
        if ((CD_MODE & 7u) != 4u)
        {
            CD_CTRL = 0;
            scd_ray_available = 0;
            return;
        }
        pending = 0;
        ready = (uint16_t)(tic - submitted_tic) == 1;
        scd_ray_transition_ticks += CD_DRAW_TICKS;
        ++scd_ray_batches;
    }
}

void SCD_RayEnd(void)
{
    if (!scd_ray_available || !active || pending || !queued)
        return;
    ++epoch;
    submitted_tic = current_tic;
    pending = 1;
    CD_REQUEST = epoch;
}

int SCD_RayQuery(uint32_t actor, int32_t x1, int32_t y1, int32_t x2, int32_t y2)
{
    if (!scd_ray_available || !active || pending)
        return 0;
    x1 = (x1 >> 16) - RAY_ORIGIN_X;
    y1 = (y1 >> 16) - RAY_ORIGIN_Y;
    x2 = (x2 >> 16) - RAY_ORIGIN_X;
    y2 = (y2 >> 16) - RAY_ORIGIN_Y;
    if ((uint32_t)(x1 | y1 | x2 | y2) >= 32768u)
        return 0;

    const uint16_t slot = (uint16_t)((actor >> 2) ^ (actor >> 9)) & (SLOTS - 1u);
    volatile uint16_t *old = RAY_BANK + (epoch & 1u) * SLOT_WORDS + slot * STRIDE;
    const uint16_t key = (uint16_t)actor;
    const uint16_t high = (uint16_t)(actor >> 16);
    const bool blocked = ready && old[0] == epoch && old[1] == key && old[2] == high &&
                         (old[3] >> 3) == (x1 >> 3) && (old[4] >> 3) == (y1 >> 3) &&
                         (old[5] >> 3) == (x2 >> 3) && (old[6] >> 3) == (y2 >> 3) && old[7];
    const uint16_t next = epoch + 1u;
    if (next == 0 || next == COOKIE)
    {
        CD_CTRL = 0;
        scd_ray_available = 0;
        return 0;
    }
    volatile uint16_t *job = RAY_BANK + (next & 1u) * SLOT_WORDS + slot * STRIDE;
    job[0] = next;
    job[1] = key;
    job[2] = high;
    job[3] = x1;
    job[4] = y1;
    job[5] = x2;
    job[6] = y2;
    job[7] = 0;
    queued = 1;
    ++scd_ray_queued;
    if (blocked)
        ++scd_ray_accepted;
    return blocked;
}

uint16_t SCD_RayClock(void)
{
    return CD_TIMER;
}

void SCD_RayProfile(uint16_t start)
{
    scd_ray_sight_ticks += (CD_TIMER - start) & 0xfffu;
}
