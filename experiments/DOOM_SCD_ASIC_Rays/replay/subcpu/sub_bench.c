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

static uint16_t elapsed(uint16_t start)
{
    return (TIMER - start) & 0xfffu;
}

static bool asic(uint16_t width)
{
    STAMP_SIZE = 6; /* 32-pixel stamps, 4096-pixel map, no wrapping */
    REG(0xff805a) = 0x4000;
    REG(0xff805c) = RAYS / 8 - 1;
    REG(0xff805e) = 0x8000;
    REG(0xff8060) = 0;
    REG(0xff8062) = width;
    REG(0xff8064) = RAYS;
    REG(0xff8066) = 0x6000;
    for (uint32_t tries = 0; tries < 60000UL; ++tries)
        if (!(STAMP_SIZE & 0x8000u))
            return true;
    return false;
}

static bool scan(uint16_t row, uint16_t length)
{
    for (uint16_t x = 0; x < length; ++x)
    {
        const uint16_t word = IMAGE[((x >> 3) << 7) + row * 2u + ((x >> 2) & 1u)];
        if (word & (0xf000u >> ((x & 3u) * 4u)))
            return true;
    }
    return false;
}

static bool dda(const uint16_t *ray)
{
    uint32_t fx = (uint32_t)ray[0] << 8, fy = (uint32_t)ray[1] << 8;
    const int32_t dx = (int16_t)ray[2], dy = (int16_t)ray[3];
    for (uint16_t i = 0; i < ray[4]; ++i)
    {
        const uint16_t x = (fx >> 11) & 4095u, y = (fy >> 11) & 4095u;
        const uint16_t stamp = MAP[(y >> 5) * 128u + (x >> 5)];
        if (stamp)
        {
            const uint16_t word = STAMPS[((uint32_t)stamp << 6) + ((x & 31u) >> 3) * 64u +
                                          (y & 31u) * 2u + ((x >> 2) & 1u)];
            if (word & (0xf000u >> ((x & 3u) * 4u)))
                return true;
        }
        fx += dx;
        fy += dy;
    }
    return false;
}

void ray_bench(void)
{
    uint32_t report[REPORT_WORDS] = {0};
    const uint16_t *src = ray_assets;
    const uint16_t words = *src++;
    for (uint16_t i = 0; i < words; ++i)
        STAMPS[i] = *src++;
    for (uint16_t i = 0; i < 16384; ++i)
        MAP[i] = *src++;

    for (uint16_t batch = 0; batch < BATCHES; ++batch)
    {
        const uint16_t width = *src++;
        const uint16_t *vectors = src;
        uint16_t mark = TIMER;
        for (uint16_t i = 0; i < RAYS; ++i, src += 6)
            for (uint16_t j = 0; j < 4; ++j)
                TRACE[i * 4u + j] = src[j];
        report[SETUP] += elapsed(mark);
        mark = TIMER;
        if (!asic(width))
        {
            ++report[TIMEOUTS];
            break;
        }
        report[DRAW] += elapsed(mark);
        bool blocked[RAYS];
        for (uint16_t base = 0; base < RAYS; base += 8)
        {
            mark = TIMER;
            for (uint16_t i = base; i < base + 8u; ++i)
                blocked[i] = scan(i, vectors[i * 6u + 4u]);
            report[SCAN] += elapsed(mark);
        }
        for (uint16_t base = 0; base < RAYS; base += 8)
        {
            bool software[8];
            mark = TIMER;
            for (uint16_t i = 0; i < 8; ++i)
                software[i] = dda(vectors + (base + i) * 6u);
            report[DDA] += elapsed(mark);
            for (uint16_t i = 0; i < 8; ++i)
            {
                const uint16_t row = base + i;
                ++report[COUNT];
                report[MISMATCH] += blocked[row] != software[i];
                if (vectors[row * 6u + 5u])
                {
                    ++report[NATIVE_CLEAR];
                    report[FALSE_BLOCK] += blocked[row];
                }
                else
                {
                    ++report[NATIVE_BLOCK];
                    report[FALSE_CLEAR] += !blocked[row];
                }
            }
        }
    }
    for (uint16_t i = 0; i < REPORT_WORDS; ++i)
        REPORT[i] = report[i];
}
