#include <stdbool.h>
#include <stdint.h>

#define REG(addr) (*(volatile uint16_t *)(addr))
#define STAMP_SIZE REG(0xff8058)
#define TIMER REG(0xff800c)
#define STAMPS ((volatile uint16_t *)0x080000)
#define MAP ((volatile uint16_t *)0x090000)
#define TRACE ((volatile uint16_t *)0x098000)
#define IMAGE ((volatile uint16_t *)0x0a0000)
#define REPORT ((volatile uint32_t *)0x0b0000)
enum { BATCHES = 4, RAYS = 64 };
enum { COUNT, SETUP, DRAW, SCAN, DDA, MISMATCH, FALSE_BLOCK, FALSE_CLEAR,
       NATIVE_CLEAR, NATIVE_BLOCK, TIMEOUTS, REPORT_WORDS };
extern const uint16_t ray_assets[];

static bool asic(uint16_t width, uint16_t rows)
{
    STAMP_SIZE = 6; /* 32-pixel stamps, 4096-pixel map, no wrapping */
    REG(0xff805a) = 0x4000;
    REG(0xff805c) = (rows - 1u) >> 3;
    REG(0xff805e) = 0x8000;
    REG(0xff8060) = 0;
    REG(0xff8062) = width;
    REG(0xff8064) = rows;
    REG(0xff8066) = 0x6000;
    for (uint32_t tries = 0; tries < 60000UL; ++tries)
        if (!(STAMP_SIZE & 0x8000u))
            return true;
    return false;
}

enum { CLEAR = UINT16_MAX, STRIDE = 8 };
#define HITS ((volatile uint32_t *)0x0b0040)

static uint16_t first_nibble(uint16_t word)
{
    uint16_t i = 0;
    while (!(word & 0xf000u))
    {
        word <<= 4;
        ++i;
    }
    return i;
}

static uint16_t scan(uint16_t row, uint16_t length, uint16_t stride)
{
    const volatile uint16_t *word = IMAGE + row * 2u;
    uint16_t i = 0;
    while (length >= 8)
    {
        const uint16_t a = word[0], b = word[1];
        if (a)
            return i + first_nibble(a);
        if (b)
            return i + 4u + first_nibble(b);
        word += stride;
        length -= 8;
        i += 8;
    }
    if (length >= 4)
    {
        const uint16_t a = *word++;
        if (a)
            return i + first_nibble(a);
        length -= 4;
        i += 4;
    }
    if (length)
    {
        const uint16_t a = *word & (uint16_t)(0xffffu << ((4u - length) * 4u));
        if (a)
            return i + first_nibble(a);
    }
    return CLEAR;
}


#define RAY_BANK ((volatile uint16_t *)0x0b8000)
#define SLOT_WORDS (RAYS * STRIDE)

void load_ray_map(void)
{
    const uint16_t *src = ray_assets;
    const uint16_t words = *src++;
    for (uint16_t i = 0; i < words; ++i)
        STAMPS[i] = *src++;
    for (uint16_t i = 0; i < 16384; ++i)
        MAP[i] = *src++;
}

int run_ray_batch(uint32_t epoch)
{
    uint16_t slots[RAYS], lengths[RAYS], rows = 0, width = 0;
    volatile uint16_t *const bank = RAY_BANK + (epoch & 1u) * SLOT_WORDS * 2u;
    for (uint16_t i = 0; i < RAYS; ++i)
    {
        volatile uint16_t *const job = bank + i * STRIDE * 2u;
        if (job[0] != epoch)
            continue;
        const int32_t x = job[6], y = job[8];
        const int32_t dx = (int32_t)job[10] - x, dy = (int32_t)job[12] - y;
        const uint32_t ax = dx < 0 ? -dx : dx, ay = dy < 0 ? -dy : dy;
        const uint16_t distance = ax > ay ? ax : ay;
        if (distance < 64 || distance > 4072)
            continue;
        const uint16_t steps = (distance + 7u) >> 3;
        const uint16_t trim = (32u * steps + distance - 1u) / distance;
        if (2u * trim > steps)
            continue;
        const int16_t sx = dx * 256 / steps, sy = dy * 256 / steps;
        const uint16_t length = steps + 1u - 2u * trim;
        TRACE[rows * 4u] = x + (sx * trim) / 256;
        TRACE[rows * 4u + 1u] = y + (sy * trim) / 256;
        TRACE[rows * 4u + 2u] = sx;
        TRACE[rows * 4u + 3u] = sy;
        slots[rows] = i;
        lengths[rows++] = length;
        if (length > width)
            width = length;
    }
    if (rows && !asic(width, rows))
        return 1;
    const uint16_t stride = ((rows + 7u) & ~7u) * 2u;
    for (uint16_t row = 0; row < rows; ++row)
        bank[slots[row] * STRIDE * 2u + 14u] = scan(row, lengths[row], stride) != CLEAR;
    return 0;
}
