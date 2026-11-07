/* S1a: identical engine checks compiled for the Mega Drive (inside R128) and for the Sega CD sub-CPU. */
#ifndef S1A_TESTS_H
#define S1A_TESTS_H
#include "doomtype.h"
#include "m_fixed.h"
#include "m_random.h"
#include "tables.h"

#define S1A_TESTS 3

static uint32_t s1a_crc(uint32_t crc, const uint8_t *p, uint32_t n)
{
    crc = ~crc;
    while (n--)
    {
        crc ^= *p++;
        for (int k = 0; k < 8; k++)
            crc = (crc >> 1) ^ (0xEDB88320u & (0u - (crc & 1u)));
    }
    return ~crc;
}

static uint32_t s1a_crc32w(uint32_t crc, uint32_t v)
{
    uint8_t b[4] = { (uint8_t)(v >> 24), (uint8_t)(v >> 16), (uint8_t)(v >> 8), (uint8_t)v };
    return s1a_crc(crc, b, 4);
}

static uint32_t s1a_test(int which)
{
    uint32_t crc = 0, seed = 0x13579BDFu;
    switch (which)
    {
    case 0: /* random tables and indices */
        M_ClearRandom();
        for (int i = 0; i < 1024; i++) crc = s1a_crc32w(crc, (uint32_t)P_Random());
        for (int i = 0; i < 1024; i++) crc = s1a_crc32w(crc, (uint32_t)M_Random());
        M_ClearRandom();
        break;
    case 1: /* FixedMul as the engine implements it */
        for (int i = 0; i < 2048; i++)
        {
            seed = seed * 1103515245u + 12345u; const fixed_t a = (fixed_t)seed;
            seed = seed * 1103515245u + 12345u; const fixed_t b = (fixed_t)seed >> (seed & 15);
            crc = s1a_crc32w(crc, (uint32_t)FixedMul(a, b));
        }
        break;
    default: /* sine/cosine lookups */
        for (int x = 0; x < FINEANGLES; x += 3)
        {
            crc = s1a_crc32w(crc, (uint32_t)finesine(x));
            crc = s1a_crc32w(crc, (uint32_t)finecosine(x));
        }
        break;
    }
    return crc;
}
#endif
