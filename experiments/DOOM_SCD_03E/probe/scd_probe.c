#include "scd_probe.h"
#include "packet.h"
#include <genesis.h>
#include "scd_probe_sub.h"

#define HW_VERSION (*(volatile const u8 *)0xa10001)
#define CD_BIOS (*(volatile const u32 *)0x400100)
#define CD_CTRL (*(volatile u8 *)0xa12001)
#define CD_MODE (*(volatile u16 *)0xa12002)
#define CD_REQUEST (*(volatile u16 *)0xa12018)
#define CD_READY (*(volatile const u16 *)0xa12020)
#define CD_STATUS (*(volatile const u16 *)0xa1202a)
#define CD_ACK (*(volatile const u16 *)0xa12026)
#define CD_PRG ((volatile u16 *)0x420000)
#define WORD_MARKER (*(volatile const u16 *)0x600000)
#define TIMEOUT 60
#define COOKIE 0x37e1u

volatile unsigned char scd_available;
volatile uint16_t scd_rendered_batches;
volatile uint16_t scd_textured_columns;
volatile uint16_t scd_render_fault;
volatile uint8_t scd_verify;
static uint8_t in_world;
static uint16_t textured_in_batch;
static volatile ScdPacket *const packet = (volatile ScdPacket *)0x600000;

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
    if (!scd_available)
        CD_CTRL = 0;
}

static void fail_render(uint16_t error)
{
    scd_render_fault = error;
    scd_available = 0;
    CD_CTRL = 0;
}

void SCD_BeginWorld(void)
{
    in_world = scd_available;
    if (in_world)
    {
        packet->columns = 0;
        packet->luts = 0;
        textured_in_batch = 0;
    }
}

/* Used by the emulator test to compare returned pixels against an
 * independent reference with the exact same input framebuffer. */
static void verify_batch(uint8_t *fb)
{
    for (uint16_t i = 0; i < packet->columns; ++i)
    {
        const volatile ScdColumn *column = &packet->column[i];
        uint16_t phase = column->phase;
        uint16_t lut = column->lut;
        uint8_t *dst = fb + column->offset;
        for (uint16_t row = column->odd; row < column->rows + column->odd; ++row)
        {
            uint8_t shade = lut == SCD_FLAT ? column->step :
                packet->lut[lut][column->source[phase >> 9]];
            if (row & 1u)
            {
                *dst = (*dst & 0xf0u) | shade;
                dst += SCD_STRIDE;
            }
            else
                *dst = (*dst & 0x0fu) | (shade << 4);
            phase += column->step;
        }
    }
}

void SCD_Flush(void)
{
    if (!in_world || !scd_available || !packet->columns)
        return;

    uint16_t *fb = (uint16_t *)SCD_DrawBuffer();
    for (uint16_t i = 0; i < SCD_FRAME_BYTES / 2; ++i)
        packet->frame[i] = fb[i];

    const uint16_t id = CD_ACK + 1u;
    packet->sequence = id;
    CD_REQUEST = id;
    for (uint32_t tries = 0; tries < 240000UL; ++tries)
    {
        if (CD_READY == 0xdead)
            break;
        if (CD_ACK != id || (CD_MODE & 5u) != 5u)
            continue;
        if (CD_STATUS || packet->sequence != id)
            break;

        if (scd_verify)
            verify_batch((uint8_t *)fb);
        for (uint16_t i = 0; i < SCD_FRAME_BYTES / 2; ++i)
        {
            uint16_t word = packet->frame[i];
            if (scd_verify && fb[i] != word)
            {
                fail_render(2);
                return;
            }
            fb[i] = word;
        }
        scd_rendered_batches++;
        scd_textured_columns += textured_in_batch;
        packet->columns = 0;
        packet->luts = 0;
        textured_in_batch = 0;
        return;
    }
    fail_render(1);
}

int SCD_EndWorld(void)
{
    SCD_Flush();
    const int complete = !in_world || scd_available;
    in_world = 0;
    return complete;
}

static void copy_bytes(volatile uint8_t *dst, const uint8_t *src, uint16_t bytes)
{
    uint16_t i = 0;
    for (; i + 1u < bytes; i += 2)
        *(volatile uint16_t *)(dst + i) = ((uint16_t)src[i] << 8) | src[i + 1u];
    if (i < bytes)
        *(volatile uint16_t *)(dst + i) = (uint16_t)src[i] << 8;
}

int SCD_Column(uint8_t *fb, uint8_t *dst, const uint8_t *source,
               const uint8_t *lut, uint16_t phase, uint16_t step,
               uint16_t rows, uint16_t odd)
{
    if (!in_world || !scd_available)
        return 0;

    uint32_t offset = (uintptr_t)dst - (uintptr_t)fb;
    if (!rows || rows > SCD_MAX_ROWS || odd > 1 || offset >= SCD_FRAME_BYTES ||
        offset + SCD_STRIDE * ((rows + odd - 1u) >> 1) >= SCD_FRAME_BYTES)
    {
        SCD_Flush();
        return 0;
    }

    if (packet->columns == SCD_MAX_COLUMNS || packet->luts == SCD_MAX_LUTS)
    {
        SCD_Flush();
        if (!scd_available)
            return 0;
    }

    volatile ScdColumn *column = &packet->column[packet->columns];
    column->offset = offset;
    column->phase = phase;
    column->step = step;
    column->rows = rows;
    column->odd = odd;
    column->lut = SCD_FLAT;
    if (source)
    {
        uint16_t slot = 0;
        const uint32_t key = (uintptr_t)lut;
        while (slot < packet->luts && packet->lut_key[slot] != key)
            ++slot;
        if (slot == packet->luts)
        {
            packet->lut_key[slot] = key;
            copy_bytes(packet->lut[slot], lut, 256);
            packet->luts++;
        }
        column->lut = slot;
        /* A patch post can be shorter than 128 bytes. Copy only the range
         * the real kernel can sample, including columns that wrap phase. */
        const uint32_t end = (uint32_t)phase + (uint32_t)step * (rows - 1u);
        uint16_t max_sample = end >> 9;
        if (end > 0xffffu)
        {
            max_sample = phase >> 9;
            for (uint16_t i = 1, f = phase; i < rows; ++i)
            {
                f += step;
                if ((f >> 9) > max_sample)
                    max_sample = f >> 9;
            }
        }
        copy_bytes(column->source, source, max_sample + 1u);
        textured_in_batch++;
    }
    packet->columns++;
    return 1;
}
