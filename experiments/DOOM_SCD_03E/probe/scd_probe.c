#include "scd_probe.h"
#include "packet.h"
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

volatile unsigned char scd_available;
volatile uint16_t scd_rendered_batches;
volatile uint16_t scd_textured_columns;
volatile uint16_t scd_render_fault;
volatile uint8_t scd_verify;
volatile uint32_t scd_copy_ticks, scd_wait_ticks, scd_sub_ticks, scd_pack_ticks;
volatile uint8_t scd_route;

enum { SCD_VERIFY_PIXELS = 1, SCD_PROFILE = 2, SCD_TEST_TIMEOUT = 4 };
enum {
    SCD_ROUTE_MASK = 3, SCD_REJECT_ALL = 3,
    SCD_EARLY_REJECT = 4, SCD_LUT_RESIDENT = 8, SCD_SHARE_SOURCE = 16
};
void SCD_LutBases(const uint8_t **base);
static void prepare_luts(void);

static uint8_t in_world;
static uint8_t pending;
static uint16_t sequence;
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
    sequence = COOKIE;
    if (scd_available)
        packet->lut_base[0] = packet->lut_base[1] = 0;
    else
        CD_CTRL = 0;
}

static void fail_render(uint16_t error)
{
    scd_render_fault = error;
    scd_available = 0;
    CD_CTRL = 0;
}

static void clear_packet(void)
{
    packet->columns = 0;
    packet->luts = 0;
    packet->last_source = 0;
}

void SCD_BeginWorld(void)
{
    in_world = scd_available;
    if (in_world)
    {
        clear_packet();
        if (scd_route & SCD_LUT_RESIDENT)
            prepare_luts();
    }
}

/* The BSP gives each wall its own rows. Merge edge nibbles so native
 * floors and ceilings can share bytes with the returned wall pixels. */
static int compose(uint8_t *fb, bool verify)
{
    const volatile uint8_t *frame = (const volatile uint8_t *)packet->frame;
    for (uint16_t i = 0; i < packet->columns; ++i)
    {
        const volatile ScdColumn *column = &packet->column[i];
        uint8_t *dst = fb + column->offset;
        const volatile uint8_t *src = frame + column->offset;
        uint16_t rows = column->rows;

        if (verify)
        {
            uint16_t phase = column->phase;
            for (uint16_t row = column->odd; row < rows + column->odd; ++row)
            {
                uint8_t pair = src[(row >> 1) * SCD_STRIDE];
                uint8_t pixel = row & 1u ? pair & 15u : pair >> 4;
                if (pixel != packet->lut[column->lut][packet->source[column->source_slot][phase >> 9]])
                    return 0;
                phase += column->step;
            }
        }
        if (column->odd)
        {
            *dst = (*dst & 0xf0u) | (*src & 0x0fu);
            dst += SCD_STRIDE;
            src += SCD_STRIDE;
            --rows;
        }
        for (uint16_t pairs = rows >> 1; pairs; --pairs)
        {
            *dst = *src;
            dst += SCD_STRIDE;
            src += SCD_STRIDE;
        }
        if (rows & 1u)
            *dst = (*dst & 0x0fu) | (*src & 0xf0u);
    }
    return 1;
}

/* Word RAM and these buffers are word-aligned. Each MOVE.L on the
 * 68000 is two 16-bit bus transfers, so this also works at address 2 mod 4. */
static void copy_bursts(volatile void *dst, const volatile void *src, uint16_t bursts)
{
    if (!bursts)
        return;
    --bursts;
    __asm__ volatile (
        "1: move.l (%[src])+,(%[dst])+\n\t"
        "move.l (%[src])+,(%[dst])+\n\t"
        "move.l (%[src])+,(%[dst])+\n\t"
        "move.l (%[src])+,(%[dst])+\n\t"
        "dbra %[n],1b"
        : [src] "+a"(src), [dst] "+a"(dst), [n] "+d"(bursts)
        : : "cc", "memory");
}

static uint16_t elapsed(uint16_t start)
{
    return (CD_TIMER - start) & 0xfffu;
}

static bool wait_word(volatile const uint16_t *reg, uint16_t id)
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

/* Exchange banks once. The sub starts the new batch as soon as it owns
 * it, while the main CPU composes the completed batch in the other bank. */
static void exchange(void)
{
    const uint8_t flags = scd_verify;
    const uint16_t previous = sequence;
    const bool submitted = packet->columns != 0;
    uint16_t mark = flags & SCD_PROFILE ? CD_TIMER : 0;
    if (pending)
    {
        if (!wait_word(&CD_DONE, previous) || CD_STATUS)
        {
            fail_render(1);
            return;
        }
        if (flags & SCD_PROFILE)
        {
            scd_wait_ticks += elapsed(mark);
            scd_sub_ticks += CD_DRAW_TICKS;
        }
    }

    const uint16_t id = previous + 1u;
    const uint16_t expected_mode = (CD_MODE & 5u) ^ 1u;
    packet->sequence = id;
    if (flags & SCD_PROFILE)
        mark = CD_TIMER;
    CD_REQUEST = id;
    sequence = id;
    /* The debugger can withhold the expected ACK to exercise the real timeout. */
    const uint16_t expected_ack = flags & SCD_TEST_TIMEOUT ? id ^ 0x8000u : id;
    if (!wait_word(&CD_ACK, expected_ack) || (CD_MODE & 5u) != expected_mode)
    {
        fail_render(1);
        return;
    }
    if (flags & SCD_PROFILE)
        scd_wait_ticks += elapsed(mark);

    if (pending)
    {
        if (packet->sequence != previous || !packet->columns ||
            packet->columns > SCD_MAX_COLUMNS)
        {
            fail_render(1);
            return;
        }
        if (flags & SCD_PROFILE)
            mark = CD_TIMER;
        if (!compose(SCD_DrawBuffer(), flags & SCD_VERIFY_PIXELS))
        {
            fail_render(2);
            return;
        }
        if (flags & SCD_PROFILE)
            scd_copy_ticks += elapsed(mark);
        scd_rendered_batches++;
        scd_textured_columns += packet->columns;
    }
    /* The first exchange returns the bank used by the bootstrap handshake. */
    if (previous == COOKIE && !pending)
        packet->lut_base[0] = packet->lut_base[1] = 0;
    pending = submitted;
    clear_packet();
    if (scd_route & SCD_LUT_RESIDENT)
        prepare_luts();
}

int SCD_EndWorld(void)
{
    if (in_world && scd_available && packet->columns)
        exchange();
    if (in_world && scd_available && pending)
        exchange();  /* empty handoff retrieves the final batch before sprites */
    const int complete = !in_world || scd_available;
    in_world = 0;
    return complete;
}

typedef uint16_t __attribute__((may_alias)) SourceWord;

static void copy_bytes(volatile uint8_t *dst, const uint8_t *src, uint16_t bytes)
{
    uint16_t i = 0;
    if (!((uintptr_t)src & 1u))
    {
        copy_bursts(dst, src, bytes >> 4);
        i = bytes & ~15u;
        for (; i + 1u < bytes; i += 2)
            *(volatile uint16_t *)(dst + i) = *(const SourceWord *)(src + i);
    }
    else
    {
        for (; i + 1u < bytes; i += 2)
            *(volatile uint16_t *)(dst + i) = ((uint16_t)src[i] << 8) | src[i + 1u];
    }
    if (i < bytes)
        *(volatile uint16_t *)(dst + i) = (uint16_t)src[i] << 8;
}

static void prepare_luts(void)
{
    const uint8_t *base[SCD_LUT_BANKS];
    SCD_LutBases(base);
    for (uint16_t parity = 0; parity < SCD_LUT_BANKS; ++parity)
    {
        if (packet->lut_base[parity] != (uintptr_t)base[parity])
        {
            const uint16_t first = SCD_MAX_LUTS + parity * SCD_LUTS_PER_PARITY;
            copy_bytes(packet->lut[first], base[parity], SCD_LUTS_PER_PARITY * 256u);
            packet->lut_base[parity] = (uintptr_t)base[parity];
        }
    }
}

static uint16_t lut_slot(const uint8_t *lut, uint8_t options)
{
    const uint32_t key = (uintptr_t)lut;
    if (options & SCD_LUT_RESIDENT)
    {
        for (uint16_t parity = 0; parity < SCD_LUT_BANKS; ++parity)
        {
            const uint32_t offset = key - packet->lut_base[parity];
            if (offset < SCD_LUTS_PER_PARITY * 256u && !(offset & 255u))
                return SCD_MAX_LUTS + parity * SCD_LUTS_PER_PARITY + (offset >> 8);
        }
    }
    uint16_t slot = 0;
    while (slot < packet->luts && packet->lut_key[slot] != key)
        ++slot;
    if (slot == packet->luts)
    {
        packet->lut_key[slot] = key;
        copy_bytes(packet->lut[slot], lut, 256);
        packet->luts++;
    }
    return slot;
}

int SCD_Column(uint8_t *fb, uint8_t *dst, const uint8_t *source,
               const uint8_t *lut, uint16_t phase, uint16_t step,
               uint16_t rows, uint16_t odd)
{
    if (!in_world || !scd_available)
        return 0;

    const uint8_t options = scd_route;
    const uint8_t route = options & SCD_ROUTE_MASK;
    if (route == SCD_REJECT_ALL)
        return 0;
    const uint16_t limit = route == 1 ? rows : rows >> 1;

    uint32_t offset = (uintptr_t)dst - (uintptr_t)fb;
    if (!rows || rows > SCD_MAX_ROWS || odd > 1 || offset >= SCD_FRAME_BYTES ||
        offset + SCD_STRIDE * ((rows + odd - 1u) >> 1) >= SCD_FRAME_BYTES)
        return 0;

    /* Dispatch early enough to leave BSP work for the other CPU to overlap. */
    if (packet->columns == SCD_BATCH_COLUMNS || packet->luts == SCD_MAX_LUTS)
    {
        exchange();
        if (!scd_available)
            return 0;
    }

    const uint8_t profile = scd_verify & SCD_PROFILE;
    const uint16_t mark = profile ? CD_TIMER : 0;
    const uint32_t end = (uint32_t)phase + (uint32_t)step * (rows - 1u);
    uint16_t min_sample = phase >> 9;
    uint16_t max_sample = end >> 9;
    if (end > 0xffffu)
    {
        max_sample = min_sample;
        for (uint16_t i = 1, f = phase; i < rows; ++i)
        {
            f += step;
            if ((f >> 9) > max_sample)
                max_sample = f >> 9;
            if ((f >> 9) < min_sample)
                min_sample = f >> 9;
            if (route && (options & SCD_EARLY_REJECT) &&
                max_sample - (min_sample & ~1u) + 1u > limit)
                goto rejected;
        }
    }
    min_sample &= ~1u;
    const uint16_t bytes = max_sample - min_sample + 1u;
    if (route && bytes > limit)
        goto rejected;

    const uint16_t index = packet->columns;
    volatile ScdColumn *column = &packet->column[index];
    column->offset = offset;
    column->phase = phase;
    column->step = step;
    column->rows = rows;
    column->odd = odd;
    column->lut = lut_slot(lut, options);

    uint16_t source_slot = index;
    const uint32_t source_key = (uintptr_t)source;
    /* Only cartridge ROM sources are immutable. Reuse a copied range
     * only if it covers all samples in this command. */
    if ((options & SCD_SHARE_SOURCE) && source_key &&
        source_key < 0x400000UL && source_key == packet->last_source &&
        min_sample >= packet->last_min && max_sample <= packet->last_max)
    {
        source_slot = packet->last_slot;
    }
    else
    {
        copy_bytes(packet->source[index] + min_sample, source + min_sample, bytes);
        if (options & SCD_SHARE_SOURCE)
        {
            packet->last_source = source_key;
            packet->last_slot = index;
            packet->last_min = min_sample;
            packet->last_max = max_sample;
        }
    }
    column->source_slot = source_slot;
    packet->columns = index + 1u;
    if (profile)
        scd_pack_ticks += elapsed(mark);
    return 1;

rejected:
    if (profile)
        scd_pack_ticks += elapsed(mark);
    return 0;
}
