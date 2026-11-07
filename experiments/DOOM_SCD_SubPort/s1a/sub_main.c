/* S1a sub-CPU program: engine code from the R128 All objects runs here.
 * 1) run the engine checks and keep their CRCs;
 * 2) enter Word RAM 1M (bank 0 to the MD), signal READY;
 * 3) serve requests: id in $FF8018 changes -> swap banks (RET) -> ack $FF8026=id ->
 *    lump requests (id < 0x8000): CRC the lump in our bank, append it to a PRG-RAM cache;
 *    result requests (0x8000|k): report CRC k (k<S1A_TESTS) or the cache CRC (k==15);
 *    -> CRC in $FF802A/$FF802C, done = id in $FF8028.  Swap requests via comm word, never DMNA. */
#include "s1a_tests.h"

#define REG16(a) (*(volatile uint16_t *)(a))
#define BANK ((volatile const uint8_t *)0x0C0000)

void *memset(void *d, int c, unsigned long n) { uint8_t *p = d; while (n--) *p++ = (uint8_t)c; return d; }
void *memcpy(void *d, const void *s, unsigned long n) { uint8_t *p = d; const uint8_t *q = s; while (n--) *p++ = *q++; return d; }

static uint8_t cache[160u * 1024u];
static uint32_t cache_used, cache_crc, results[S1A_TESTS];

static void reply(uint16_t id, uint32_t crc)
{
    REG16(0xFF802A) = (uint16_t)(crc >> 16);
    REG16(0xFF802C) = (uint16_t)crc;
    REG16(0xFF8028) = id;
}

void sub_main(void)
{
    REG16(0xFF8026) = 0; REG16(0xFF8028) = 0;
    for (int k = 0; k < S1A_TESTS; k++)
        results[k] = s1a_test(k);
    uint16_t mode = 4;                 /* 1M, RET=0 */
    REG16(0xFF8002) = mode;
    REG16(0xFF8020) = 0x5343;          /* READY */
    uint16_t last = 0;
    for (;;)
    {
        const uint16_t id = REG16(0xFF8018);
        if (id == last) continue;
        last = id;
        mode ^= 1; REG16(0xFF8002) = mode; /* swap: we now own the bank the MD filled */
        REG16(0xFF8026) = id;
        if (id & 0x8000u)
        {
            const uint16_t k = id & 15u;
            reply(id, k < S1A_TESTS ? results[k] : (k == 15 ? cache_crc : cache_used));
            continue;
        }
        const uint16_t size = (uint16_t)((BANK[0] << 8) | BANK[1]);
        uint32_t crc = s1a_crc(0, (const uint8_t *)BANK + 4, size);
        if (cache_used + size <= sizeof cache)
        {
            for (uint16_t i = 0; i < size; i++) cache[cache_used + i] = BANK[4 + i];
            cache_crc = s1a_crc(cache_crc, cache + cache_used, size);
            cache_used += size;
        }
        reply(id, crc);
    }
}
